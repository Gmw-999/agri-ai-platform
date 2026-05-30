# config/settings.py
import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

# 尽早屏蔽生产噪音警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 加载环境变量
load_dotenv(Path(__file__).parent.parent / ".env")

# ====================== 原有基础配置 ======================
# 编码配置
FORCE_ENCODING = "utf-8"
ACCEPT_CHARSET = "utf-8"

# 豆包大模型配置
DOUBAO_API_BASE = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_DEFAULT_TIMEOUT = 60
DOUBAO_DEFAULT_TEMPERATURE = 0.7
DOUBAO_DEFAULT_MAX_TOKENS = 1024
DOUBAO_FAST_TEMPERATURE = 0.3
DOUBAO_FAST_MAX_TOKENS = 512
DOUBAO_STREAM_CHUNK_SIZE = 5

# 百度AI配置
BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_OCR_BASIC_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
BAIDU_OCR_ACCURATE_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
BAIDU_PLANT_RECOG_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v1/plant"
BAIDU_GENERAL_RECOG_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general"
BAIDU_DEFAULT_TIMEOUT = 30

# 农药信息网配置
NONGYAO_BASE_URL = "https://www.nongyao001.com"
NONGYAO_SEARCH_PATH = "/sell/search.php"
NONGYAO_DEFAULT_TIMEOUT = 15

# API 服务地址（用于图片代理等场景，与前端 API_BASE 保持一致）
API_SERVER_HOST = os.getenv("API_SERVER_HOST", "192.168.43.228")
API_SERVER_PORT = os.getenv("API_SERVER_PORT", "8000")
API_SERVER_BASE = f"http://{API_SERVER_HOST}:{API_SERVER_PORT}"

# 向量数据库配置
BASE_DIR = Path(__file__).parent.parent
VECTOR_DB_DIR = str(BASE_DIR / "data" / "vector_db")
VECTOR_COLLECTION_NAME = "agri_knowledge"
VECTOR_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# 自定义模型路径配置
DISEASE_DISTRIBUTION_MODEL_PATH = str(BASE_DIR / "models" / "disease_distribution")
DISEASE_SEVERITY_MODEL_PATH = str(BASE_DIR / "models" / "disease_severity")
CROP_PEST_CLASSIFIER_MODEL_PATH = str(BASE_DIR / "models" / "crop_pest_classifier")

# ====================== 视觉三模型路径配置 ======================
# YOLOv8 目标检测模型
YOLO_MODEL_PATH = "E:/python/PythonProject/all/yolo-weights/best.pt"
# ResNet 图像分类模型（ultralytics classify 格式）
RESNET_MODEL_PATH = "E:/python/PythonProject/all/resnet-weights/best.pt"
# DeepLabV3 语义分割模型
DEEPLABV3_MODEL_PATH = "E:/python/PythonProject/all/deeplabv3_best.pth"


# ====================== 全局实例初始化 ======================
import pandas as pd
from pathlib import Path
from core.llm_factory import LLMFactory

# 1. 初始化LLM实例（通过工厂，后续换模型只改这里）
llm = LLMFactory.init_llm(
    provider="deepseek",
    api_key="REDACTED_KEY",
    model="deepseek-chat",
)


# 2. 初始化农药Excel数据库（修复encoding参数错误）
def load_pesticide_excel():
    # 指向api目录下的Excel文件（你的实际路径）
    excel_path = Path("E:/python/PythonProject/豆包完善版/agri_ai_service/api/农药_农药产品库_世纪农药网.xlsx")
    print(f"[配置] 尝试加载Excel文件：{excel_path.absolute()}")

    if not excel_path.exists():
        print(f"[警告] 农药Excel文件不存在 → {excel_path.absolute()}")
        return pd.DataFrame()

    try:
        # ✅ 修复：删除read_excel的encoding参数
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
        # Excel 没有单独的"标题"列，用 pesticide_name 作为 title（供 agri_tools 查询用）
        if "title" not in df.columns:
            df["title"] = df["pesticide_name"]
        print(f"[成功] 加载农药数据库，共 {len(df)} 条记录 | 列: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"[错误] 加载Excel失败：{str(e)}")
        return pd.DataFrame()


df = load_pesticide_excel()

# 3. 其他全局实例（无则保留None）
searcher = None
agri_vector_db = None
baidu_plant_recognizer = None
baidu_ocr_recognizer = None
disease_detector = None
DiseaseSeverityEstimator = None