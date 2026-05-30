import os
import base64
import requests
import json
from typing import Any, Dict, Union, Optional

from core.baidu_ai_base import BaiduAIUtils
from core.llm_factory import LLMFactory
from tools.disease_detection import DiseaseSeverityEstimator
from config.settings import BAIDU_OCR_ACCURATE_URL, BAIDU_DEFAULT_TIMEOUT
from utils.common import ensure_utf8_string, build_utf8_headers, generate_request_id, safe_json_loads


class BaiduOCRRecognizer:
    """百度AI通用文字识别工具"""

    def __init__(self, api_key: str, secret_key: str, doubao_api_key: str = None, doubao_endpoint_id: str = None):
        self.baidu_utils = BaiduAIUtils(api_key, secret_key)
        self.ocr_api_url = BAIDU_OCR_ACCURATE_URL
        self.timeout = BAIDU_DEFAULT_TIMEOUT

        # 通过工厂获取全局 LLM 实例（统一入口，换模型只改配置）
        self.llm = LLMFactory.get_llm()
        self.severity_estimator = DiseaseSeverityEstimator()

    def recognize_text(self, image: Union[str, bytes], pos: int = 0) -> Dict[str, Any]:
        """百度AI通用文字识别"""
        try:
            # 处理图片输入
            if isinstance(image, str):
                if not os.path.exists(image):
                    raise FileNotFoundError(f"文件不存在: {image}")
                with open(image, 'rb') as f:
                    image_data = f.read()
            else:
                image_data = image

            if not image_data:
                raise ValueError("图片数据为空")

            # 编码为base64
            encoded_image = base64.b64encode(image_data).decode('utf-8').replace('\n', '').replace(' ', '')

            # 构建参数
            params = {
                "image": encoded_image,
                "language_type": "CHN_ENG",
                "detect_direction": "true",
                "enable_pdf": "false"
            }
            if pos == 1 or pos == 2:
                params["recognize_granularity"] = "small"
                params["vertexes_location"] = "true"

            # 获取Token并构建URL
            access_token = self.baidu_utils.get_access_token()
            full_url = f"{self.ocr_api_url}?access_token={access_token}"

            # 发送请求
            headers = build_utf8_headers("application/x-www-form-urlencoded")
            response = requests.post(
                full_url,
                headers=headers,
                data=params,
                timeout=self.timeout
            )
            response.encoding = "utf-8"
            response.raise_for_status()
            ocr_result = response.json()

            # 处理错误
            if "error_code" in ocr_result:
                error_msg = ensure_utf8_string(ocr_result.get("error_msg", "未知错误"))
                return {
                    "success": False,
                    "error": f"百度OCR识别失败（code: {ocr_result['error_code']}）: {error_msg}",
                    "requestId": generate_request_id()
                }

            # 提取文本和位置信息
            text_content = "\n".join([item["words"] for item in ocr_result.get("words_result", [])])
            position_data = []
            if pos in [1, 2] and "words_result" in ocr_result:
                for item in ocr_result["words_result"]:
                    pos_item = {
                        "text": item["words"],
                        "rectangle": item["location"],
                        "polygon": item.get("vertexes_location", [])
                    }
                    position_data.append(pos_item)

            return {
                "success": True,
                "text": text_content,
                "position_data": position_data if pos != 0 else None,
                "raw_data": ocr_result,
                "requestId": generate_request_id(),
                "source": "百度AI通用文字识别（高精度版）"
            }

        except Exception as e:
            import traceback
            print(f"[百度OCR错误] {str(e)}")
            print(f"[百度OCR堆栈] {traceback.format_exc()}")
            return {"success": False, "error": str(e), "source": "百度AI通用文字识别"}

    def recognize_agri_text_with_severity(self, image: Union[str, bytes], distribution_data: Optional[Dict] = None) -> Dict[str, Any]:
        """识别农业文本并估计危害程度"""
        # 执行OCR识别
        ocr_result = self.recognize_text(image, pos=0)
        if not ocr_result["success"]:
            return ocr_result
        ocr_text = ocr_result["text"]
        if not ocr_text.strip():
            return {
                "success": False,
                "error": "OCR识别成功但未提取到文本内容",
                "ocr_raw": ocr_result
            }

        # 英文转中文
        translate_prompt = f"""
        任务：将以下英文农业病害相关文本精准翻译为中文，仅返回翻译结果。
        要求：
        1. 农业术语准确；
        2. 保留关键数据；
        3. 去除无意义字符。
        英文文本：{ocr_text}
        """
        chinese_text = self.llm(translate_prompt, temperature=0)

        # 估计危害程度
        severity_result = self.severity_estimator.estimate(chinese_text, distribution_data)
        if not severity_result["success"]:
            return {
                "success": False,
                "error": severity_result["error"],
                "ocr_text": ocr_text,
                "translated_text": chinese_text,
                "ocr_raw": ocr_result["raw_data"]
            }

        # 解析农业文本
        agri_parse_prompt = f"""
        角色：资深农业病虫害防治专家，基于文本解析关键信息并生成防治方案。
        文本内容：{chinese_text}
        输出要求：
        1. 严格JSON格式，键值对为中文；
        2. 防治措施分农业防治、化学防治、栽培管理；
        3. 避免英文术语；
        4. 关键数据明确。
        输出格式：
        {{
            "病虫害类型":"",
            "作物类型":"",
            "发病面积":"",
            "防治措施": {{
                "农业防治":"",
                "化学防治":"",
                "栽培管理":""
            }}
        }}
        """
        parse_result = self.llm(agri_parse_prompt, temperature=0.1)
        parse_json = safe_json_loads(parse_result)

        # 返回结果
        return {
            "success": True,
            "ocr_text": ocr_text,
            "translated_text": chinese_text,
            "ocr_raw": ocr_result["raw_data"],
            "agri_parse": parse_json,
            "severity_estimation": {
                "severity": severity_result["severity"],
                "reason": severity_result["reason"],
                "raw_data": severity_result["raw_data"]
            },
            "distribution_data": distribution_data,
            "source": "百度OCR+豆包农业解析(全中文输出)"
        }