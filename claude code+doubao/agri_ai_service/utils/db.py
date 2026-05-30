"""
数据库连接工具 - SQLAlchemy 连接池版本
提供统一的 MySQL 连接池和操作接口。
所有数据库配置从 config/settings.py 统一读取。
"""
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

import pymysql
import pymysql.cursors
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool

from config.settings import get_db_config

logger = logging.getLogger("agri_ai.db")

# 引擎缓存: {database_name: engine}
_engines: Dict[str, Any] = {}


def _get_engine(database: str = None):
    """获取或创建 SQLAlchemy 引擎（带连接池）"""
    if database is None:
        from config.settings import DB_NAME_AGRI
        database = DB_NAME_AGRI

    if database not in _engines:
        cfg = get_db_config(database)
        pool_size = int(cfg.pop("pool_size", 5))
        max_overflow = int(cfg.pop("max_overflow", 10))
        pool_recycle = int(cfg.pop("pool_recycle", 3600))

        url = (
            f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
            f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
            f"?charset={cfg.get('charset', 'utf8mb4')}"
        )

        engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # 连接前检测有效性
            echo=False,
        )

        # 确保 pymysql 连接使用 utf8mb4
        @event.listens_for(engine, "connect")
        def set_charset(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("SET NAMES utf8mb4")
            cursor.execute("SET CHARACTER SET utf8mb4")
            cursor.execute("SET character_set_connection=utf8mb4")
            cursor.close()

        _engines[database] = engine
        logger.info(f"数据库引擎已创建: {database} (pool_size={pool_size})")

    return _engines[database]


@contextmanager
def get_conn(database: str = None):
    """获取数据库连接（上下文管理器，自动归还连接池）"""
    engine = _get_engine(database)
    conn = engine.raw_connection()
    try:
        yield conn
    finally:
        conn.close()


def query_all(sql: str, params: tuple = (), database: str = None) -> List[dict]:
    """查询多条记录"""
    with get_conn(database) as conn:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def query_one(sql: str, params: tuple = (), database: str = None) -> Optional[dict]:
    """查询单条记录"""
    rows = query_all(sql, params, database)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = (), database: str = None) -> int:
    """执行 INSERT/UPDATE/DELETE，返回影响行数"""
    with get_conn(database) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount


def execute_last_id(sql: str, params: tuple = (), database: str = None) -> int:
    """执行 INSERT，返回自增ID"""
    with get_conn(database) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid


def close_all():
    """关闭所有数据库引擎（优雅退出时调用）"""
    for name, engine in _engines.items():
        engine.dispose()
        logger.info(f"数据库引擎已关闭: {name}")
    _engines.clear()
