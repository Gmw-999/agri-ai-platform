# tools/__init__.py
# 1. 导入实际存在的工具文件（agri_tools.py）
from .agri_tools import (
    agri_knowledge_query,
    enhanced_agri_knowledge_query,
    agri_info_extract,
    agri_data_analysis,
    simple_drug_links,
    pest_treatment_from_image
)

# 2. 定义缺失的 set_global_deps 函数（依赖注入核心）
# 全局变量存储依赖
_global_deps = {
    "llm": None,
    "pesticide_df": None,
    "vector_db": None,
    "disease_detector": None
}

def set_global_deps(llm, pesticide_df, vector_db, disease_detector):
    """
    全局依赖注入函数（给所有工具提供公共依赖）
    :param llm: 豆包LLM实例
    :param pesticide_df: 农药Excel数据库DataFrame
    :param vector_db: 向量数据库实例（可选）
    :param disease_detector: 病害检测模型实例（可选）
    """
    _global_deps["llm"] = llm
    _global_deps["pesticide_df"] = pesticide_df
    _global_deps["vector_db"] = vector_db
    _global_deps["disease_detector"] = disease_detector

def get_global_dep(dep_name: str):
    """获取全局依赖（工具内部调用）"""
    return _global_deps.get(dep_name)

# 3. 导出函数（方便外部导入）
__all__ = [
    "set_global_deps",
    "get_global_dep",
    "agri_knowledge_query",
    "enhanced_agri_knowledge_query",
    "agri_info_extract",
    "agri_data_analysis",
    "simple_drug_links",
    "pest_treatment_from_image"
]