"""
自定义图像识别模型封装
集成你自己训练的三个模型：
1. 病害分布检测模型
2. 病害严重程度评估模型
3. 作物/病虫害分类模型
"""
import os
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
import numpy as np
from PIL import Image


class CustomModelBase:
    """自定义模型基类"""

    def __init__(self, model_name: str, model_path: str):
        self.logger = logging.getLogger(f"agri_ai.image_recognition.{model_name}")
        self.model_name = model_name
        self.model_path = model_path
        self.model = None
        self.is_loaded = False

        self.logger.info(f"初始化模型: {model_name}")
        self.logger.debug(f"模型路径: {model_path}")

    def load_model(self) -> bool:
        """加载模型（子类实现）"""
        raise NotImplementedError

    def predict(self, image: Union[str, bytes, np.ndarray]) -> Dict[str, Any]:
        """推理预测（子类实现）"""
        raise NotImplementedError

    def _load_image(self, image: Union[str, bytes, np.ndarray]) -> np.ndarray:
        """
        统一加载图片

        Args:
            image: 图片路径、字节流或numpy数组

        Returns:
            numpy数组格式的图片
        """
        try:
            if isinstance(image, str):
                # 文件路径
                if not os.path.exists(image):
                    raise FileNotFoundError(f"图片文件不存在: {image}")
                img = Image.open(image)
            elif isinstance(image, bytes):
                # 字节流
                from io import BytesIO
                img = Image.open(BytesIO(image))
            elif isinstance(image, np.ndarray):
                # 已经是numpy数组
                return image
            else:
                raise ValueError(f"不支持的图片类型: {type(image)}")

            # 转换为RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')

            return np.array(img)

        except Exception as e:
            self.logger.error(f"图片加载失败: {e}", exc_info=True)
            raise


class DiseaseDistributionDetector(CustomModelBase):
    """
    病害分布检测模型
    功能：识别图片中病害的位置和分布区域
    """

    def __init__(self, model_path: str = "./models/disease_distribution"):
        super().__init__("disease_distribution", model_path)
        self.class_names = ["健康", "叶斑病", "白粉病", "锈病", "枯萎病"]  # 根据你的实际类别修改

    def load_model(self) -> bool:
        """加载病害分布检测模型"""
        try:
            self.logger.info(f"加载病害分布检测模型: {self.model_path}")
            if not os.path.exists(self.model_path):
                self.logger.warning(f"模型文件不存在: {self.model_path}")
                self.is_loaded = False
                return False

            # 根据模型格式加载 (PyTorch / ONNX / TensorFlow)
            if self.model_path.endswith('.pt') or self.model_path.endswith('.pth'):
                import torch
                self.model = torch.load(self.model_path, map_location='cpu', weights_only=False)
            elif self.model_path.endswith('.onnx'):
                import onnxruntime as ort
                self.model = ort.InferenceSession(self.model_path)
            else:
                self.logger.warning(f"不支持的模型格式: {self.model_path}")
                self.is_loaded = False
                return False

            self.is_loaded = True
            self.logger.info("病害分布检测模型加载成功")
            return True

        except Exception as e:
            self.logger.warning(f"模型加载失败 ({self.model_path}): {e}")
            self.is_loaded = False
            return False

    def predict(self, image: Union[str, bytes, np.ndarray]) -> Dict[str, Any]:
        if not self.is_loaded:
            return {
                "success": False,
                "error": f"模型未加载，请确保模型文件存在: {self.model_path}",
                "distribution_data": None
            }
        try:
            img_array = self._load_image(image)
            # 实际推理逻辑取决于模型类型
            return {
                "success": False,
                "error": "模型推理逻辑需根据具体模型实现",
                "distribution_data": None
            }
        except Exception as e:
            self.logger.error(f"病害分布检测失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"检测失败: {str(e)}",
                "distribution_data": None
            }


class DiseaseSeverityEstimator(CustomModelBase):
    """
    病害严重程度评估模型
    功能：评估病害的危害程度（轻度/中度/重度）
    """

    def __init__(self, model_path: str = "./models/disease_severity"):
        super().__init__("disease_severity", model_path)
        self.severity_levels = ["轻度", "中度", "重度"]

    def load_model(self) -> bool:
        """加载严重程度评估模型"""
        try:
            self.logger.info(f"加载病害严重程度评估模型: {self.model_path}")
            if not os.path.exists(self.model_path):
                self.logger.warning(f"模型文件不存在: {self.model_path}")
                self.is_loaded = False
                return False
            import torch
            self.model = torch.load(self.model_path, map_location='cpu', weights_only=False)
            self.is_loaded = True
            self.logger.info("病害严重程度评估模型加载成功")
            return True
        except Exception as e:
            self.logger.warning(f"模型加载失败 ({self.model_path}): {e}")
            self.is_loaded = False
            return False

    def predict(
        self,
        image: Union[str, bytes, np.ndarray],
        ocr_text: Optional[str] = None,
        distribution_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            return {
                "success": False,
                "error": f"模型未加载，请确保模型文件存在: {self.model_path}",
                "severity": None
            }
        try:
            img_array = self._load_image(image)
            return {
                "success": False,
                "error": "模型推理逻辑需根据具体模型实现",
                "severity": None
            }
        except Exception as e:
            self.logger.error(f"严重程度评估失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"评估失败: {str(e)}",
                "severity": None
            }


class CropPestClassifier(CustomModelBase):
    """
    作物/病虫害分类模型
    功能：识别作物种类和病虫害类型
    """

    def __init__(self, model_path: str = "./models/crop_pest_classifier"):
        super().__init__("crop_pest_classifier", model_path)
        # 根据你的实际类别修改
        self.crop_classes = ["水稻", "小麦", "玉米", "大豆", "棉花"]
        self.pest_classes = ["稻瘟病", "小麦白粉病", "玉米螟", "蚜虫", "红蜘蛛"]

    def load_model(self) -> bool:
        """加载分类模型"""
        try:
            self.logger.info(f"加载作物/病虫害分类模型: {self.model_path}")
            if not os.path.exists(self.model_path):
                self.logger.warning(f"模型文件不存在: {self.model_path}")
                self.is_loaded = False
                return False
            import torch
            self.model = torch.load(self.model_path, map_location='cpu', weights_only=False)
            self.is_loaded = True
            self.logger.info("作物/病虫害分类模型加载成功")
            return True
        except Exception as e:
            self.logger.warning(f"模型加载失败 ({self.model_path}): {e}")
            self.is_loaded = False
            return False

    def predict(self, image: Union[str, bytes, np.ndarray]) -> Dict[str, Any]:
        if not self.is_loaded:
            return {
                "success": False,
                "error": f"模型未加载，请确保模型文件存在: {self.model_path}",
                "classification": None
            }
        try:
            img_array = self._load_image(image)
            return {
                "success": False,
                "error": "模型推理逻辑需根据具体模型实现",
                "classification": None
            }
        except Exception as e:
            self.logger.error(f"分类识别失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"识别失败: {str(e)}",
                "classification": None
            }


# ====================== 工厂函数 ======================
def create_distribution_detector(model_path: str = "./models/disease_distribution") -> DiseaseDistributionDetector:
    """创建病害分布检测器"""
    detector = DiseaseDistributionDetector(model_path)
    detector.load_model()
    return detector


def create_severity_estimator(model_path: str = "./models/disease_severity") -> DiseaseSeverityEstimator:
    """创建严重程度评估器"""
    estimator = DiseaseSeverityEstimator(model_path)
    estimator.load_model()
    return estimator


def create_crop_pest_classifier(model_path: str = "./models/crop_pest_classifier") -> CropPestClassifier:
    """创建作物/病虫害分类器"""
    classifier = CropPestClassifier(model_path)
    classifier.load_model()
    return classifier
