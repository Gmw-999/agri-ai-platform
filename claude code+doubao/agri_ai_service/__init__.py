# 包版本、核心类导出
__version__ = "1.0.0"

# ====================== 关键修复：消除编辑器误报 + 延迟导入避免循环 ======================
# 仅在编辑器静态检查时导入（不实际执行，消除红色提示）
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core.base_llm import BaseLLM
    from .core.llm_wrapper import DoubaoLLM
    from .core.llm_factory import LLMFactory
    from .tools.baidu_ocr import BaiduOCRRecognizer
    from .tools.baidu_multimodal import BaiduMultimodalRecognizer
    from .tools.disease_detection import DiseaseDistributionDetector, DiseaseSeverityEstimator
    from .tools.nongyao_search import Nongyao001Searcher
    from .tools.vector_db import AgriVectorDB

# 运行时延迟导入（核心：避免初始化时循环导入）
def __getattr__(name):
    """动态导入核心类，解决循环导入问题"""
    if name == "BaseLLM":
        from .core.base_llm import BaseLLM
        return BaseLLM
    elif name == "DoubaoLLM":
        from .core.llm_wrapper import DoubaoLLM
        return DoubaoLLM
    elif name == "LLMFactory":
        from .core.llm_factory import LLMFactory
        return LLMFactory
    elif name == "BaiduOCRRecognizer":
        from .tools.baidu_ocr import BaiduOCRRecognizer
        return BaiduOCRRecognizer
    elif name == "BaiduMultimodalRecognizer":
        from .tools.baidu_multimodal import BaiduMultimodalRecognizer
        return BaiduMultimodalRecognizer
    elif name == "DiseaseDistributionDetector":
        from .tools.disease_detection import DiseaseDistributionDetector
        return DiseaseDistributionDetector
    elif name == "DiseaseSeverityEstimator":
        from .tools.disease_detection import DiseaseSeverityEstimator
        return DiseaseSeverityEstimator
    elif name == "Nongyao001Searcher":
        from .tools.nongyao_search import Nongyao001Searcher
        return Nongyao001Searcher
    elif name == "AgriVectorDB":
        from .tools.vector_db import AgriVectorDB
        return AgriVectorDB
    raise AttributeError(f"模块 {__name__} 没有属性 {name}")

# 保留原有导出列表，确保外部使用方式不变
__all__ = [
    "BaseLLM",
    "DoubaoLLM",
    "LLMFactory",
    "BaiduOCRRecognizer",
    "BaiduMultimodalRecognizer",
    "DiseaseDistributionDetector",
    "DiseaseSeverityEstimator",
    "Nongyao001Searcher",
    "AgriVectorDB"
]