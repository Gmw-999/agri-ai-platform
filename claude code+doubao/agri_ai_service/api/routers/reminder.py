"""
农事提醒 API 路由
- 提醒增删改查、农事日历、病虫害预警、天气农事建议
"""
import logging
import json
from datetime import datetime, date
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from utils.db import query_all, query_one, execute, execute_last_id

logger = logging.getLogger("agri_ai.api.reminder")
router = APIRouter(prefix="/api/reminder", tags=["农事提醒"])


# ====================== 请求模型 ======================
class ReminderReq(BaseModel):
    openid: str
    title: str
    content: str = ""
    remind_date: str  # YYYY-MM-DD
    remind_time: str = "08:00"
    remind_type: str = "custom"
    crop_type: str = ""


class ReminderUpdateReq(BaseModel):
    id: int
    title: Optional[str] = None
    content: Optional[str] = None
    remind_date: Optional[str] = None
    remind_time: Optional[str] = None
    remind_type: Optional[str] = None
    crop_type: Optional[str] = None
    status: Optional[str] = None


# ====================== 提醒 CRUD ======================
@router.get("/list")
def list_reminders(
    openid: str = Query(...),
    status: str = Query("", description="筛选状态：pending/completed/cancelled"),
    date_from: str = Query(""),
    date_to: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """获取用户的提醒列表"""
    where = ["openid = %s"]
    params = [openid]

    if status:
        where.append("status = %s")
        params.append(status)
    if date_from:
        where.append("remind_date >= %s")
        params.append(date_from)
    if date_to:
        where.append("remind_date <= %s")
        params.append(date_to)

    where_sql = " AND ".join(where)
    offset = (page - 1) * page_size

    total = query_one(
        f"SELECT COUNT(*) AS cnt FROM agri_reminders WHERE {where_sql}", tuple(params)
    )["cnt"]

    rows = query_all(
        f"""SELECT id, openid, title, content, remind_date, remind_time,
                   remind_type, crop_type, status, created_at
            FROM agri_reminders
            WHERE {where_sql}
            ORDER BY remind_date ASC, remind_time ASC
            LIMIT %s OFFSET %s""",
        tuple(params + [page_size, offset]),
    )

    # 转换 timedelta → "HH:MM" 字符串，避免前端 .slice() 报错
    from datetime import timedelta
    for row in rows:
        if isinstance(row.get("remind_time"), timedelta):
            s = int(row["remind_time"].total_seconds())
            row["remind_time"] = f"{s // 3600:02d}:{(s % 3600) // 60:02d}"
        if hasattr(row.get("remind_date"), "isoformat"):
            row["remind_date"] = row["remind_date"].isoformat()

    return {"success": True, "data": rows, "total": total}


@router.post("/create")
def create_reminder(req: ReminderReq):
    """创建新提醒"""
    rid = execute_last_id(
        """INSERT INTO agri_reminders (openid, title, content, remind_date, remind_time, remind_type, crop_type)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (req.openid, req.title, req.content, req.remind_date, req.remind_time, req.remind_type, req.crop_type),
    )
    return {"success": True, "data": {"id": rid, "message": "提醒创建成功"}}


@router.put("/update")
def update_reminder(req: ReminderUpdateReq):
    """更新提醒（只传需要改的字段）"""
    fields = []
    params = []
    for field in ["title", "content", "remind_date", "remind_time", "remind_type", "crop_type", "status"]:
        val = getattr(req, field, None)
        if val is not None:
            fields.append(f"{field} = %s")
            params.append(val)

    if not fields:
        return {"success": False, "error": "没有要更新的字段"}

    params.append(req.id)
    execute(
        f"UPDATE agri_reminders SET {', '.join(fields)} WHERE id = %s",
        tuple(params),
    )
    return {"success": True, "message": "更新成功"}


@router.delete("/delete")
def delete_reminder(id: int = Query(...)):
    """删除提醒"""
    execute("DELETE FROM agri_reminders WHERE id = %s", (id,))
    return {"success": True, "message": "已删除"}


# ====================== 日历 ======================
@router.get("/calendar")
def get_calendar(openid: str = Query(...), year: int = Query(0), month: int = Query(0)):
    """获取某月的提醒日历数据，返回该月每天是否有提醒"""
    today = date.today()
    y = year or today.year
    m = month or today.month

    rows = query_all(
        """SELECT remind_date, COUNT(*) AS cnt
           FROM agri_reminders
           WHERE openid = %s
             AND YEAR(remind_date) = %s AND MONTH(remind_date) = %s
             AND status = 'pending'
           GROUP BY remind_date
           ORDER BY remind_date""",
        (openid, y, m),
    )

    day_map = {str(r["remind_date"]): r["cnt"] for r in rows}

    # 生成该月所有日期
    import calendar as cal_mod
    days_in_month = cal_mod.monthrange(y, m)[1]
    calendar_data = []
    for d in range(1, days_in_month + 1):
        date_str = f"{y:04d}-{m:02d}-{d:02d}"
        calendar_data.append({"date": date_str, "count": day_map.get(date_str, 0)})

    return {"success": True, "data": calendar_data, "year": y, "month": m}


# ====================== 病虫害预警 ======================
@router.get("/pest-warnings")
def list_pest_warnings(
    region: str = Query("", description="地区"),
    crop: str = Query("", description="作物"),
    limit: int = Query(20, ge=1, le=100),
):
    """获取病虫害预警列表"""
    where = ["1=1"]
    params = []

    if region:
        where.append("(region LIKE %s OR %s = '')")
        params.extend([f"%{region}%", region])
    if crop:
        where.append("(crop LIKE %s OR %s = '')")
        params.extend([f"%{crop}%", crop])

    where_sql = " AND ".join(where)
    rows = query_all(
        f"""SELECT id, region, crop, pest_name, warning_level, description,
                   prevention_measures, start_date, end_date, source, created_at
            FROM pest_warnings
            WHERE {where_sql}
            ORDER BY FIELD(warning_level,'extreme','high','medium','low'),
                     start_date ASC
            LIMIT %s""",
        tuple(params + [limit]),
    )

    return {"success": True, "data": rows}


# ====================== 天气农事建议 ======================
@router.get("/weather-advice")
def get_weather_advice(region: str = Query("长沙")):
    """获取当前天气的农事建议（基于已有天气工具）"""
    try:
        from tools.agri_tools import farm_weather_advice
        result = farm_weather_advice(f"{region}今天天气怎么样，适合打药吗")
        # farm_weather_advice 返回完整JSON，提取纯文本建议
        data = json.loads(result) if isinstance(result, str) else result
        advice = data.get("farm_advice", data.get("error", "暂无建议"))
        return {"success": True, "data": {"advice": advice}}
    except Exception as e:
        logger.error(f"获取农事天气建议失败: {e}")
        return {"success": False, "error": str(e)}


class CreateFromAdviceReq(BaseModel):
    openid: str
    diagnosis: str = ""
    drugs_info: str = ""
    image_base64: str = ""


@router.post("/create-from-advice")
def create_from_advice(req: CreateFromAdviceReq):
    """
    从AI诊断结果自动创建农事提醒 + 备份日志
    1. LLM 提取病虫害名称、防治日期
    2. 创建提醒
    3. 写入诊断日志
    """
    try:
        from config.settings import llm

        # 用 LLM 提取结构化信息
        extract_prompt = f"""你是一个农业助手，请从以下AI诊断结果中提取关键信息，输出JSON格式（只输出JSON，不要多余文字）：

{{
    "disease_name": "病害名称",
    "drug_names": ["药1", "药2"],
    "suggested_action": "具体农事操作描述"
}}

诊断结果：
{req.diagnosis[:1000]}
"""
        try:
            raw = llm.invoke(extract_prompt, temperature=0.1)
            import re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            parsed = json.loads(match.group()) if match else {"disease_name": "病虫害防治", "drug_names": [], "suggested_action": req.diagnosis[:100]}
        except Exception:
            parsed = {"disease_name": "病虫害防治", "drug_names": [], "suggested_action": req.diagnosis[:100]}

        disease_name = parsed.get("disease_name", "病虫害防治")
        drug_names = parsed.get("drug_names", [])
        action_text = parsed.get("suggested_action", req.diagnosis[:100])

        # 构建提醒标题和内容
        title = f"{disease_name} - 防治提醒"
        content = action_text
        if drug_names:
            content += "\n推荐用药：" + "、".join(drug_names)

        # 提醒日期：默认明天
        from datetime import timedelta
        remind_date = (date.today() + timedelta(days=1)).isoformat()

        # 创建提醒
        remind_id = execute_last_id(
            """INSERT INTO agri_reminders (openid, title, content, remind_date, remind_time, remind_type, crop_type)
               VALUES (%s, %s, %s, %s, '08:00', 'pesticide', %s)""",
            (req.openid, title, content, remind_date, disease_name.split(" ")[0] if " " in disease_name else ""),
        )

        # 写入诊断日志
        log_id = execute_last_id(
            """INSERT INTO agri_advice_logs (openid, image_base64, diagnosis, drugs_info, reminder_id)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                req.openid,
                req.image_base64[:50000] if req.image_base64 else "",
                req.diagnosis[:2000],
                json.dumps({"drug_names": drug_names, "extracted_disease": disease_name}, ensure_ascii=False),
                remind_id,
            ),
        )

        return {
            "success": True,
            "data": {
                "reminder_id": remind_id,
                "log_id": log_id,
                "title": title,
                "content": content,
                "remind_date": remind_date,
                "remind_time": "08:00",
            },
            "message": "农事提醒已创建",
        }

    except Exception as e:
        logger.error(f"❌ 从诊断创建提醒失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
