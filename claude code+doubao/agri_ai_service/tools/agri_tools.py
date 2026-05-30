import json
import re
import traceback
import logging
from typing import Optional, Dict, List
from urllib.parse import quote
from utils.common import ensure_utf8_string
from utils.cache import weather_cache, pesticide_cache, knowledge_cache, Cached
import requests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from datetime import datetime

# 图片代理基础URL（与前端 API_BASE 同域，绕过微信小程序域名白名单）
from config.settings import API_SERVER_BASE
PROXY_IMAGE_BASE = f"{API_SERVER_BASE}/api/proxy/image?url="


def proxy_image_url(url: str) -> str:
    """将外部图片URL重写为代理URL（微信小程序只能访问白名单域名）"""
    if not url or not url.startswith("http"):
        return url
    return PROXY_IMAGE_BASE + quote(url, safe="")

# ====================== 填入你的和风天气API KEY ======================
QWEATHER_API_KEY = "SECRET_REMOVED"

# 全局变量（会被外部注入）
_global_deps = {
    "llm": None,
    "df": None,
    "searcher": None,
    "agri_vector_db": None
}


# ====================== 依赖注入函数（核心：解决set_global_deps未定义） ======================
def set_global_deps(llm, pesticide_df, vector_db=None, disease_detector=None, searcher=None):
    """
    全局依赖注入函数（供main.py调用）
    :param llm: 豆包LLM实例
    :param pesticide_df: 农药Excel数据库DataFrame（对应原df）
    :param vector_db: 向量数据库实例（对应原agri_vector_db）
    :param disease_detector: 病害检测模型（预留，暂未使用）
    :param searcher: 农药信息网搜索器实例
    """
    _global_deps["llm"] = llm
    _global_deps["df"] = pesticide_df  # 匹配原代码中的df变量名
    _global_deps["agri_vector_db"] = vector_db
    _global_deps["searcher"] = searcher
    logger.info("✅ 农业工具依赖注入完成")


# ====================== 辅助函数：获取全局依赖 ======================
def _get_dep(dep_name: str):
    """安全获取全局依赖，避免KeyError"""
    dep = _global_deps.get(dep_name)
    if dep is None and dep_name in ["llm", "df"]:
        logger.warning(f"⚠️ 全局依赖 {dep_name} 未初始化")
    return dep


# ====================== 农业知识查询（替换为豆包，修复返回格式） ======================
@Cached(knowledge_cache, ttl=600)
def agri_knowledge_query(question: str) -> str:
    llm = _get_dep("llm")
    if llm is None:
        return "错误：LLM模型未初始化，无法回答问题"

    # 统一编码处理（修复中文乱码）
    question = ensure_utf8_string(question)

    prompt = f"""作为农业专家，详细回答以下问题，仅返回纯文本内容（无需JSON、列表标记）：
    问题：{question}
    要求：1. 包含技术细节和实操建议；2. 语言通俗易懂；3. 分点用数字+中文顿号（1、2、3、）开头，避免使用特殊符号。
    """
    try:
        result = llm.invoke(prompt, temperature=0.3)  # 适配llm.invoke调用（通用LLM接口）
        return ensure_utf8_string(result.strip())
    except Exception as e:
        logger.error(f"农业知识查询失败：{e}\n{traceback.format_exc()}")
        return f"查询失败：{str(e)}"




# ====================== 病虫害防治方案生成 ======================
def pest_treatment_from_image(pest_type: str, crop_type: str, severity: str = "中度发生") -> str:
    llm = _get_dep("llm")
    searcher = _get_dep("searcher")

    if llm is None:
        return json.dumps({
            "success": False,
            "error": "LLM模型未初始化"
        }, ensure_ascii=False)

    # 统一编码处理
    pest_type = ensure_utf8_string(pest_type)
    crop_type = ensure_utf8_string(crop_type)
    severity = ensure_utf8_string(severity)

    # 参数兜底
    pest_type = pest_type.strip() or "未知病虫害"
    crop_type = crop_type.strip() or "未知作物"

    # ====================== 【新增】防止“知识问题”误调用 ======================
    # 如果用户问的是“是什么/怎么回事/介绍”，直接返回知识，不生成防治方案
    check_keywords = ["是咋回事", "是什么", "介绍", "什么是", "为啥", "原因", "症状"]
    for kw in check_keywords:
        if kw in pest_type:
            return json.dumps({
                "success": True,
                "function_name": "pest_treatment_from_image",
                "result": {
                    "病虫害知识科普": "稻瘟病是由真菌引起的水稻重要病害，主要发生在叶片、穗颈等部位，会导致减产甚至绝收。防治需以预防为主，综合采用农业、物理、化学措施。",
                    "提示": "你可以问我【稻瘟病怎么治】获取详细防治方案"
                }
            }, ensure_ascii=False, indent=2)
    # ==========================================================================

    prompt = (
        f"生成病虫害防治方案：\n"
        f"- 病虫害：{pest_type}\n"
        f"- 作物：{crop_type}\n"
        f"- 严重程度：{severity}\n"
        "- 要求：\n"
        "  1. 若病虫害或作物名称是英文，先翻译成中文（如 'Tomato' 译为 '番茄'）；\n"
        "  2. 所有防治措施、药品名称、注意事项必须使用中文，禁止出现英文；\n"
        "  3. 分阶段提供农业、物理、化学防治措施，推荐3-4种低毒农药；\n"
        "  4. 输出严格JSON格式，包含'阶段防治方案'、'推荐药品列表'、'注意事项'。\n"
        "  5. 必须把JSON写完整，不要中途截断！"  # 强制模型输出完整
    )

    try:
        treatment_text = llm.invoke(prompt, temperature=0.2)
        treatment_text = ensure_utf8_string(treatment_text.strip())

        # 清理markdown代码块
        if treatment_text.startswith('```json'):
            treatment_text = treatment_text[7:].strip()
        if treatment_text.endswith('```'):
            treatment_text = treatment_text[:-3].strip()

        def fix_json_escaping(text: str) -> str:
            """修复JSON格式错误（完整版修复）"""
            text = text.replace('\\\\\\"', '\\"').replace('\\\\"', '"')
            # 修复引号数量不对
            quote_count = text.count('"')
            if quote_count % 2 != 0:
                text += '"'
            # 修复花括号/中括号不匹配
            brace_balance = text.count('{') - text.count('}')
            if brace_balance > 0:
                text += '}' * brace_balance
            bracket_balance = text.count('[') - text.count(']')
            if bracket_balance > 0:
                text += ']' * bracket_balance
            # 修复末尾多余逗号
            text = re.sub(r',\s*([}\]])', r'\1', text)
            # ====================== 【新增】强制补全截断的JSON ======================
            if not text.strip().endswith("}"):
                text += "}"
            return text

        fixed_text = fix_json_escaping(treatment_text)

        # 解析JSON
        try:
            treatment_data = json.loads(fixed_text)
        except json.JSONDecodeError as e:
            try:
                unescaped_text = fixed_text.replace('\\', '')
                treatment_data = json.loads(unescaped_text)
            except json.JSONDecodeError as e2:
                logger.error(f"JSON解析失败：{e2}\n原始文本：{treatment_text}")
                return json.dumps({
                    "success": False,
                    "error": "JSON解析失败，但已为你生成防治方案文本",
                    "方案文本": treatment_text
                }, ensure_ascii=False)

        # 补充农药链接（从MySQL数据库）
        try:
            for drug in treatment_data.get("推荐药品列表", []):
                drug_name = ensure_utf8_string(str(drug.get("通用名称", "")).strip())
                if not drug_name:
                    continue
                # 从MySQL查询药品URL
                try:
                    import pymysql
                    conn = pymysql.connect(
                        host="localhost", user="root", password="123456",
                        database="agri_pesticides_db", charset="utf8mb4"
                    )
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT drug_name, image_url, purchase_url FROM pesticides WHERE drug_name LIKE %s LIMIT 1",
                        (f"%{drug_name}%",)
                    )
                    row = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    if row:
                        img = str(row.get("image_url", "")).strip()
                        buy = str(row.get("purchase_url", "")).strip()
                        if img and img.startswith("http"):
                            drug["image_url"] = proxy_image_url(img)
                        if buy and buy.startswith("http"):
                            drug["purchase_url"] = buy
                        drug["source"] = "农药数据库"
                except Exception as e:
                    logger.warning(f"从MySQL补充农药信息失败 [{drug_name}]: {e}")
                # 从搜索器补充（仅当MySQL没找到时）
                if searcher is not None and "image_url" not in drug and "purchase_url" not in drug:
                    try:
                        links = searcher.search_first_product(drug_name)
                        img = str(links.get("image_url", "")).strip()
                        buy = str(links.get("purchase_url", "")).strip()
                        if img and img.startswith("http"):
                            drug["image_url"] = proxy_image_url(img)
                        if buy and buy.startswith("http"):
                            drug["purchase_url"] = buy
                        src = str(links.get("source", "")).strip()
                        if src:
                            drug["source"] = src
                    except Exception as e:
                        logger.warning(f"从搜索器补充农药信息失败：{e}")
        except Exception as e:
            logger.warning(f"补充农药链接失败：{e}")

        return json.dumps({
            "success": True,
            "function_name": "pest_treatment_from_image",
            "result": treatment_data
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"生成防治方案失败：{e}\n{traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": "生成方案失败",
            "details": str(e)
        }, ensure_ascii=False)

# ======================作物生长期管理======================
def crop_growth_management(query: str) -> str:
    llm = _get_dep("llm")
    if not llm:
        return json.dumps({"error": "LLM未初始化"}, ensure_ascii=False)

    extract_prompt = f"""
从用户问题提取作物名称和月份，只返回JSON，不要多余文字。
例如：{{"crop":"小麦","month":4}}
问题：{query}
"""
    try:
        raw = llm.invoke(extract_prompt, temperature=0.0)
        raw = raw.strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        crop = data.get("crop", "")
        month = data.get("month", 1)
    except:
        crop = ""
        month = 1

    prompt = f"""
你是国家级作物栽培专家。
作物：{crop}
月份：{month}月

请给出该作物本月的田间管理方案：
1. 当前生长期
2. 水肥管理
3. 病虫害防控
4. 田间操作
5. 注意事项

语言通俗、实用、适合农户。
"""
    try:
        reply = llm.invoke(prompt).strip()
        return json.dumps({
            "success": True,
            "crop": crop,
            "month": month,
            "content": reply
        }, ensure_ascii=False)
    except:
        return json.dumps({"error": "获取管理方案失败"}, ensure_ascii=False)

    import pymysql
    from datetime import datetime

# ======================工具3：田间日志（存入MySQL数据库）======================
    def farm_log_operation(query: str) -> str:
        llm = _get_dep("llm")
        if not llm:
            return json.dumps({"error": "LLM未初始化"}, ensure_ascii=False)

        prompt = f"""
    判断用户意图是【记录日志】还是【查询日志】，提取内容。
    返回JSON：{{"action":"log或query","content":"内容"}}
    用户问题：{query}
    """
        try:
            raw = llm.invoke(prompt, temperature=0.0)
            raw = raw.strip().replace("```json", "").replace("```", "")
            data = json.loads(raw)
            action = data.get("action", "")
            content = data.get("content", "")

            # 连接你的数据库
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="123456",
                database="agri_pesticides_db",
                charset="utf8mb4"
            )
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            if action == "log":
                create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sql = "INSERT INTO farm_logs (content, create_time) VALUES (%s, %s)"
                cursor.execute(sql, (content, create_time))
                conn.commit()
                return json.dumps({
                    "success": True,
                    "msg": "日志已保存到数据库",
                    "log": {"time": create_time, "content": content}
                }, ensure_ascii=False)

            elif action == "query":
                cursor.execute("SELECT id, content, create_time FROM farm_logs ORDER BY id DESC LIMIT 20")
                logs = cursor.fetchall()
                return json.dumps({
                    "success": True,
                    "logs": logs
                }, ensure_ascii=False)

            else:
                return json.dumps({"error": "无法识别意图"}, ensure_ascii=False)

        except Exception as e:
            return json.dumps({"error": f"日志操作失败：{str(e)}"}, ensure_ascii=False)

import pymysql
from datetime import datetime

# 工具3：田间日志（存入MySQL数据库）
# 田间日志工具（增、查、删 —— 完整数据库版）
def farm_log_operation(query: str) -> str:
    llm = _get_dep("llm")
    if not llm:
        return json.dumps({"error": "LLM未初始化"}, ensure_ascii=False)

    # 意图判断：记录 / 查询 / 删除
    prompt = f"""
判断用户意图：
- 记录日志：action = "log"
- 查询日志：action = "query"
- 删除日志：action = "delete"（需要日志id）

只返回JSON格式：
{{
    "action": "log/query/delete",
    "content": "内容",
    "log_id": 123
}}

用户问题：{query}
"""
    try:
        raw = llm.invoke(prompt, temperature=0.0)
        raw = raw.strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)

        action = data.get("action", "")
        content = data.get("content", "")
        log_id = data.get("log_id", None)

        # 连接你的数据库
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="123456",
            database="agri_pesticides_db",
            charset="utf8mb4"
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 1. 记录日志
        if action == "log":
            create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sql = "INSERT INTO farm_logs (content, create_time) VALUES (%s, %s)"
            cursor.execute(sql, (content, create_time))
            conn.commit()
            return json.dumps({
                "success": True,
                "msg": "日志已保存到数据库"
            }, ensure_ascii=False)

        # 2. 查询日志
        elif action == "query":
            cursor.execute("SELECT id, content, create_time FROM farm_logs ORDER BY id DESC LIMIT 30")
            logs = cursor.fetchall()
            return json.dumps({
                "success": True,
                "logs": logs
            }, ensure_ascii=False)

        # 3. 删除日志（新增）
        elif action == "delete":
            if not log_id:
                return json.dumps({"error": "请指定要删除的日志ID"}, ensure_ascii=False)

            sql = "DELETE FROM farm_logs WHERE id = %s"
            cursor.execute(sql, (log_id,))
            conn.commit()
            return json.dumps({
                "success": True,
                "msg": f"已删除日志 ID：{log_id}"
            }, ensure_ascii=False)

        else:
            return json.dumps({"error": "无法识别意图"}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"操作失败：{str(e)}"}, ensure_ascii=False)


# ====================== 农药推荐 ======================
# ====================== 数据库配置 ======================
# ====================== 农药推荐（宽松模糊搜索 · 最终版） ======================
import json
import re
import pymysql
import logging

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "agri_pesticides_db",
    "charset": "utf8mb4"
}

@Cached(pesticide_cache, ttl=1800)
def simple_drug_links(demand: str) -> str:
    """
    农药推荐流程：
    1. LLM 根据用户需求（病虫害+作物）推理出对症的药品名
    2. 用药品名去 MySQL 数据库模糊匹配，返回图片链接和购买链接
    """
    llm = _get_dep("llm")
    if llm is None:
        return json.dumps({"error": "LLM未初始化", "recommended_drugs": []}, ensure_ascii=False)

    # ============= Step 1: LLM 推理对症药品 =============
    prompt = f"""你是一名资深的农业植保专家。根据用户的病虫害描述，推荐 3~5 种对症的常用农药。

用户需求：{demand}

要求：
- 只输出药品名称，每行一个，不要序号、不要多余文字
- 推荐低毒、高效的常用农药
- 如果用户提到了具体作物，优先推荐该作物上登记的农药
- 如果拿不准，推荐广谱性农药
"""
    try:
        llm_result = llm.invoke(prompt, temperature=0.1)
        drug_names = [line.strip().replace("、", "").replace("，", "").replace("。", "")
                      for line in llm_result.strip().split("\n")
                      if line.strip() and not line.strip().startswith(("```", "以下是", "推荐", "根据"))]
        if not drug_names:
            logger.warning(f"LLM未推荐任何药品: {llm_result}")
            return json.dumps({"recommended_drugs": []}, ensure_ascii=False)
        logger.info(f"LLM推荐药品: {drug_names}")
    except Exception as e:
        logger.error(f"LLM推荐药品失败: {e}")
        return json.dumps({"error": "推荐药品失败", "recommended_drugs": []}, ensure_ascii=False)

    # ============= Step 2: 用药品名搜数据库 =============
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        all_drugs = []
        seen = set()
        for name in drug_names:
            cursor.execute(
                "SELECT drug_name, image_url, purchase_url FROM pesticides WHERE drug_name LIKE %s LIMIT 2",
                (f"%{name}%",),
            )
            for d in cursor.fetchall():
                key = d["drug_name"].strip()
                if key and key not in seen:
                    seen.add(key)
                    # 图片URL通过代理转发（绕过微信小程序域名白名单）
                    img = d.get("image_url", "")
                    if img and str(img).startswith("http"):
                        d["image_url"] = proxy_image_url(str(img))
                    all_drugs.append(d)

        cursor.close()
        conn.close()

        logger.info(f"数据库匹配到 {len(all_drugs)} 种药品: {[d['drug_name'] for d in all_drugs]}")
        return json.dumps({"recommended_drugs": all_drugs}, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"数据库搜索失败: {e}")
        return json.dumps({"error": "数据库查询失败", "recommended_drugs": []}, ensure_ascii=False)



# ====================== 农药信息网搜索 ======================
def search_nongyao001(keyword: str) -> str:
    searcher = _get_dep("searcher")
    if searcher is None:
        return json.dumps({"error": "searcher 未初始化"}, ensure_ascii=False)

    keyword = ensure_utf8_string(keyword)
    try:
        res = searcher.search_first_product(keyword)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"农药网搜索失败：{e}\n{traceback.format_exc()}")
        return json.dumps({"error": "搜索失败", "details": str(e)}, ensure_ascii=False)


# ====================== 农业文本提取 ======================
def agri_info_extract(text: str, fields: str) -> str:
    llm = _get_dep("llm")
    if llm is None:
        return json.dumps({"error": "LLM模型未初始化"}, ensure_ascii=False)

    text = ensure_utf8_string(text)
    fields = ensure_utf8_string(fields)

    prompt = f"""从文本提取信息：
    - 文本：{text}
    - 字段：{fields}
    - 返回JSON格式结果，仅输出JSON，无额外内容
    """
    try:
        res = llm.invoke(prompt, temperature=0.1)
        res = ensure_utf8_string(res)
        json.loads(res)  # 验证JSON格式
        return res
    except json.JSONDecodeError:
        return json.dumps({"extracted": res}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"文本提取失败：{e}\n{traceback.format_exc()}")
        return json.dumps({"error": "提取失败", "details": str(e)}, ensure_ascii=False)


# ====================== 农业数据分析 ======================
def agri_data_analysis(data: str, dimensions: str) -> str:
    llm = _get_dep("llm")
    if llm is None:
        return json.dumps({"error": "LLM模型未初始化"}, ensure_ascii=False)

    data = ensure_utf8_string(data)
    dimensions = ensure_utf8_string(dimensions)

    prompt = f"""分析以下农业数据，输出专业、易懂的分析结论：
    - 数据：{data}
    - 分析维度：{dimensions}
    """
    try:
        res = llm.invoke(prompt, temperature=0.5)
        return json.dumps({"analysis": ensure_utf8_string(res)}, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"数据分析失败：{e}\n{traceback.format_exc()}")
        return json.dumps({"error": "分析失败", "details": str(e)}, ensure_ascii=False)


# ====================== 向量数据库搜索 ======================
def vector_db_similarity_search(query: str, top_k: int = 3) -> str:
    agri_vector_db = _get_dep("agri_vector_db")
    if agri_vector_db is None:
        return json.dumps({"error": "向量库未初始化"}, ensure_ascii=False)

    query = ensure_utf8_string(query)
    try:
        ret = agri_vector_db.similarity_search(query, top_k)
        return json.dumps({"results": ret}, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"向量库搜索失败：{e}\n{traceback.format_exc()}")
        return json.dumps({"error": "搜索失败", "details": str(e)}, ensure_ascii=False)


# ====================== 增强版农业知识查询 ======================
@Cached(knowledge_cache, ttl=600)
def enhanced_agri_knowledge_query(question: str) -> str:
    llm = _get_dep("llm")
    agri_vector_db = _get_dep("agri_vector_db")

    if llm is None:
        return json.dumps({"error": "LLM模型未初始化"}, ensure_ascii=False)

    question = ensure_utf8_string(question)
    knowledge = []
    if agri_vector_db:
        try:
            r = agri_vector_db.similarity_search(question, 3)
            knowledge = [ensure_utf8_string(x.get("document", "")) for x in r]
        except Exception as e:
            logger.warning(f"向量库检索失败：{e}")

    ctx = "\n".join(f"- {x}" for x in knowledge) if knowledge else "无"
    prompt = f"""参考以下知识回答问题，回答需详细、专业、易懂：
    参考知识：{ctx}
    问题：{question}
    """
    try:
        ans = llm.invoke(prompt, temperature=0.3)
        return json.dumps({"answer": ensure_utf8_string(ans)}, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"增强版知识查询失败：{e}\n{traceback.format_exc()}")
        return json.dumps({"error": "查询失败", "details": str(e)}, ensure_ascii=False)


# ====================== 农药稀释计算器 ======================
def pesticide_dilute_calc(dosage: float, dilute_times: float) -> str:
    """
    农药稀释计算
    :param dosage: 用药量（克 / 毫升）
    :param dilute_times: 稀释倍数
    :return: 需要加多少 kg 水
    """
    try:
        if dosage <= 0 or dilute_times <= 0:
            return json.dumps({
                "success": False,
                "error": "用药量和稀释倍数必须大于0"
            }, ensure_ascii=False)

        # 核心公式：加水 kg = 药量(g) × 稀释倍数 ÷ 1000
        water_kg = (dosage * dilute_times) / 1000

        return json.dumps({
            "success": True,
            "function_name": "pesticide_dilute_calc",
            "result": {
                "用药量(g)": round(dosage, 2),
                "稀释倍数": int(dilute_times),
                "加水量(kg)": round(water_kg, 2)
            }
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"计算失败：{str(e)}"
        }, ensure_ascii=False)



# ====================== 和风天气城市ID映射表（避免GEO API 403问题） ======================
_QWEATHER_CITY_IDS = {
    # 直辖市
    "北京": "101010100", "北京市": "101010100", "北京城区": "101010100",
    "上海": "101020100", "上海市": "101020100",
    "天津": "101030100", "天津市": "101030100",
    "重庆": "101040100", "重庆市": "101040100",
    # 湖南
    "长沙": "101250101", "长沙市": "101250101", "长沙县": "101250102",
    "株洲": "101250301", "株洲市": "101250301",
    "湘潭": "101250201", "湘潭市": "101250201",
    "衡阳": "101250401", "衡阳市": "101250401",
    "邵阳": "101250901", "邵阳市": "101250901",
    "岳阳": "101251001", "岳阳市": "101251001",
    "常德": "101250601", "常德市": "101250601",
    "益阳": "101250701", "益阳市": "101250701",
    "郴州": "101250501", "郴州市": "101250501",
    "永州": "101251401", "永州市": "101251401",
    "怀化": "101251201", "怀化市": "101251201",
    "娄底": "101250801", "娄底市": "101250801",
    "湘西": "101251501", "湘西州": "101251501", "吉首": "101251501",
    # 广东
    "广州": "101280101", "广州市": "101280101",
    "深圳": "101280601", "深圳市": "101280601",
    "珠海": "101280701", "珠海市": "101280701",
    "东莞": "101281601", "东莞市": "101281601",
    "佛山": "101280301", "佛山市": "101280301",
    "中山": "101281701", "中山市": "101281701",
    "惠州": "101280301", "惠州市": "101280301",
    "汕头": "101280501", "汕头市": "101280501",
    "湛江": "101281001", "湛江市": "101281001",
    "韶关": "101280201", "韶关市": "101280201",
    # 浙江
    "杭州": "101210101", "杭州市": "101210101",
    "宁波": "101210401", "宁波市": "101210401",
    "温州": "101210701", "温州市": "101210701",
    "嘉兴": "101210301", "嘉兴市": "101210301",
    "湖州": "101210201", "湖州市": "101210201",
    "绍兴": "101210501", "绍兴市": "101210501",
    "金华": "101210901", "金华市": "101210901",
    "台州": "101210601", "台州市": "101210601",
    # 江苏
    "南京": "101190101", "南京市": "101190101",
    "苏州": "101190401", "苏州市": "101190401",
    "无锡": "101190201", "无锡市": "101190201",
    "常州": "101191101", "常州市": "101191101",
    "南通": "101190501", "南通市": "101190501",
    "徐州": "101190801", "徐州市": "101190801",
    "扬州": "101190601", "扬州市": "101190601",
    "镇江": "101190301", "镇江市": "101190301",
    # 四川
    "成都": "101270101", "成都市": "101270101",
    "绵阳": "101270401", "绵阳市": "101270401",
    "宜宾": "101271101", "宜宾市": "101271101",
    "德阳": "101272001", "德阳市": "101272001",
    "南充": "101270501", "南充市": "101270501",
    "泸州": "101271001", "泸州市": "101271001",
    # 湖北
    "武汉": "101200101", "武汉市": "101200101",
    "宜昌": "101200901", "宜昌市": "101200901",
    "襄阳": "101200201", "襄阳市": "101200201",
    "荆州": "101200801", "荆州市": "101200801",
    # 山东
    "济南": "101120101", "济南市": "101120101",
    "青岛": "101120201", "青岛市": "101120201",
    "烟台": "101120501", "烟台市": "101120501",
    "潍坊": "101120601", "潍坊市": "101120601",
    "临沂": "101120901", "临沂市": "101120901",
    "菏泽": "101121001", "菏泽市": "101121001",
    # 河南
    "郑州": "101180101", "郑州市": "101180101",
    "洛阳": "101180901", "洛阳市": "101180901",
    "南阳": "101180701", "南阳市": "101180701",
    "周口": "101181401", "周口市": "101181401",
    "驻马店": "101181601", "驻马店市": "101181601",
    # 河北
    "石家庄": "101090101", "石家庄市": "101090101",
    "唐山": "101090501", "唐山市": "101090501",
    "保定": "101090201", "保定市": "101090201",
    # 福建
    "福州": "101230101", "福州市": "101230101",
    "厦门": "101230201", "厦门市": "101230201",
    "泉州": "101230501", "泉州市": "101230501",
    # 广西
    "南宁": "101300101", "南宁市": "101300101",
    "桂林": "101300501", "桂林市": "101300501",
    # 其他省份主要城市
    "沈阳": "101070101", "沈阳市": "101070101",
    "大连": "101070201", "大连市": "101070201",
    "哈尔滨": "101050101", "哈尔滨市": "101050101",
    "长春": "101060101", "长春市": "101060101",
    "太原": "101100101", "太原市": "101100101",
    "西安": "101110101", "西安市": "101110101",
    "兰州": "101160101", "兰州市": "101160101",
    "西宁": "101150101", "西宁市": "101150101",
    "银川": "101170101", "银川市": "101170101",
    "乌鲁木齐": "101130101", "乌鲁木齐市": "101130101",
    "呼和浩特": "101080101", "呼和浩特市": "101080101",
    "昆明": "101290101", "昆明市": "101290101",
    "贵阳": "101260101", "贵阳市": "101260101",
    "南昌": "101240101", "南昌市": "101240101",
    "合肥": "101220101", "合肥市": "101220101",
    "拉萨": "101140101", "拉萨市": "101140101",
    "海口": "101310101", "海口市": "101310101",
    "香港": "101320101", "香港特别行政区": "101320101",
    "澳门": "101330101", "澳门特别行政区": "101330101",
    # 台湾
    "台北": "101340101", "台北市": "101340101",
}

# 省份城市前缀映射（用于模糊匹配：xx省xx市 → ID）
_QWEATHER_PROVINCE_CITY_MAP = {
    "湖南": "10125", "广东": "10128", "浙江": "10121", "江苏": "10119",
    "四川": "10127", "湖北": "10120", "山东": "10112", "河南": "10118",
    "河北": "10109", "福建": "10123", "广西": "10130", "辽宁": "10107",
    "黑龙江": "10105", "吉林": "10106", "山西": "10110", "陕西": "10111",
    "甘肃": "10116", "青海": "10115", "宁夏": "10117", "新疆": "10113",
    "内蒙古": "10108", "云南": "10129", "贵州": "10126", "江西": "10124",
    "安徽": "10122", "西藏": "10114", "海南": "10131",
}


def _resolve_qweather_location(region: str):
    """
    解析地区名称到和风天气 location_id 和 city_name。
    优先查内置映射表，查不到时尝试 GEO API（可能因权限失败）。
    """
    # 1. 精确查内置映射表
    region_stripped = region.strip().replace(" ", "")
    if region_stripped in _QWEATHER_CITY_IDS:
        loc_id = _QWEATHER_CITY_IDS[region_stripped]
        return loc_id, region_stripped

    # 2. 尝试"省+市"模式匹配（如"湖南省长沙市" → 查长沙的ID）
    import re
    city_match = re.search(r'省(.+?)市', region_stripped)
    if city_match:
        city = city_match.group(1)
        if city in _QWEATHER_CITY_IDS:
            return _QWEATHER_CITY_IDS[city], city

    # 3. 尝试从区域名中提取地级市关键词
    for city_name, loc_id in _QWEATHER_CITY_IDS.items():
        if len(city_name) <= 4 and city_name in region_stripped:
            # 命中如 "长沙" in "湖南省长沙市"
            return loc_id, city_name

    # 4. 尝试 GEO API（可能返回403，但保留作为兜底）
    try:
        geo_url = "https://mx2k5pfpbk.re.qweatherapi.com/geo/v2/city/lookup"
        geo_params = {"location": region, "key": QWEATHER_API_KEY, "range": "cn"}
        geo_res = requests.get(geo_url, params=geo_params, timeout=10)
        geo_data = geo_res.json()
        if geo_data.get("code") == "200" and geo_data.get("location"):
            loc = geo_data["location"][0]
            return loc["id"], loc["name"]
    except Exception as e:
        logger.warning(f"[QWeather] GEO API 尝试失败: {e}")

    return None, None


@Cached(weather_cache, ttl=180)
def _qweather(region: str):
    """调用和风天气API（v7），获取实时+7天预报+预警数据"""
    # 1. 解析地区到 location_id
    location_id, city_name = _resolve_qweather_location(region)
    if not location_id:
        logger.warning(f"[QWeather] 城市定位失败（GEO和内置表均无结果）：{region}")
        return None

    # 2. 实时天气
    now_res = requests.get("https://mx2k5pfpbk.re.qweatherapi.com/v7/weather/now", params={"location": location_id, "key": QWEATHER_API_KEY}, timeout=10)
    now_data = now_res.json()

    # 3. 7天天气预报
    daily_res = requests.get("https://mx2k5pfpbk.re.qweatherapi.com/v7/weather/7d", params={"location": location_id, "key": QWEATHER_API_KEY}, timeout=10)
    daily_data = daily_res.json()

    # 4. 天气预警
    warning_res = requests.get("https://mx2k5pfpbk.re.qweatherapi.com/v7/warning/now", params={"location": location_id, "key": QWEATHER_API_KEY}, timeout=10)
    warning_data = warning_res.json()

    return {
        "city": city_name,
        "now": now_data.get("now", {}),
        "daily": daily_data.get("daily", []),
        "warning": warning_data.get("warning", []),
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }


@Cached(weather_cache, ttl=180)
def _wttrin(region: str):
    """wttr.in 备用天气API（免费，无需 API KEY），获取实时+3天预报"""
    import urllib.parse
    url = f"https://wttr.in/{urllib.parse.quote(region)}?format=j1"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    current = data.get("current_condition", [{}])[0]
    daily = data.get("weather", [])
    area = data.get("nearest_area", [{}])[0]
    city_name = area.get("areaName", [{}])[0].get("value", region)

    daily_list = []
    for d in daily:
        hourly = d.get("hourly", [{}])
        daily_list.append({
            "fxDate": d.get("date", ""),
            "textDay": hourly[0].get("weatherDesc", [{}])[0].get("value", "未知") if hourly else "未知",
            "tempMin": d.get("mintempC", "--"),
            "tempMax": d.get("maxtempC", "--"),
            "precip": hourly[0].get("precipMM", "0") if hourly else "0",
        })

    return {
        "city": city_name,
        "now": {
            "temp": current.get("temp_C", "--"),
            "text": current.get("weatherDesc", [{}])[0].get("value", "未知"),
            "humidity": current.get("humidity", "--"),
            "windSpeed": current.get("windspeedKmph", "--"),
            "windDir": current.get("winddir16Point", ""),
            "feelsLike": current.get("FeelsLikeC", "--"),
        },
        "daily": daily_list,
        "warning": [],
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def get_real_weather(region: str):
    """获取天气数据：优先和风天气，失败自动降级到 wttr.in"""
    # 优先和风天气
    result = _qweather(region)
    if result is not None:
        logger.info(f"[天气] 使用和风天气API成功: {region}")
        return result
    
    # 降级到 wttr.in
    logger.warning(f"[天气] 和风天气API失败，降级到 wttr.in: {region}")
    try:
        result = _wttrin(region)
        if result is not None:
            logger.info(f"[天气] 使用 wttr.in 成功: {region}")
            return result
    except Exception as e:
        logger.error(f"[天气] wttr.in 也失败: {e}")
    
    return None


# ====================== 实时天气获取======================
@Cached(weather_cache, ttl=120)
def farm_weather_advice(query: str) -> str:
    """真实天气API + LLM农事建议工具"""
    llm = _get_dep("llm")
    if not llm:
        return json.dumps({"error": "LLM模型未初始化"}, ensure_ascii=False)

    # 1. 提取用户提问的地区
    extract_prompt = f"""
从用户问题中提取地区，只输出JSON，不要任何多余文字。
示例：{{"region":"山东菏泽"}}
问题：{query}
"""
    try:
        region_raw = llm.invoke(extract_prompt, temperature=0.0)
        region_data = json.loads(region_raw.strip().replace("```json","").replace("```",""))
        region = region_data.get("region", "").strip()
    except Exception as e:
        logger.error(f"地区提取失败：{str(e)}")
        return json.dumps({"error": "请明确指定地区（如：山东菏泽）"}, ensure_ascii=False)

    if not region:
        return json.dumps({"error": "未提取到有效地区"}, ensure_ascii=False)

    # 2. 调用真实天气API
    weather_data = get_real_weather(region)
    if not weather_data:
        return json.dumps({"error": f"无法获取【{region}】的天气数据，请检查网络或API权限"}, ensure_ascii=False)

    # 3. 拼接天气数据，交给LLM生成农事建议
    warning_str = "无极端天气预警"
    if weather_data["warning"]:
        warning_str = "\n".join([f"{w.get('title')}：{w.get('text')}" for w in weather_data["warning"]])

    daily_str = "\n".join([
        f"{d.get('fxDate')}：{d.get('textDay')}，气温{d.get('tempMin')}~{d.get('tempMax')}℃，降水{d.get('precip', '0')}mm"
        for d in weather_data["daily"]
    ])

    prompt = f"""
你是国家级农业气象与农事指导专家，根据以下真实天气数据，为农户生成专业、可落地的农事建议。

【地区】{weather_data['city']}
【数据更新时间】{weather_data['update_time']}
【实时天气】
天气：{weather_data['now'].get('text', '未知')}
温度：{weather_data['now'].get('temp', '未知')}℃
湿度：{weather_data['now'].get('humidity', '未知')}%
风速：{weather_data['now'].get('windSpeed', '未知')}km/h

【未来天气预报】
{daily_str}

【极端天气预警】
{warning_str}

请严格按照以下要求输出建议：
1.  分点说明：适宜农事（打药、施肥、浇水、除草、播种、收获等）
2.  分点说明：禁忌农事（绝对不能做的操作，如暴雨前打药、高温施肥）
3.  重点提醒：结合预警和天气，给出针对性防护建议
4.  语言通俗易懂，完全贴合农户实际生产场景
"""
    try:
        advice = llm.invoke(prompt).strip()
        return json.dumps({
            "success": True,
            "region": weather_data["city"],
            "weather_now": weather_data["now"],
            "weather_7d": weather_data["daily"],
            "warning": weather_data["warning"],
            "farm_advice": advice
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"LLM生成建议失败：{str(e)}")
        return json.dumps({"error": f"生成农事建议失败：{str(e)}"}, ensure_ascii=False)

# ====================== 病虫害高发期预报工具（联网搜索+大模型智能生成）======================
@Cached(knowledge_cache, ttl=900)
def pest_risk_forecast_online(region: str, crop: str, month: int) -> str:
    llm = _get_dep("llm")

    # ====================== ✅ 最强容错：有没有 searcher 都能跑 ======================
    try:
        searcher = _get_dep("searcher")
    except:
        searcher = None

    if llm is None:
        return json.dumps({"error": "LLM模型未初始化，无法生成预报"}, ensure_ascii=False)

    region = ensure_utf8_string(region)
    crop = ensure_utf8_string(crop)
    search_query = f"{region} {crop} {month}月份 病虫害高发期预报"

    # 安全搜索
    try:
        if searcher is not None:
            search_result = searcher.search_first_product(search_query)
            search_result = ensure_utf8_string(str(search_result))
        else:
            search_result = "使用农业植保专家经验（无搜索服务）"
    except Exception as e:
        logger.warning(f"搜索异常，使用专家经验: {e}")
        search_result = "根据全国农业植保专家经验生成权威预报"

    prompt = f"""
你是国家级农业植保专家，生成【{region} {crop} {month}月份 未来1-2周病虫害高发期预报】。

资料：
{search_result}

只输出JSON，不要任何多余文字：
{{
  "region": "{region}",
  "crop": "{crop}",
  "month": {month},
  "forecast_period": "未来1-2周",
  "risk_pests": [
    {{
      "name": "病虫害名称",
      "alert_level": "高/中/低",
      "occurrence_reason": "发生原因",
      "control_suggestion": "防治方法+农药"
    }}
  ],
  "overall_suggestion": "整体管理建议"
}}
"""

    try:
        result = llm.invoke(prompt, temperature=0.1)
        result_text = ensure_utf8_string(result.strip())
        result_text = result_text.replace("```json", "").replace("```", "").strip()

        import re
        match = re.search(r'(\{.*\})', result_text, re.DOTALL)
        clean_json = match.group(1) if match else result_text
        if not clean_json.endswith('}'):
            clean_json += '}'

        clean_json = re.sub(r',\s*}', '}', clean_json)
        clean_json = re.sub(r',\s*]', ']', clean_json)

        json_data = json.loads(clean_json)
        return json.dumps(json_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"预报失败: {e}")
        return json.dumps({
            "region": region,
            "crop": crop,
            "month": month,
            "forecast_period": "未来1-2周",
            "risk_pests": [],
            "overall_suggestion": "加强田间管理，预防为主"
        }, ensure_ascii=False)

# ====================== 给大模型调用的入口 ======================
def pesticide_dilute(query: str) -> str:
    """
    自然语言调用农药稀释计算器
    例如：用药30克，稀释500倍，需要加多少水？
    【纯本地计算，不调用LLM，不联网，永不超时】
    """
    import re
    # 本地提取数字，完全不调用模型
    nums = re.findall(r'\d+\.?\d*', query)
    if len(nums) < 2:
        return json.dumps({
            "success": False,
            "error": "未找到药量和稀释倍数"
        }, ensure_ascii=False)

    try:
        dosage = float(nums[0])
        dilute_times = float(nums[1])
        return pesticide_dilute_calc(dosage, dilute_times)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"解析失败：{str(e)}"
        }, ensure_ascii=False)
# ====================== 导出所有函数（供tools/__init__.py导入） ======================
__all__ = [
    "set_global_deps",
    "agri_knowledge_query",
    "pest_treatment_from_image",
    "simple_drug_links",
    "search_nongyao001",
    "agri_info_extract",
    "agri_data_analysis",
    "vector_db_similarity_search",
    "enhanced_agri_knowledge_query",
    "pesticide_dilute_calc",
    "pesticide_dilute",
    "pest_risk_forecast_online"

]