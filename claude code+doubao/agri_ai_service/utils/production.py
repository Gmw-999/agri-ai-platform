"""
生产环境优化配置
集中管理：警告屏蔽、请求超时、重试策略
"""
import logging
import warnings
import urllib3

logger = logging.getLogger("agri_ai.production")


def suppress_noisy_warnings():
    """屏蔽生产环境中的常见噪音警告"""
    # 1. urllib3 证书验证警告（verify=False 时产生）
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 2. 通用 Python 警告
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
    warnings.filterwarnings("ignore", category=UserWarning, module="numpy")
    warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn")

    # 3. LangChain 冗余日志（如果不需要调试）
    logging.getLogger("langchain_core").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)

    # 4. urllib3 连接池日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # 5. chromadb 日志
    logging.getLogger("chromadb").setLevel(logging.WARNING)

    # 6. httpx 日志（某些 HTTP 库）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.info("✅ 生产环境警告已屏蔽")


# ====================== 全局超时配置 ======================

# 各外部服务超时（秒）
TIMEOUT_CONFIG = {
    "llm_request": 55,         # 大模型请求（豆包）
    "weather_api": 8,          # 和风天气 API
    "baidu_api": 15,           # 百度 AI API
    "pesticide_search": 10,    # 农药数据库搜索
    "nongyao001": 10,          # 农药信息网爬虫
    "searcher": 8,             # DuckDuckGo 搜索
    "vision_predict": 25,      # 视觉模型推理
    "image_preprocess": 10,    # 图片预处理
}

# 重试策略
RETRY_CONFIG = {
    "max_retries": 2,          # 最大重试次数
    "backoff_base": 0.5,       # 退避基础时间（秒）
    "backoff_max": 5.0,        # 最大退避时间
}
