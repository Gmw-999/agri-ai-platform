"""
Agent Trace 可观测性系统
记录每次 Agent 对话的完整执行链路，包括：
- LLM Plan 步骤（prompt、返回的 tool plan）
- 每个工具的调用详情（名称、入参、返回值、耗时）
- Synthesize 步骤（回复内容）
- 总耗时和 token 估算

使用 SQLite 作为存储后端，无外部依赖。
"""
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("agri_ai.tracer")

# 北京时间时区
CST = timezone(timedelta(hours=8))

DB_PATH = Path(__file__).parent.parent / "data" / "traces.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """获取线程本地 SQLite 连接"""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
    return _local.conn


def _init_db():
    """初始化 Trace 数据库表"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS traces (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_query TEXT,
            has_image INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            total_duration_ms INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS trace_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            step_type TEXT NOT NULL,
            step_order INTEGER NOT NULL,
            input_data TEXT,
            output_data TEXT,
            duration_ms INTEGER,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (trace_id) REFERENCES traces(id)
        );
        CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id);
        CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at);
        CREATE INDEX IF NOT EXISTS idx_steps_trace ON trace_steps(trace_id);
    """)
    conn.commit()


_init_db()


class AgentTrace:
    """单次 Agent 调用的 Trace 记录器"""

    def __init__(self, session_id: str, user_query: str, has_image: bool = False):
        self.trace_id = str(uuid.uuid4())[:12]
        self.session_id = session_id
        self.user_query = user_query[:500]  # 截断长查询
        self.has_image = has_image
        self.steps: List[Dict] = []
        self._start_time = time.time()
        self._status = "running"

        # 写入 trace 记录
        try:
            conn = _get_conn()
            conn.execute(
                "INSERT INTO traces (id, session_id, user_query, has_image, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (self.trace_id, session_id, self.user_query, int(has_image), self._status)
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"写入 trace 记录失败: {e}")

    def log_step(
        self,
        step_type: str,
        step_order: int,
        input_data: Any = None,
        output_data: Any = None,
        duration_ms: int = 0,
        error: str = None,
    ):
        """记录一个执行步骤"""
        step = {
            "type": step_type,
            "order": step_order,
            "input": input_data,
            "output": output_data,
            "duration_ms": duration_ms,
            "error": error,
        }
        self.steps.append(step)

        # 异步写入数据库
        try:
            conn = _get_conn()
            conn.execute(
                "INSERT INTO trace_steps (trace_id, step_type, step_order, input_data, output_data, duration_ms, error, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    self.trace_id,
                    step_type,
                    step_order,
                    json.dumps(input_data, ensure_ascii=False, default=str)[:2000] if input_data else None,
                    json.dumps(output_data, ensure_ascii=False, default=str)[:5000] if output_data else None,
                    duration_ms,
                    error,
                )
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"写入 trace step 失败: {e}")

    def finish(self, status: str = "success"):
        """标记 trace 完成"""
        self._status = status
        total_ms = int((time.time() - self._start_time) * 1000)
        try:
            conn = _get_conn()
            conn.execute(
                "UPDATE traces SET status = ?, total_duration_ms = ? WHERE id = ?",
                (status, total_ms, self.trace_id)
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"更新 trace 状态失败: {e}")

    def fail(self, error: str):
        """标记 trace 失败"""
        self.log_step("error", len(self.steps), error=error)
        self.finish("error")


# ====================== 查询接口 ======================

def get_recent_traces(limit: int = 20) -> List[Dict]:
    """获取最近的 trace 列表"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, session_id, user_query, has_image, status, total_duration_ms, created_at "
        "FROM traces ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_trace_detail(trace_id: str) -> Optional[Dict]:
    """获取单个 trace 的详细信息（含所有步骤）"""
    conn = _get_conn()
    trace = conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
    if not trace:
        return None

    steps = conn.execute(
        "SELECT * FROM trace_steps WHERE trace_id = ? ORDER BY step_order",
        (trace_id,)
    ).fetchall()

    result = dict(trace)
    result["steps"] = [
        {
            "type": s["step_type"],
            "order": s["step_order"],
            "input": json.loads(s["input_data"]) if s["input_data"] else None,
            "output": json.loads(s["output_data"]) if s["output_data"] else None,
            "duration_ms": s["duration_ms"],
            "error": s["error"],
            "created_at": s["created_at"],
        }
        for s in steps
    ]
    return result


def get_trace_stats() -> Dict:
    """获取 trace 统计信息"""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM traces").fetchone()["c"]
    success = conn.execute("SELECT COUNT(*) as c FROM traces WHERE status='success'").fetchone()["c"]
    error = conn.execute("SELECT COUNT(*) as c FROM traces WHERE status='error'").fetchone()["c"]
    avg_duration = conn.execute(
        "SELECT AVG(total_duration_ms) as avg FROM traces WHERE total_duration_ms IS NOT NULL"
    ).fetchone()["avg"]

    # 工具调用分布
    tool_stats = conn.execute(
        "SELECT step_type, COUNT(*) as cnt, AVG(duration_ms) as avg_ms "
        "FROM trace_steps WHERE step_type='tool_call' "
        "GROUP BY step_type"
    ).fetchall()

    return {
        "total_traces": total,
        "success_rate": round(success / total * 100, 1) if total else 0,
        "error_count": error,
        "avg_duration_ms": round(avg_duration, 0) if avg_duration else 0,
    }
