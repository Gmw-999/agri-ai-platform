"""
药品链接增强器
从 Agent 回答中识别药品名称，到 MySQL 农药库查找对应药品，
直接在药品名称后插入图片和购买链接（内联模式），
同时支持仅在回答末尾汇总追加。
"""
import json
import logging
import re
from typing import List, Optional
from urllib.parse import quote

import pymysql
from config.settings import API_SERVER_BASE, get_db_config

logger = logging.getLogger("agri_ai.drug_enricher")

PROXY_IMAGE_BASE = f"{API_SERVER_BASE}/api/proxy/image?url="


def _proxy_image_url(url: str) -> str:
    """将外部图片URL重写为代理URL"""
    if not url or not url.startswith("http"):
        return url
    return PROXY_IMAGE_BASE + quote(url, safe="")

DB_CONFIG = get_db_config("agri_pesticides_db")


def _search_drug(keyword: str) -> List[dict]:
    """模糊搜索农药数据库，返回匹配的药品信息"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = """
        SELECT drug_name, image_url, purchase_url
        FROM pesticides
        WHERE drug_name LIKE %s
        LIMIT 3
        """
        cursor.execute(sql, (f"%{keyword}%",))
        drugs = cursor.fetchall()
        cursor.close()
        conn.close()
        return drugs
    except Exception as e:
        logger.warning(f"药品搜索失败 [{keyword}]: {e}")
        return []


def enrich_drug_links(reply: str) -> str:
    """
    从回复文本中识别药品名称，查找数据库并直接在药品名称后内联插入图片和购买链接。
    纯正则匹配，不走 LLM。

    Args:
        reply: Agent 生成的原始回复文本

    Returns:
        图片和购买链接已内联插入的增强回复
    """
    drug_names = _extract_drug_names_fallback(reply)
    if not drug_names:
        return reply

    # 去重后查询数据库
    seen = set()
    drug_map = {}  # 原始关键词 → 匹配到的药品信息
    for name in drug_names:
        normalized = name.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            drugs = _search_drug(name)
            for d in drugs:
                key = d["drug_name"].strip()
                if key and key not in drug_map:
                    drug_map[key] = d

    if not drug_map:
        return reply

    # 内联插入：在回复中找到药品名，在后面插入图片和购买链接
    enriched = reply
    for drug_name, drug_info in drug_map.items():
        enriched = _inline_insert_links(enriched, drug_name, drug_info)

    # 如果没有任何内联插入成功（药品名在回复中没出现），在末尾追加汇总
    if enriched == reply:
        link_lines = ["\n\n【推荐药品购买链接】"]
        for d in drug_map.values():
            parts = [f"**{d['drug_name']}**"]
            if d.get("image_url"):
                parts.append(f"![{d['drug_name']}]({_proxy_image_url(d['image_url'])})")
            if d.get("purchase_url"):
                parts.append(f"[点击购买]({d['purchase_url']})")
            link_lines.append(" | ".join(parts))
        enriched = reply + "\n".join(link_lines)

    return enriched


def _inline_insert_links(text: str, drug_name: str, drug_info: dict) -> str:
    """
    在文本中查找药品名，在其后方插入图片和购买链接 markdown。
    如果后方已有图片/链接标记则跳过，避免重复插入。
    """
    image_url = _proxy_image_url(drug_info.get("image_url", "") or "")
    purchase_url = drug_info.get("purchase_url", "") or ""
    if not image_url and not purchase_url:
        return text

    # 构建要插入的链接字符串
    link_parts = []
    if image_url:
        link_parts.append(f"![{drug_name}]({image_url})")
    if purchase_url:
        link_parts.append(f"[点击购买]({purchase_url})")
    link_suffix = " " + " ".join(link_parts)

    # 用药品名分割文本，在每个出现位置后面插入（除非后面已有链接）
    result_parts = []
    search_from = 0
    inserted_count = 0

    while True:
        idx = text.find(drug_name, search_from)
        if idx == -1:
            break

        after_idx = idx + len(drug_name)

        # 检查后面是否已经有图片或链接标记（避免重复插入）
        next_chars = text[after_idx:after_idx + 20]
        if "![" in next_chars[:5] or "[点击购买]" in next_chars[:15]:
            # 已有链接，跳过
            result_parts.append(text[search_from:after_idx])
        else:
            result_parts.append(text[search_from:after_idx])
            result_parts.append(link_suffix)
            inserted_count += 1

        search_from = after_idx

    result_parts.append(text[search_from:])

    if inserted_count > 0:
        return "".join(result_parts)
    return text  # 没插成功，返回原文本


# ====================== 药品名称提取 ======================


_DRUG_FORM_KEYWORDS = [
    "乳油", "悬浮剂", "水剂", "可湿性粉剂", "水分散粒剂",
    "颗粒剂", "粉剂", "微乳剂", "水乳剂", "烟剂",
    "颗粒", "油剂", "片剂",
]


def _extract_drug_names_fallback(reply: str) -> List[str]:
    """关键词回退模式：提取疑似药品名称"""
    names = set()

    # 模式1：书名号内的内容
    for match in re.findall(r"《([^》]+)》", reply):
        names.add(match.strip())

    # 模式2：数字+%+名称（如 "25%吡唑醚菌酯"）
    for match in re.findall(r"\d+%?\s*[一-鿿]+", reply):
        cleaned = match.strip()
        if len(cleaned) >= 2:
            names.add(cleaned)

    # 模式3：剂型关键词前面的内容
    for kw in _DRUG_FORM_KEYWORDS:
        for match in re.findall(rf"([一-鿿]{{2,8}}){kw}", reply):
            names.add(match.strip())

    # 模式4：常见农药名称模式
    for match in re.findall(r"[一-鿿·・]{2,8}", reply):
        skip_words = {
            "水稻", "小麦", "玉米", "大豆", "棉花", "果树", "蔬菜",
            "建议", "防治", "方法", "发生", "症状", "危害", "田间",
            "农业", "物理", "化学", "生物", "综合", "及时", "喷洒",
            "喷雾", "稀释", "倍数", "公斤", "毫升", "克水", "均匀",
            "作物", "病害", "虫害", "杂草", "以上", "以下", "左右",
            "晴天", "阴天", "雨后", "早晨", "傍晚", "上午", "下午",
        }
        if match not in skip_words and len(match) >= 2:
            names.add(match)

    return list(names)
