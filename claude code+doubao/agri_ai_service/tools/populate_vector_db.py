"""
向量知识库自动填充脚本
为 6 大作物类别批量生成病虫害防治知识，导入 ChromaDB，同时写入 MySQL

用法：
    python tools/populate_vector_db.py                    # 全量生成 + 导入
    python tools/populate_vector_db.py --crop 水稻         # 只生成某个作物
    python tools/populate_vector_db.py --dry-run           # 只看要生成哪些，不调 LLM
    python tools/populate_vector_db.py --mysql-only        # 只写 MySQL，不写向量库
"""

import sys
import json
import time
import argparse
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

# 项目根目录加入路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("populate_db")

# ============================================================
# 作物 → 病虫害列表（按类别组织）
# ============================================================

CROP_DISEASES = {
    "水稻": [
        # 病害
        ("稻瘟病", False),         # (名称, 是否虫害)
        ("纹枯病", False),
        ("白叶枯病", False),
        ("稻曲病", False),
        ("胡麻叶斑病", False),
        ("细菌性条斑病", False),
        ("稻粒黑粉病", False),
        ("水稻矮缩病", False),
        # 虫害
        ("稻飞虱", True),
        ("二化螟", True),
        ("三化螟", True),
        ("稻纵卷叶螟", True),
        ("稻水象甲", True),
        ("稻蝗", True),
        ("稻秆潜蝇", True),
    ],
    "小麦": [
        ("条锈病", False),
        ("叶锈病", False),
        ("秆锈病", False),
        ("白粉病", False),
        ("赤霉病", False),
        ("全蚀病", False),
        ("小麦纹枯病", False),
        ("小麦根腐病", False),
        ("麦蚜", True),
        ("麦红蜘蛛", True),
        ("吸浆虫", True),
        ("麦秆蝇", True),
        ("金针虫", True),
        ("蛴螬", True),
    ],
    "玉米": [
        ("玉米大斑病", False),
        ("玉米小斑病", False),
        ("玉米锈病", False),
        ("玉米丝黑穗病", False),
        ("玉米瘤黑粉病", False),
        ("玉米茎基腐病", False),
        ("玉米纹枯病", False),
        ("玉米粗缩病", False),
        ("玉米螟", True),
        ("黏虫", True),
        ("草地贪夜蛾", True),
        ("玉米蚜虫", True),
        ("双斑萤叶甲", True),
        ("地老虎", True),
    ],
    "蔬菜": [
        ("黄瓜霜霉病", False),
        ("黄瓜白粉病", False),
        ("番茄晚疫病", False),
        ("番茄早疫病", False),
        ("番茄灰霉病", False),
        ("辣椒疫病", False),
        ("白菜软腐病", False),
        ("蔬菜枯萎病", False),
        ("蔬菜根结线虫病", False),
        ("小菜蛾", True),
        ("菜青虫", True),
        ("蔬菜蚜虫", True),
        ("红蜘蛛", True),
        ("蓟马", True),
        ("斑潜蝇", True),
        ("白粉虱", True),
        ("黄曲条跳甲", True),
    ],
    "水果": [
        ("苹果腐烂病", False),
        ("苹果轮纹病", False),
        ("苹果褐斑病", False),
        ("梨黑星病", False),
        ("桃褐腐病", False),
        ("桃缩叶病", False),
        ("葡萄霜霉病", False),
        ("葡萄白腐病", False),
        ("葡萄炭疽病", False),
        ("柑橘黄龙病", False),
        ("柑橘溃疡病", False),
        ("柑橘疮痂病", False),
        ("草莓灰霉病", False),
        ("草莓白粉病", False),
        ("桃蛀螟", True),
        ("柑橘红蜘蛛", True),
        ("介壳虫", True),
        ("食心虫", True),
        ("柑橘潜叶蛾", True),
    ],
    "经济作物": [
        ("棉花枯萎病", False),
        ("棉花黄萎病", False),
        ("花生叶斑病", False),
        ("花生根结线虫病", False),
        ("大豆锈病", False),
        ("大豆食心虫", True),
        ("油菜菌核病", False),
        ("油菜霜霉病", False),
        ("烟草花叶病毒病", False),
        ("茶树炭疽病", False),
        ("茶小绿叶蝉", True),
        ("甘蔗螟虫", True),
        ("棉铃虫", True),
        ("油菜蚜虫", True),
    ],
}

# 作物 ID 映射（对应 MySQL agri_knowledge_categories）
CATEGORY_IDS = {
    "水稻": 1,
    "小麦": 2,
    "玉米": 3,
    "蔬菜": 4,
    "水果": 5,
    "经济作物": 6,
}

# ============================================================
# LLM 生成
# ============================================================

def init_llm():
    """初始化 DeepSeek LLM"""
    from core.llm_factory import LLMFactory
    LLMFactory.init_llm(
        provider="deepseek",
        api_key="REDACTED_KEY",
        model="deepseek-chat",
    )
    return LLMFactory.get_llm()


def _build_prompt(crop: str, disease: str, is_pest: bool) -> str:
    dtype = "虫害" if is_pest else "病害"
    return f"""你是一位农业植保专家。请为以下作物病虫害生成详细的防治知识。

作物：{crop}
名称：{disease}
类型：{dtype}

要求：
1. 内容必须专业、准确、符合中国农业生产实际
2. 语言通俗易懂，农户能看明白、能操作
3. 推荐用药要写具体药品名称和用法用量

严格输出以下 JSON 格式，不要多余文字：
{{
    "title": "{disease}",
    "summary": "一句话概述（30字以内）",
    "symptoms": "详细症状描述，包括发病部位、典型症状特征",
    "cause": "发病原因，包括病原菌/虫害习性、发病条件",
    "prevention": "预防措施，包括农业防治、物理防治等",
    "treatment": "治疗方法，分点列出",
    "drugs": [
        {{"name": "药品名称", "usage": "用法用量（如稀释倍数、亩用量）"}},
        {{"name": "药品名称", "usage": "用法用量"}}
    ],
    "tags": ["{crop}", "{disease}", "{dtype}"]
}}
"""


def generate_one(llm, crop: str, disease: str, is_pest: bool, retries: int = 3) -> Optional[dict]:
    """调用 LLM 生成单个病虫害知识条目"""
    prompt = _build_prompt(crop, disease, is_pest)
    for attempt in range(retries):
        try:
            raw = llm.chat(prompt, temperature=0.3, max_tokens=1500)
            # 提取 JSON
            text = raw.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            data = json.loads(text)
            # 补全字段
            data.setdefault("title", disease)
            data.setdefault("summary", "")
            data.setdefault("symptoms", "")
            data.setdefault("cause", "")
            data.setdefault("prevention", "")
            data.setdefault("treatment", "")
            data.setdefault("drugs", [])
            data.setdefault("tags", [crop, disease])
            # 额外元数据
            data["crop"] = crop
            data["is_pest"] = is_pest
            data["category_id"] = CATEGORY_IDS.get(crop, 0)
            return data
        except Exception as e:
            logger.warning(f"  第{attempt+1}次失败: {disease} -> {e}")
            time.sleep(2)
    return None


# ============================================================
# 导入到 MySQL
# ============================================================

def insert_mysql(entries: List[dict]):
    """将生成的数据写入 MySQL agri_knowledge 表"""
    try:
        import pymysql
        conn = pymysql.connect(
            host="localhost", port=3306, user="root",
            password="123456", database="agri_db",
            charset="utf8mb4",
        )
        cursor = conn.cursor()

        # 检查已存在的 title（去重）
        cursor.execute("SELECT title FROM agri_knowledge")
        existing = {row[0] for row in cursor.fetchall()}

        inserted = 0
        for entry in entries:
            title = entry["title"]
            if title in existing:
                logger.info(f"  ⏭ 跳过已存在: {title}")
                continue

            drugs_json = json.dumps(entry.get("drugs", []), ensure_ascii=False)
            tags_str = ",".join(entry.get("tags", []))
            is_pest = 1 if entry.get("is_pest") else 0

            sql = """INSERT INTO agri_knowledge
                (category_id, title, summary, symptoms, cause, prevention, treatment, drugs, tags, is_pest)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                entry["category_id"],
                title,
                entry.get("summary", ""),
                entry.get("symptoms", ""),
                entry.get("cause", ""),
                entry.get("prevention", ""),
                entry.get("treatment", ""),
                drugs_json,
                tags_str,
                is_pest,
            ))
            inserted += 1

        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"✅ MySQL 写入完成: 新增 {inserted} 条")
        return inserted
    except Exception as e:
        logger.error(f"❌ MySQL 写入失败: {e}")
        return 0


# ============================================================
# 导入到 ChromaDB
# ============================================================

def import_vector_db(entries: List[dict]):
    """将生成的数据导入 ChromaDB"""
    try:
        from tools.vector_db import AgriVectorDB
        db = AgriVectorDB()
        count_before = db.get_document_count()
        logger.info(f"  当前向量库文档数: {count_before}")
    except Exception as e:
        logger.error(f"❌ 向量库初始化失败: {e}")
        return

    texts = []
    metadatas = []

    for entry in entries:
        # 组合全文作为向量化文本
        parts = [
            f"【{entry['title']}】",
            f"概述：{entry.get('summary', '')}",
            f"症状：{entry.get('symptoms', '')}",
            f"发病原因：{entry.get('cause', '')}",
            f"预防措施：{entry.get('prevention', '')}",
            f"治疗方法：{entry.get('treatment', '')}",
        ]
        drug_names = [d.get("name", "") for d in entry.get("drugs", [])]
        if drug_names:
            parts.append(f"推荐用药：{'、'.join(drug_names)}")

        text = "\n".join(parts)
        texts.append(text)
        metadatas.append({
            "title": entry["title"],
            "crop": entry.get("crop", ""),
            "category_id": entry.get("category_id", 0),
            "is_pest": entry.get("is_pest", False),
            "tags": ",".join(entry.get("tags", [])),
        })

    try:
        doc_ids = db.add_documents_batch(texts, metadatas)
        count_after = db.get_document_count()
        logger.info(f"✅ 向量库导入完成: 新增 {len(doc_ids)} 条 | 当前总数: {count_after}")
    except Exception as e:
        logger.error(f"❌ 向量库导入失败: {e}")


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="自动生成病虫害知识并导入向量库+MySQL")
    parser.add_argument("--crop", type=str, default="", help="只处理特定作物")
    parser.add_argument("--dry-run", action="store_true", help="只看要生成哪些，不调 LLM")
    parser.add_argument("--mysql-only", action="store_true", help="只写 MySQL，不写向量库")
    parser.add_argument("--vector-only", action="store_true", help="只写向量库，不写 MySQL")
    parser.add_argument("--max-workers", type=int, default=4, help="并发数（默认4）")
    args = parser.parse_args()

    # 收集待生成条目
    tasks = []
    for crop, diseases in CROP_DISEASES.items():
        if args.crop and crop != args.crop:
            continue
        for disease, is_pest in diseases:
            tasks.append((crop, disease, is_pest))

    logger.info(f"📋 共 {len(tasks)} 个病虫害条目待生成")
    if args.dry_run:
        for crop, disease, is_pest in tasks:
            tag = "虫害" if is_pest else "病害"
            logger.info(f"  [{crop}] {disease}（{tag}）")
        return

    # 初始化 LLM
    logger.info("🚀 初始化 DeepSeek LLM...")
    llm = init_llm()

    # 并发生成
    logger.info(f"⏳ 开始生成（并发 {args.max_workers}）...")
    entries = []
    done = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {
            pool.submit(generate_one, llm, crop, disease, is_pest): (crop, disease)
            for crop, disease, is_pest in tasks
        }
        for future in as_completed(futures):
            crop, disease = futures[future]
            result = future.result()
            done += 1
            if result:
                entries.append(result)
                logger.info(f"  ✅ [{done}/{len(tasks)}] {crop} > {disease}")
            else:
                failed += 1
                logger.warning(f"  ❌ [{done}/{len(tasks)}] {crop} > {disease} 生成失败")

    logger.info(f"📊 生成完成: 成功 {len(entries)} 条, 失败 {failed} 条")

    if not entries:
        logger.error("没有成功生成的条目，退出")
        return

    # 写入 MySQL
    if not args.vector_only:
        logger.info("📦 写入 MySQL...")
        insert_mysql(entries)

    # 写入向量库
    if not args.mysql_only:
        logger.info("📦 导入 ChromaDB 向量库...")
        import_vector_db(entries)

    logger.info("🎉 全部完成！")


if __name__ == "__main__":
    main()
