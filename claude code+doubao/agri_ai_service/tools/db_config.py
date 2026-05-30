# 数据库配置（根据你的实际情况修改）
# 支持MySQL/SQLite，选其一即可

# ========== MySQL配置（推荐） ==========
DB_CONFIG = {
    "host": "localhost",      # 数据库地址
    "port": 3306,             # 端口
    "user": "root",           # 用户名
    "password": "你的数据库密码", # 密码
    "database": "agri_db",    # 数据库名
    "charset": "utf8mb4"
}

# ========== SQLite配置（备用，无需安装数据库） ==========
# DB_PATH = "agri_pesticides.db"

# 数据库表和字段映射（必须和你的数据库一致！）
TABLE_NAME = "pesticides"  # 你的农药表名
FIELD_MAPPING = {
    "drug_name": "药品名称",  # 数据库中的药品名字段
    "image_url": "图片链接",  # 数据库中的图片链接字段
    "purchase_url": "购买链接" # 数据库中的购买链接字段
}