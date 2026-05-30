"""
数据库连接工具
提供统一的 MySQL 连接和操作接口。
所有数据库配置从 config/settings.py 统一读取，不再硬编码。
"""
import pymysql
import pymysql.cursors
import logging
from typing import Optional
from config.settings import get_db_config

logger = logging.getLogger("agri_ai.db")


def get_conn(database: str = None):
    """获取数据库连接，配置从环境变量读取"""
    config = get_db_config(database)
    config["cursorclass"] = pymysql.cursors.DictCursor
    return pymysql.connect(**config)


def query_all(sql: str, params: tuple = ()) -> list:
    """查询多条记录"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> Optional[dict]:
    """查询单条记录"""
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    """执行 INSERT/UPDATE/DELETE，返回影响行数"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_last_id(sql: str, params: tuple = ()) -> int:
    """执行 INSERT，返回自增ID"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
