import base64
import requests
import json
from typing import Any, Dict, Union
from core.baidu_ai_base import BaiduAIUtils
from core.llm_factory import LLMFactory
from config.settings import BAIDU_PLANT_RECOG_URL, BAIDU_GENERAL_RECOG_URL, BAIDU_DEFAULT_TIMEOUT
from utils.common import ensure_utf8_string, build_utf8_headers, safe_json_loads


class BaiduMultimodalRecognizer:
    """百度AI图像识别工具（植物/病虫害）"""

    def __init__(self, api_key: str, secret_key: str, doubao_api_key: str = None, doubao_endpoint_id: str = None):
        self.baidu_utils = BaiduAIUtils(api_key, secret_key)
        self.plant_recog_url = BAIDU_PLANT_RECOG_URL
        self.general_recog_url = BAIDU_GENERAL_RECOG_URL
        self.timeout = BAIDU_DEFAULT_TIMEOUT
        self.debug = False
        # 通过工厂获取全局 LLM 实例（统一入口，换模型只改配置）
        self.llm = LLMFactory.get_llm()

    def recognize_plant(self, image: Union[str, bytes]) -> Dict[str, Any]:
        """植物/病虫害识别"""
        try:
            # 处理图片
            if isinstance(image, str):
                with open(image, 'rb') as f:
                    image_data = f.read()
            else:
                image_data = image
            encoded_image = base64.b64encode(image_data).decode('utf-8').replace('\n', '').replace(' ', '')

            # 调用百度植物识别接口
            access_token = self.baidu_utils.get_access_token()
            full_url = f"{self.plant_recog_url}?access_token={access_token}"
            params = {
                "image": encoded_image,
                "baike_num": 1
            }
            headers = build_utf8_headers("application/x-www-form-urlencoded")
            response = requests.post(full_url, headers=headers, data=params, timeout=self.timeout)
            response.encoding = "utf-8"
            response.raise_for_status()
            baidu_result = response.json()

            if self.debug:
                print(f"[百度植物识别] 原始响应: {json.dumps(baidu_result, ensure_ascii=False)[:500]}...")

            # 处理错误（降级到通用识别）
            if "error_code" in baidu_result:
                error_msg = ensure_utf8_string(baidu_result.get("error_msg", "未知错误"))
                if baidu_result["error_code"] == 216201:
                    # 植物接口无结果，降级通用识别
                    full_url = f"{self.general_recog_url}?access_token={access_token}"
                    response = requests.post(full_url, headers=headers, data=params, timeout=self.timeout)
                    response.encoding = "utf-8"
                    baidu_result = response.json()
                else:
                    return {
                        "success": False,
                        "error": f"百度图像识别失败（code: {baidu_result['error_code']}）: {error_msg}",
                        "source": "百度AI图像识别"
                    }

            # 提取识别结果
            plant_info = {
                "植物名称": "未知",
                "置信度": 0.0,
                "是否有病虫害": False,
                "病虫害名称": "未知",
                "症状描述": "未知",
                "百科链接": "",
                "raw_baidu_result": baidu_result
            }

            if "result" in baidu_result and len(baidu_result["result"]) > 0:
                top_result = baidu_result["result"][0]
                plant_info["植物名称"] = top_result.get("name", "未知")
                plant_info["置信度"] = round(top_result.get("score", 0.0), 4)
                plant_info["百科链接"] = top_result.get("baike_info", {}).get("baike_url", "")

                # 判断是否有病虫害
                disease_keywords = ["病", "虫", "害", "枯", "斑", "腐", "霉"]
                if any(keyword in plant_info["植物名称"] for keyword in disease_keywords):
                    plant_info["是否有病虫害"] = True
                    plant_info["病虫害名称"] = plant_info["植物名称"]
                    plant_info["症状描述"] = top_result.get("baike_info", {}).get("description", "未知")[:200]

            # 豆包优化结果
            optimize_prompt = f"""基于以下百度AI识别结果优化植物/病虫害识别：
            原始结果：{json.dumps(plant_info, ensure_ascii=False)}
            要求：
            1. 修正识别错误；
            2. 补充症状和防治建议；
            3. 输出JSON格式，包含"植物名称","置信度","是否有病虫害","病虫害名称","症状描述","防治建议"；
            4. 无信息标注"未知"。
            """
            optimized_result = self.llm(optimize_prompt, temperature=0.2)
            optimized_json = safe_json_loads(optimized_result)
            plant_info.update(optimized_json)

            return {
                "success": True,
                "source": "百度AI植物识别+豆包优化",
                "result": plant_info
            }

        except requests.exceptions.HTTPError as e:
            error_detail = ensure_utf8_string(e.response.text if e.response else "无响应详情")
            return {
                "success": False,
                "error": f"百度AI HTTP错误: {e.response.status_code} - {error_detail}",
                "source": "百度AI图像识别"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"百度图像识别请求失败: {str(e)}",
                "source": "百度AI图像识别"
            }