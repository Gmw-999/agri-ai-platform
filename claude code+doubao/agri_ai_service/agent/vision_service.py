"""
视觉模型服务 v2 —— 真实模型推理
管理三个视觉小模型的调用入口：
- YOLOv8  → 目标检测（病虫害定位）
- ResNet  → 图像分类（病害种类识别，基于 ultralytics classify）
- DeepLabV3 → 语义分割（病斑区域分割，基于 torchvision）

两种调用模式：
1. manual_detect(model_name, image)    → 指定模型
2. auto_detect(image, user_context)    → LLM 自动判断
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

# 解决 Windows 下 OMP 多副本冲突
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from utils.image_utils import (
    preprocess_image,
    validate_image,
    get_image_info,
    with_timeout,
)

logger = logging.getLogger("agri_ai.vision")

# ====================== 懒加载防止 import 时卡住 ======================

_DETECTOR_CACHE: Dict[str, Any] = {}


def _lazy_load_ultralytics():
    if "ultralytics" not in _DETECTOR_CACHE:
        from ultralytics import YOLO
        _DETECTOR_CACHE["ultralytics"] = YOLO
    return _DETECTOR_CACHE["ultralytics"]


def _lazy_load_torch():
    if "torch" not in _DETECTOR_CACHE:
        import torch
        _DETECTOR_CACHE["torch"] = torch
    return _DETECTOR_CACHE["torch"]


def _lazy_load_torchvision():
    if "torchvision" not in _DETECTOR_CACHE:
        import torchvision
        _DETECTOR_CACHE["torchvision"] = torchvision
    return _DETECTOR_CACHE["torchvision"]


# ====================== 视觉模型包装器基类 ======================

class VisionModelWrapper:
    """视觉模型包装器基类"""

    def __init__(self, name: str, description: str, model_path: str = None):
        self.name = name
        self.description = description
        self.model_path = model_path
        self._model = None
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def load(self) -> bool:
        logger.info(f"[{self.name}] 模型加载: {self.model_path}")
        self._is_loaded = True
        return True

    @with_timeout(timeout_sec=60.0)
    def predict(self, image: bytes, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "loaded": self._is_loaded,
            "model_path": self.model_path,
        }


# ====================== YOLOv8 目标检测（真实推理） ======================

class YOLODetector(VisionModelWrapper):
    """
    YOLOv8 目标检测
    加载 ultralytics YOLO 模型进行真实推理
    """

    def __init__(self, model_path: str = None):
        super().__init__(
            name="yolov8",
            description="YOLOv8 目标检测：检测作物、病虫害、杂草的位置和类别",
            model_path=model_path,
        )

    def load(self) -> bool:
        try:
            YOLO = _lazy_load_ultralytics()
            self._model = YOLO(self.model_path)
            self._is_loaded = True
            logger.info(f"[YOLOv8] 模型加载成功 | 类别数: {len(self._model.names)}")
            return True
        except Exception as e:
            logger.error(f"[YOLOv8] 模型加载失败: {e}")
            return False

    def predict(self, image: bytes, confidence: float = 0.25, iou: float = 0.45, **kwargs) -> Dict[str, Any]:
        if not self._is_loaded and not self.load():
            return {"success": False, "error": "YOLOv8 模型未加载", "model": "yolov8"}

        try:
            import tempfile
            # ultralytics 支持直接传 numpy/PIL，但通过临时文件更稳定
            from PIL import Image
            import io
            pil_img = Image.open(io.BytesIO(image))
            results = self._model(pil_img, conf=confidence, iou=iou)

            detections = []
            for r in results:
                if r.boxes is not None:
                    for box, cls_id, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                        detections.append({
                            "label": self._model.names[int(cls_id)],
                            "confidence": round(float(conf), 4),
                            "bbox": [round(float(box[0]), 1), round(float(box[1]), 1),
                                     round(float(box[2]), 1), round(float(box[3]), 1)],
                        })

            img_info = get_image_info(image)
            return {
                "success": True,
                "model": "yolov8",
                "detections": detections,
                "detection_count": len(detections),
                "image_info": img_info,
            }
        except Exception as e:
            logger.error(f"[YOLOv8] 推理失败: {e}", exc_info=True)
            return {"success": False, "error": str(e), "model": "yolov8"}


# ====================== ResNet 图像分类（真实推理） ======================

class ResNetClassifier(VisionModelWrapper):
    """
    ResNet 图像分类（基于 ultralytics classify）
    注意：实际权重是 ultralytics 分类模型格式
    """

    def __init__(self, model_path: str = None):
        super().__init__(
            name="resnet",
            description="ResNet 图像分类：识别作物病害种类",
            model_path=model_path,
        )
        self.class_names = []

    def load(self) -> bool:
        try:
            YOLO = _lazy_load_ultralytics()
            self._model = YOLO(self.model_path, task="classify")
            self._is_loaded = True
            self.class_names = list(self._model.names.values())
            logger.info(f"[ResNet] 模型加载成功 | 类别数: {len(self.class_names)}")
            return True
        except Exception as e:
            logger.error(f"[ResNet] 模型加载失败: {e}")
            return False

    def predict(self, image: bytes, top_k: int = 5, **kwargs) -> Dict[str, Any]:
        if not self._is_loaded and not self.load():
            return {"success": False, "error": "ResNet 模型未加载", "model": "resnet"}

        try:
            from PIL import Image
            import io
            pil_img = Image.open(io.BytesIO(image))
            results = self._model(pil_img)

            predictions = []
            if results and results[0].probs is not None:
                probs = results[0].probs
                top_indices = probs.top5 if hasattr(probs, 'top5') else range(len(probs))
                for i in top_indices:
                    en_name = self._model.names[int(i)]
                    predictions.append({
                        "class": en_name,
                        "class_cn": CLASS_NAMES_CN.get(en_name, en_name),
                        "confidence": round(float(probs.data[int(i)]), 4),
                    })
                # 按置信度排序
                predictions = sorted(predictions, key=lambda x: x["confidence"], reverse=True)[:top_k]

            img_info = get_image_info(image)
            return {
                "success": True,
                "model": "resnet",
                "top_predictions": predictions,
                "image_info": img_info,
            }
        except Exception as e:
            logger.error(f"[ResNet] 推理失败: {e}", exc_info=True)
            return {"success": False, "error": str(e), "model": "resnet"}


# ====================== DeepLabV3 语义分割（真实推理） ======================

# 38类病害中文名称映射
CLASS_NAMES_CN = {
    "Apple_BlackRot": "苹果黑腐病",
    "Apple_CedarRust": "苹果雪松锈病",
    "Apple_Healthy": "苹果健康",
    "Apple_Scab": "苹果黑星病",
    "Blueberry_Healthy": "蓝莓健康",
    "Cherry_Healthy": "樱桃健康",
    "Cherry_PowderyMildew": "樱桃白粉病",
    "Corn_CercosporaLeafSpot": "玉米褐斑病",
    "Corn_CommonRust": "玉米普通锈病",
    "Corn_Healthy": "玉米健康",
    "Corn_NorthernBlight": "玉米大斑病",
    "Grape_BlackRot": "葡萄黑腐病",
    "Grape_Esca": "葡萄 Esca 病",
    "Grape_Healthy": "葡萄健康",
    "Grape_LeafBlight": "葡萄叶枯病",
    "Orange_Huanglongbing": "柑橘黄龙病",
    "Peach_BacterialSpot": "桃细菌性穿孔病",
    "Peach_Healthy": "桃健康",
    "Pepper_BacterialSpot": "辣椒细菌性斑点病",
    "Pepper_Healthy": "辣椒健康",
    "Potato_EarlyBlight": "马铃薯早疫病",
    "Potato_Healthy": "马铃薯健康",
    "Potato_LateBlight": "马铃薯晚疫病",
    "Raspberry_Healthy": "树莓健康",
    "Soybean_Healthy": "大豆健康",
    "Squash_PowderyMildew": "南瓜白粉病",
    "Strawberry_Healthy": "草莓健康",
    "Strawberry_LeafScorch": "草莓叶枯病",
    "Tomato_BacterialSpot": "番茄细菌性斑点病",
    "Tomato_EarlyBlight": "番茄早疫病",
    "Tomato_Healthy": "番茄健康",
    "Tomato_LateBlight": "番茄晚疫病",
    "Tomato_LeafMold": "番茄叶霉病",
    "Tomato_MosaicVirus": "番茄花叶病毒病",
    "Tomato_SeptoriaLeafSpot": "番茄斑枯病",
    "Tomato_SpiderMites": "番茄红蜘蛛",
    "Tomato_TargetSpot": "番茄靶斑病",
    "Tomato_YellowLeafCurlVirus": "番茄黄化曲叶病毒病",
}


class DeepLabV3Segmenter(VisionModelWrapper):
    """
    DeepLabV3 语义分割（torchvision deeplabv3_resnet50）
    对作物叶片病斑进行像素级分割
    """

    def __init__(self, model_path: str = None):
        super().__init__(
            name="deeplabv3",
            description="DeepLabV3 语义分割：对作物叶片病斑进行像素级分割",
            model_path=model_path,
        )
        self._transform = None

    def load(self) -> bool:
        try:
            torch = _lazy_load_torch()
            tv = _lazy_load_torchvision()

            state_dict = torch.load(self.model_path, map_location="cpu", weights_only=True)
            num_classes = state_dict["classifier.4.weight"].shape[0]
            # 去掉 aux_classifier 键（和标准 torchvision 不匹配）
            clean_sd = {k: v for k, v in state_dict.items() if not k.startswith("aux_classifier")}

            self._model = tv.models.segmentation.deeplabv3_resnet50(
                weights=None, num_classes=num_classes
            )
            self._model.load_state_dict(clean_sd, strict=False)
            self._model.eval()
            self._is_loaded = True
            self._num_classes = num_classes

            # 训练时预处理：resize → /255.0，不使用 ImageNet 标准化
            from torchvision import transforms
            self._transform = transforms.Compose([
                transforms.Resize((640, 640)),
                transforms.ToTensor(),
                # 训练时仅除以255，不做 ImageNet 标准化
            ])

            logger.info(f"[DeepLabV3] 模型加载成功 | 类别数: {num_classes}")
            return True
        except Exception as e:
            logger.error(f"[DeepLabV3] 模型加载失败: {e}", exc_info=True)
            return False

    def predict(self, image: bytes, **kwargs) -> Dict[str, Any]:
        if not self._is_loaded and not self.load():
            return {"success": False, "error": "DeepLabV3 模型未加载", "model": "deeplabv3"}

        try:
            torch = _lazy_load_torch()
            from PIL import Image
            import io

            pil_img = Image.open(io.BytesIO(image)).convert("RGB")
            input_tensor = self._transform(pil_img).unsqueeze(0)

            with torch.no_grad():
                output = self._model(input_tensor)["out"][0]
                mask = output.argmax(0).cpu().numpy()

            total_pixels = mask.size
            disease_pixels = int((mask == 1).sum())
            healthy_pixels = int((mask == 0).sum())
            disease_ratio = round(disease_pixels / total_pixels, 4)

            img_info = get_image_info(image)
            return {
                "success": True,
                "model": "deeplabv3",
                "segmentation": {
                    "disease_area_ratio": disease_ratio,
                    "healthy_area_ratio": round(1 - disease_ratio, 4),
                    "disease_pixels": disease_pixels,
                    "healthy_pixels": healthy_pixels,
                    "total_pixels": total_pixels,
                    "mask_shape": list(mask.shape),
                    "num_classes": self._num_classes,
                },
                "image_info": img_info,
            }
        except Exception as e:
            logger.error(f"[DeepLabV3] 推理失败: {e}", exc_info=True)
            return {"success": False, "error": str(e), "model": "deeplabv3"}


# ====================== 视觉模型管理中心 ======================

class VisionService:
    """
    视觉模型服务
    管理三个小模型的注册、加载、调用。
    """

    MODEL_MAP = {
        "yolov8": (YOLODetector, "目标检测"),
        "resnet": (ResNetClassifier, "图像分类"),
        "deeplabv3": (DeepLabV3Segmenter, "语义分割"),
    }

    def __init__(self):
        self._instances: Dict[str, VisionModelWrapper] = {}
        self._init_models()

    def _init_models(self):
        """初始化所有视觉模型"""
        for name, (cls, desc) in self.MODEL_MAP.items():
            model_path = self._get_model_path(name)
            self._instances[name] = cls(model_path=model_path)
            logger.info(f"[Vision] 注册: {name} ({desc}) | 路径: {model_path}")

    def _get_model_path(self, name: str) -> Optional[str]:
        """从 settings 配置获取模型路径"""
        from config.settings import (
            YOLO_MODEL_PATH,
            RESNET_MODEL_PATH,
            DEEPLABV3_MODEL_PATH,
        )
        paths = {
            "yolov8": YOLO_MODEL_PATH,
            "resnet": RESNET_MODEL_PATH,
            "deeplabv3": DEEPLABV3_MODEL_PATH,
        }
        return paths.get(name)

    def get_model(self, name: str) -> Optional[VisionModelWrapper]:
        return self._instances.get(name)

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"name": name, **inst.get_info()}
            for name, inst in self._instances.items()
        ]

    # ====================== 模式1：手动调用 ======================

    def manual_detect(self, model_name: str, image_data: bytes, **params) -> Dict[str, Any]:
        """前端手动指定调用某个小模型"""
        model = self._instances.get(model_name)
        if not model:
            return {
                "success": False,
                "error": f"未知模型: {model_name}，可选: {list(self._instances.keys())}",
            }

        valid, msg = validate_image(image_data)
        if not valid:
            return {"success": False, "error": msg}

        processed = preprocess_image(image_data)
        logger.info(f"[Vision] manual_detect | model={model_name} | img_size={len(image_data)}")
        result = model.predict(processed, **params)
        return result

    # ====================== 模式2：LLM 自动判断 ======================

    def auto_detect(self, image_data: bytes, user_context: str = "") -> Dict[str, Any]:
        """LLM 自动判断需要调用哪个/哪些模型"""
        from core.llm_factory import LLMFactory

        valid, msg = validate_image(image_data)
        if not valid:
            return {"success": False, "error": msg, "auto_decision": False}

        processed = preprocess_image(image_data)

        models_info = "\n".join([
            f"- {name}: {inst.description}"
            for name, inst in self._instances.items()
        ])

        decision_prompt = f"""你是一个农业视觉分析决策者。根据用户的问题，判断需要调用哪些视觉模型。

可用模型：
{models_info}

用户描述：{user_context}

请输出 JSON，决定调用哪些模型（可多选）：
{{
    "reasoning": "决策理由",
    "models": ["yolov8"],
    "params": {{"yolov8": {{"confidence": 0.25}}}}
}}

如果不确定就只调 yolov8。如果问题不涉及图片分析就设 models=[]。
"""
        try:
            llm = LLMFactory.get_llm()
            decision_text = llm.chat(decision_prompt, temperature=0.1, max_tokens=512)
            import re
            match = re.search(r"\{.*\}", decision_text, re.DOTALL)
            if match:
                decision = json.loads(match.group())
            else:
                decision = {"models": ["yolov8"], "params": {}}
        except Exception as e:
            logger.warning(f"[Vision] 自动决策失败，默认调 YOLOv8: {e}")
            decision = {"models": ["yolov8"], "params": {}}

        chosen = decision.get("models", ["yolov8"])
        params_map = decision.get("params", {})

        results = {}
        for model_name in chosen:
            if model_name in self._instances:
                model_params = params_map.get(model_name, {})
                results[model_name] = self._instances[model_name].predict(processed, **model_params)

        return {
            "success": True,
            "auto_decision": True,
            "reasoning": decision.get("reasoning", ""),
            "models_called": chosen,
            "results": results,
        }

    # ====================== 级联检测（YOLO → ResNet） ======================

    def crop_and_classify(self, image_data: bytes) -> Dict[str, Any]:
        """
        病斑裁剪后分类：DeepLabV3 分割出病斑区域 → 裁剪 → ResNet 分类

        策略：先对图片做语义分割定位病斑区域，然后只把病斑区域裁剪下来
        送给 ResNet 分类，去除大量背景干扰，提升识别准确率。

        Returns:
            {
                "success": True,
                "mode": "crop_classify" | "full_image_fallback",
                "deeplab": { "disease_area_ratio": 0.xx, "has_disease": bool },
                "resnet": { "success": True, "top_predictions": [...] },
                "crop_info": { "cropped": True, ... },
                "elapsed": 1.23,
            }
        """
        from PIL import Image
        import io
        import time
        import numpy as np

        start = time.time()

        valid, msg = validate_image(image_data)
        if not valid:
            return {"success": False, "error": msg}

        processed = preprocess_image(image_data)
        pil_orig = Image.open(io.BytesIO(image_data)).convert("RGB")
        orig_w, orig_h = pil_orig.size

        # 1. DeepLab inference to get mask
        deeplab = self._instances.get("deeplabv3")
        if not deeplab:
            return {"success": False, "error": "DeepLabV3 模型未注册"}
        if not deeplab.is_loaded:
            if not deeplab.load():
                return {"success": False, "error": "DeepLabV3 模型加载失败"}

        import torch
        pil_input = Image.open(io.BytesIO(processed)).convert("RGB")
        input_tensor = deeplab._transform(pil_input).unsqueeze(0)

        with torch.no_grad():
            output = deeplab._model(input_tensor)["out"][0]
            mask = output.argmax(0).cpu().numpy()

        disease_pixels = int((mask == 1).sum())
        total_pixels = mask.size
        disease_ratio = round(disease_pixels / total_pixels, 4)

        # 2. No disease found → fall back to full-image ResNet
        if disease_pixels == 0:
            resnet_result = self.manual_detect("resnet", processed)
            elapsed = time.time() - start
            return {
                "success": True,
                "mode": "full_image_fallback",
                "message": "未检测到病斑区域，已使用原图分类",
                "deeplab": {
                    "disease_area_ratio": disease_ratio,
                    "has_disease": False,
                },
                "resnet": resnet_result,
                "crop_info": {"cropped": False},
                "elapsed": round(elapsed, 2),
            }

        # 3. Extract disease region bbox in mask coords (640x640)
        disease_mask = mask == 1
        rows = np.any(disease_mask, axis=1)
        cols = np.any(disease_mask, axis=0)
        y_indices = np.where(rows)[0]
        x_indices = np.where(cols)[0]
        y_min, y_max = int(y_indices[0]), int(y_indices[-1])
        x_min, x_max = int(x_indices[0]), int(x_indices[-1])

        # Map mask → original image coords; add 20% padding
        bbox_w = (x_max - x_min) * orig_w / 640.0
        bbox_h = (y_max - y_min) * orig_h / 640.0
        pad_x = int(bbox_w * 0.2)
        pad_y = int(bbox_h * 0.2)

        crop_bbox = (
            max(0, int(x_min * orig_w / 640.0) - pad_x),
            max(0, int(y_min * orig_h / 640.0) - pad_y),
            min(orig_w, int(x_max * orig_w / 640.0) + pad_x),
            min(orig_h, int(y_max * orig_h / 640.0) + pad_y),
        )

        # 4. Crop original image → run ResNet
        crop_img = pil_orig.crop(crop_bbox)
        crop_buf = io.BytesIO()
        crop_img.save(crop_buf, format="JPEG", quality=92)
        crop_bytes = crop_buf.getvalue()

        resnet_result = self.manual_detect("resnet", crop_bytes)

        elapsed = time.time() - start
        return {
            "success": True,
            "mode": "crop_classify",
            "deeplab": {
                "disease_area_ratio": disease_ratio,
                "has_disease": True,
                "disease_pixels": disease_pixels,
            },
            "resnet": resnet_result,
            "crop_info": {
                "cropped": True,
                "bbox_mask": [int(x_min), int(y_min), int(x_max), int(y_max)],
                "bbox_cropped": list(crop_bbox),
                "original_size": [orig_w, orig_h],
            },
            "elapsed": round(elapsed, 2),
        }

    def cascade_detect(self, image_data: bytes) -> Dict[str, Any]:
        """
        级联检测：YOLOv8 先检测 → 对置信度最高的区域用 ResNet 分类
        """
        yolo_result = self.manual_detect("yolov8", image_data)
        if not yolo_result.get("success"):
            return yolo_result

        detections = yolo_result.get("detections", [])
        if detections:
            # 对最高置信度检测用 ResNet 精分类
            resnet_result = self.manual_detect("resnet", image_data, top_k=3)
            for det in detections[:1]:
                det["refined"] = resnet_result.get("top_predictions", [])

        return {
            "success": True,
            "mode": "cascade",
            "yolo_result": yolo_result,
            "final_detections": detections,
        }
