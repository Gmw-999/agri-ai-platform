from typing import Any, Dict, Optional
from config.settings import DISEASE_MODEL_PATH


class DiseaseDistributionDetector:
    """病害分布识别小模型封装"""

    def __init__(self, model_path: str = DISEASE_MODEL_PATH):
        self.model_path = model_path
        try:
            # 用户替换为真实模型加载代码
            self.model_loaded = True
            print(f"[小模型] 病害分布识别模型加载成功（路径：{model_path}）")
        except Exception as e:
            self.model_loaded = False
            print(f"[小模型] 加载失败：{str(e)}")

    def detect_distribution(self, image: bytes) -> Dict[str, Any]:
        """调用小模型识别病害分布"""
        if not self.model_loaded:
            return {
                "success": False,
                "error": "小模型未加载成功",
                "distribution_data": None
            }
        try:
            # 模拟小模型推理结果（用户替换为真实代码）
            simulated_regions = [
                {"x1": 120, "y1": 80, "x2": 250, "y2": 200, "disease_type": "叶斑病", "color": "#FF4444"},
                {"x1": 300, "y1": 150, "x2": 420, "y2": 280, "disease_type": "叶斑病", "color": "#FF4444"}
            ]
            return {
                "success": True,
                "distribution_data": {
                    "total_regions": len(simulated_regions),
                    "regions": simulated_regions,
                    "color_legend": {
                        "#FF4444": "叶斑病",
                        "#FFBB33": "白粉病",
                        "#00C851": "健康区域"
                    },
                    "image_size": {"width": 640, "height": 480}
                },
                "model_source": "用户自定义病害分布小模型"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"小模型推理失败：{str(e)}",
                "distribution_data": None
            }


class DiseaseSeverityEstimator:
    """病害危害程度估计模块"""

    @staticmethod
    def estimate(ocr_text: str, distribution_data: Optional[Dict] = None) -> Dict[str, Any]:
        if not ocr_text and not distribution_data:
            return {
                "success": False,
                "error": "缺少OCR文本和病害分布数据，无法估计危害程度",
                "severity": None,
                "reason": None
            }

        # 提取OCR关键信息
        ocr_key_info = {
            "has_large_area": any(keyword in ocr_text for keyword in ["大面积", "全株", "50%以上"]),
            "has_severe_symptom": any(keyword in ocr_text for keyword in ["枯萎", "腐烂", "坏死", "严重"]),
            "has_early_stage": any(keyword in ocr_text for keyword in ["初期", "少量", "零星", "10%以下"])
        }

        # 提取分布数据关键信息
        dist_key_info = {
            "region_count": distribution_data["total_regions"] if (
                    distribution_data and distribution_data.get("total_regions")) else 0,
            "is_wide_distribution": distribution_data["total_regions"] >= 3 if (
                    distribution_data and distribution_data.get("total_regions")) else False
        }

        # 综合判定危害程度
        severity = "中度"
        reason = []
        if ocr_key_info["has_early_stage"] and dist_key_info["region_count"] <= 1:
            severity = "轻度"
            reason = [
                "OCR文本提及病害处于初期/少量发生阶段",
                f"小模型识别到{dist_key_info['region_count']}个病害区域，分布范围小"
            ]
        elif (ocr_key_info["has_large_area"] or ocr_key_info["has_severe_symptom"]) and dist_key_info["is_wide_distribution"]:
            severity = "重度"
            reason = [
                "OCR文本提及大面积发病/严重症状（如枯萎、腐烂）",
                f"小模型识别到{dist_key_info['region_count']}个病害区域，分布范围广"
            ]
        else:
            reason = [
                "OCR文本未明确提及初期/重度特征",
                f"小模型识别到{dist_key_info['region_count']}个病害区域，分布范围中等"
            ]

        return {
            "success": True,
            "severity": severity,
            "reason": "\n".join(reason),
            "raw_data": {
                "ocr_key_info": ocr_key_info,
                "distribution_key_info": dist_key_info
            }
        }