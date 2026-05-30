"""
农技知识库 API 路由
- 分类/搜索/详情/收藏/历史
"""
import json
import logging
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from utils.db import query_all, query_one, execute, execute_last_id

logger = logging.getLogger("agri_ai.api.knowledge")
router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


# ====================== 请求模型 ======================
class FavoriteReq(BaseModel):
    openid: str
    knowledge_id: int


class HistoryReq(BaseModel):
    openid: str
    knowledge_id: int


# ====================== 分类 ======================
@router.get("/categories")
def list_categories():
    """获取知识分类列表"""
    rows = query_all(
        "SELECT id, name, icon, sort_order FROM agri_knowledge_categories ORDER BY sort_order ASC"
    )
    return {"success": True, "data": rows}


# ====================== 列表/搜索 ======================
@router.get("/list")
def list_knowledge(
    category_id: Optional[int] = Query(None, description="分类ID"),
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """知识条目列表，支持分类筛选和关键词搜索"""
    where = ["1=1"]
    params = []

    if category_id:
        where.append("k.category_id = %s")
        params.append(category_id)

    if keyword:
        where.append("(k.title LIKE %s OR k.tags LIKE %s OR k.summary LIKE %s)")
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])

    where_sql = " AND ".join(where)
    offset = (page - 1) * page_size

    total = query_one(
        f"SELECT COUNT(*) AS cnt FROM agri_knowledge k WHERE {where_sql}", tuple(params)
    )["cnt"]

    rows = query_all(
        f"""SELECT k.id, k.category_id, k.title, k.cover_image, k.summary,
                   k.view_count, k.is_pest, c.name AS category_name
            FROM agri_knowledge k
            LEFT JOIN agri_knowledge_categories c ON k.category_id = c.id
            WHERE {where_sql}
            ORDER BY k.view_count DESC, k.id ASC
            LIMIT %s OFFSET %s""",
        tuple(params + [page_size, offset]),
    )

    return {
        "success": True,
        "data": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ====================== 详情 ======================
@router.get("/detail")
def get_detail(id: int = Query(..., description="知识条目ID"), openid: str = Query("")):
    """获取知识条目详情，同时记录浏览历史（如果提供openid）"""
    row = query_one(
        """SELECT k.*, c.name AS category_name
           FROM agri_knowledge k
           LEFT JOIN agri_knowledge_categories c ON k.category_id = c.id
           WHERE k.id = %s""",
        (id,),
    )
    if not row:
        return {"success": False, "error": "条目不存在"}

    # 解析 drugs JSON
    if row.get("drugs") and isinstance(row["drugs"], str):
        try:
            row["drugs"] = json.loads(row["drugs"])
        except json.JSONDecodeError:
            row["drugs"] = []

    # 增加浏览量
    execute("UPDATE agri_knowledge SET view_count = view_count + 1 WHERE id = %s", (id,))

    # 记录浏览历史
    if openid:
        try:
            # 去重：先删相同记录再插入
            execute(
                "DELETE FROM user_browse_history WHERE openid = %s AND knowledge_id = %s",
                (openid, id),
            )
            execute_last_id(
                "INSERT INTO user_browse_history (openid, knowledge_id) VALUES (%s, %s)",
                (openid, id),
            )
            # 只保留最近50条
            execute(
                """DELETE FROM user_browse_history
                   WHERE openid = %s AND id NOT IN (
                       SELECT id FROM (
                           SELECT id FROM user_browse_history
                           WHERE openid = %s ORDER BY created_at DESC LIMIT 50
                       ) tmp
                   )""",
                (openid, openid),
            )
        except Exception as e:
            logger.warning(f"记录浏览历史失败: {e}")

    return {"success": True, "data": row}


# ====================== 收藏 ======================
@router.post("/favorite")
def toggle_favorite(req: FavoriteReq):
    """切换收藏状态（已收藏则取消，未收藏则添加）"""
    existing = query_one(
        "SELECT id FROM user_favorites WHERE openid = %s AND knowledge_id = %s",
        (req.openid, req.knowledge_id),
    )
    if existing:
        execute("DELETE FROM user_favorites WHERE id = %s", (existing["id"],))
        return {"success": True, "data": {"favorited": False, "message": "已取消收藏"}}
    else:
        execute_last_id(
            "INSERT INTO user_favorites (openid, knowledge_id) VALUES (%s, %s)",
            (req.openid, req.knowledge_id),
        )
        return {"success": True, "data": {"favorited": True, "message": "收藏成功"}}


@router.get("/favorite/check")
def check_favorite(openid: str = Query(...), knowledge_id: int = Query(...)):
    """检查是否已收藏"""
    row = query_one(
        "SELECT id FROM user_favorites WHERE openid = %s AND knowledge_id = %s",
        (openid, knowledge_id),
    )
    return {"success": True, "data": {"favorited": row is not None}}


@router.get("/favorites")
def list_favorites(
    openid: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取用户收藏列表"""
    offset = (page - 1) * page_size
    total = query_one(
        "SELECT COUNT(*) AS cnt FROM user_favorites WHERE openid = %s", (openid,)
    )["cnt"]

    rows = query_all(
        """SELECT k.id, k.title, k.cover_image, k.summary, k.view_count, k.is_pest,
                  c.name AS category_name, f.created_at AS favorited_at
           FROM user_favorites f
           JOIN agri_knowledge k ON f.knowledge_id = k.id
           LEFT JOIN agri_knowledge_categories c ON k.category_id = c.id
           WHERE f.openid = %s
           ORDER BY f.created_at DESC
           LIMIT %s OFFSET %s""",
        (openid, page_size, offset),
    )

    return {"success": True, "data": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/favorites/ids")
def get_favorite_ids(openid: str = Query(...)):
    """获取用户所有收藏的ID列表（前端批量标记用）"""
    rows = query_all(
        "SELECT knowledge_id FROM user_favorites WHERE openid = %s", (openid,)
    )
    return {"success": True, "data": {"ids": [r["knowledge_id"] for r in rows]}}


# ====================== 浏览历史 ======================
@router.get("/history")
def list_history(
    openid: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取用户浏览历史"""
    offset = (page - 1) * page_size
    total = query_one(
        "SELECT COUNT(*) AS cnt FROM user_browse_history WHERE openid = %s", (openid,)
    )["cnt"]

    rows = query_all(
        """SELECT k.id, k.title, k.cover_image, k.summary, k.view_count, k.is_pest,
                  c.name AS category_name, h.created_at AS browsed_at
           FROM user_browse_history h
           JOIN agri_knowledge k ON h.knowledge_id = k.id
           LEFT JOIN agri_knowledge_categories c ON k.category_id = c.id
           WHERE h.openid = %s
           ORDER BY h.created_at DESC
           LIMIT %s OFFSET %s""",
        (openid, page_size, offset),
    )

    return {"success": True, "data": rows, "total": total, "page": page, "page_size": page_size}


@router.delete("/history")
def clear_history(openid: str = Query(...)):
    """清空某用户的浏览历史"""
    execute("DELETE FROM user_browse_history WHERE openid = %s", (openid,))
    return {"success": True, "message": "已清空历史"}
