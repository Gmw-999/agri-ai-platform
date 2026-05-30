# config/settings.py
"""
统一配置管理模块。
所有配置从 .env 文件和环境变量读取，无硬编码密钥和路径。
"""
import os
import sys
import warnings
from pathlib import Path
from dotenv import load_dotenv

# 尽早屏蔽生产噪音警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 加载环境变量
load_dotenv(Path(__file__).parent.parent / ".env")

# ====================== 基础路径 ======================
BASE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BASE_DIR.parent  # all/ 目录


def _require_env(key: str) -> str:
    """获取必需的环境变量，不存在时抛出明确错误"""
    val = os.getenv(key)
    if val is None:
        raise RuntimeError(
            f"缺少必需的环境变量: {key}\n"
            f"请检查 .env 文件是否存在，参考 .env.example 填写。"
        )
    return val


def _env(key: str, default: str = "") -> str:
    """获取可选的环境变量"""
    return os.getenv(key, default)


# ====================== 编码配置 ======================
FORCE_ENCODING = "utf-8"
ACCEPT_CHARSET = "utf-8"

# ====================== LLM 配置 ======================
LLM_PROVIDER = _env("LLM_PROVIDER", "deepseek")

# DeepSeek
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = _env("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_DEFAULT_TIMEOUT = int(_env("DEEPSEEK_DEFAULT_TIMEOUT", "60"))
DEEPSEEK_DEFAULT_TEMPERATURE = float(_env("DEEPSEEK_DEFAULT_TEMPERATURE", "0.3"))
DEEPSEEK_DEFAULT_MAX_TOKENS = int(_env("DEEPSEEK_DEFAULT_MAX_TOKENS", "1024"))

# 豆包（备用）
DOUBAO_API_KEY = _env("DOUBAO_API_KEY", "")
DOUBAO_API_BASE = _env("DOUBAO_API_BASE", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
DOUBAO_DEFAULT_TIMEOUT = int(_env("DOUBAO_DEFAULT_TIMEOUT", "60"))
DOUBAO_DEFAULT_TEMPERATURE = float(_env("DOUBAO_DEFAULT_TEMPERATURE", "0.7"))
DOUBAO_DEFAULT_MAX_TOKENS = int(_env("DOUBAO_DEFAULT_MAX_TOKENS", "1024"))
DOUBAO_FAST_TEMPERATURE = float(_env("DOUBAO_FAST_TEMPERATURE", "0.3"))
DOUBAO_FAST_MAX_TOKENS = int(_env("DOUBAO_FAST_MAX_TOKENS", "512"))
DOUBAO_STREAM_CHUNK_SIZE = int(_env("DOUBAO_STREAM_CHUNK_SIZE", "5"))

# ====================== 数据库配置 ======================
DB_HOST = _env("DB_HOST", "localhost")
DB_PORT = int(_env("DB_PORT", "3306"))
DB_USER = _env("DB_USER", "root")
DB_PASSWORD = _env("DB_PASSWORD", "")
DB_NAME_AGRI = _env("DB_NAME_AGRI", "agri_db")
DB_NAME_PESTICIDES = _env("DB_NAME_PESTICIDES", "agri_pesticides_db")
DB_CHARSET = "utf8mb4"


def get_db_config(database: str = None) -> dict:
    """获取数据库连接配置"""
    if database is None:
        database = DB_NAME_AGRI
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": database,
        "charset": DB_CHARSET,
    }


# ====================== 百度AI配置 ======================
BAIDU_API_KEY = _env("BAIDU_API_KEY", "")
BAIDU_SECRET_KEY = _env("BAIDU_SECRET_KEY", "")
BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_OCR_BASIC_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
BAIDU_OCR_ACCURATE_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
BAIDU_PLANT_RECOG_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v1/plant"
BAIDU_GENERAL_RECOG_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general"
BAIDU_DEFAULT_TIMEOUT = 30

# ====================== 天气 API ======================
QWEATHER_API_KEY = _env("QWEATHER_API_KEY", "")

# ====================== 农药信息网配置 ======================
NONGYAO_BASE_URL = "https://www.nongyao001.com"
NONGYAO_SEARCH_PATH = "/sell/search.php"
NONGYAO_DEFAULT_TIMEOUT = 15

# ====================== API 服务地址 ======================
API_SERVER_HOST = _env("API_SERVER_HOST", "localhost")
API_SERVER_PORT = _env("API_SERVER_PORT", "8000")
API_SERVER_BASE = f"http://{API_SERVER_HOST}:{API_SERVER_PORT}"

# ====================== 向量数据库配置 ======================
VECTOR_DB_DIR = str(BASE_DIR / "data" / "vector_db")
VECTOR_COLLECTION_NAME = "agri_knowledge"
VECTOR_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ====================== 模型权重路径（相对于项目根目录） ======================
YOLO_MODEL_PATH = _env("YOLO_MODEL_PATH", str(PROJECT_ROOT / "yolo-weights" / "best.pt"))
RESNET_MODEL_PATH = _env("RESNET_MODEL_PATH", str(PROJECT_ROOT / "resnet-weights" / "best.pt"))
DEEPLABV3_MODEL_PATH = _env("DEEPLABV3_MODEL_PATH", str(PROJECT_ROOT / "deeplabv3_best.pth"))

# 自定义模型路径配置
DISEASE_DISTRIBUTION_MODEL_PATH = str(BASE_DIR / "models" / "disease_distribution")
DISEASE_SEVERITY_MODEL_PATH = str(BASE_DIR / "models" / "disease_severity")
CROP_PEST_CLASSIFIER_MODEL_PATH = str(BASE_DIR / "models" / "crop_pest_classifier")

# ====================== 农药 Excel 数据库（可选，旧版回退） ======================
PESTICIDE_EXCEL_PATH = _env("PESTICIDE_EXCEL_PATH", "")

# ====================== 应用配置 ======================
APP_DEBUG = _env("APP_DEBUG", "false").lower() == "true"
LOG_LEVEL = _env("LOG_LEVEL", "INFO")

# ====================== 全局实例初始化 ======================
import pandas as pd
from core.llm_factory import LLMFactory


def _init_llm():
    """初始化 LLM 实例"""
    if LLM_PROVIDER == "deepseek":
        if not DEEPSEEK_API_KEY:
            raise RuntimeError(
                "使用 DeepSeek 需要设置 DEEPSEEK_API_KEY 环境变量。\n"
                "请在 .env 文件中填写: DEEPSEEK_API_KEY=你的密钥"
            )
        return LLMFactory.init_llm(
            provider="deepseek",
            api_key=DEEPSEEK_API_KEY,
            model=DEEPSEEK_MODEL,
        )
    elif LLM_PROVIDER == "doubao":
        return LLMFactory.init_llm(
            provider="doubao",
            api_key=DOUBAO_API_KEY,
            model="doubao-pro",
        )
    else:
        raise ValueError(f"不支持的 LLM 供应商: {LLM_PROVIDER}")


llm = _init_llm()


def load_pesticide_excel():
    """加载农药 Excel 数据库（可选，MySQL 为主数据源）"""
    excel_path = PESTICIDE_EXCEL_PATH
    if not excel_path:
        print("[配置] 未设置 PESTICIDE_EXCEL_PATH，跳过 Excel 加载（使用 MySQL）")
        return pd.DataFrame()

    excel_path = Path(excel_path)
    print(f"[配置] 尝试加载Excel文件：{excel_path.absolute()}")

    if not excel_path.exists():
        print(f"[警告] 农药Excel文件不存在 → {excel_path.absolute()}")
        return pd.DataFrame()

    try:
        df = pd.read_excel(excel_path)
        df.columns = [col.strip() for col in df.columns]
        df.rename(
            columns={
                "药品名称": "pesticide_name",
                "标题链接": "purchase_url",
                "pro_txt1": "disease_type",
                "图片": "image_url"
            },
            inplace=True,
            errors="ignore"
        )
        if "title" not in df.columns:
            df["title"] = df["pesticide_name"]
        print(f"[成功] 加载农药数据库，共 {len(df)} 条记录 | 列: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"[错误] 加载Excel失败：{str(e)}")
        return pd.DataFrame()


df = load_pesticide_excel()

# 其他全局实例（延迟初始化，无则保留 None）
searcher = None
agri_vector_db = None
baidu_plant_recognizer = None
baidu_ocr_recognizer = None
disease_detector = None
DiseaseSeverityEstimator = None