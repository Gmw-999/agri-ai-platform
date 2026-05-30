import pandas as pd

# ====================== 你的路径我已直接填好 ======================
EXCEL_PATH = r"E:\python\PythonProject\豆包完善版\agri_ai_service\api\农药_农药产品库_世纪农药网.xlsx"
OUTPUT_SQL = "pesticides_data.sql"

# 字段映射（和你代码完全一致）
COL_MAP = {
    "药品名称": "drug_name",
    "图片": "image_url",
    "标题链接": "purchase_url"
}

# ====================== 一键生成SQL ======================
def generate_sql():
    print("正在读取 Excel...")
    df = pd.read_excel(EXCEL_PATH)
    print(f"读取成功！共 {len(df)} 条数据")
    print("Excel 列名：", df.columns.tolist())

    # 清理空值
    df = df.dropna(subset=["药品名称"])

    sql_lines = []
    sql_lines.append("USE agri_pesticides_db;")
    sql_lines.append("DELETE FROM pesticides;")
    sql_lines.append("BEGIN;")

    for idx, row in df.iterrows():
        drug = str(row["药品名称"]).replace("'", "''").strip()
        img = str(row["图片"]).replace("'", "''").strip() if pd.notna(row["图片"]) else ""
        link = str(row["标题链接"]).replace("'", "''").strip() if pd.notna(row["标题链接"]) else ""

        line = f"INSERT INTO pesticides (drug_name, image_url, purchase_url) VALUES ('{drug}', '{img}', '{link}');"
        sql_lines.append(line)

    sql_lines.append("COMMIT;")

    with open(OUTPUT_SQL, "w", encoding="utf8") as f:
        f.write("\n".join(sql_lines))

    print(f"\n✅ SQL 已生成：{OUTPUT_SQL}")
    print("✅ 直接在数据库里运行这个文件即可导入全部药品数据")

if __name__ == "__main__":
    generate_sql()