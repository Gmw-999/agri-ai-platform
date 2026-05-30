"""
异步数据库连接工具 - SQLAlchemy asyncio 版本
提供统一的 MySQL 异步连接池和操作接口。
与 utils/db.py 的同步版本互为补充——异步版本用于 FastAPI 端点，同步版本用于工具函数。
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from config.settings import get_db_config

logger = logging.getLogger("agri_ai.db_async")

_async_engines: Dict[str, AsyncEngine] = {}
_async_session_factories: Dict[str, async_sessionmaker] = {}


def _get_async_engine(database: str = None) -> AsyncEngine:
    """获取或创建异步 SQLAlchemy 引擎"""
    if database is None:
        from config.settings import DB_NAME_AGRI
        database = DB_NAME_AGRI

    if database not in _async_engines:
        cfg = get_db_config(database)
        pool_size = 5
        max_overflow = 10

        url = (
            f"mysql+aiomysql://{cfg['user']}:{cfg['password']}"
            f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
            f"?charset={cfg.get('charset', 'utf8mb4')}"
        )

        engine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
        )
        _async_engines[database] = engine
        _async_session_factories[database] = async_sessionmaker(engine, expire_on_commit=False)
        logger.info(f"异步数据库引擎已创建: {database} (pool_size={pool_size})")

    return _async_engines[database]


async def query_all_async(sql: str, params: tuple = (), database: str = None) -> List[dict]:
    """异步查询多条记录"""
    engine = _get_async_engine(database)
    async with engine.connect() as conn:
        result = await conn.execute(text(sql), params)
        rows = result.fetchall()
        if rows:
            return [dict(row._mapping) for row in rows]
        return []


async def query_one_async(sql: str, params: tuple = (), database: str = None) -> Optional[dict]:
    """异步查询单条记录"""
    rows = await query_all_async(sql, params, database)
    return rows[0] if rows else None


async def execute_async(sql: str, params: tuple = (), database: str = None) -> int:
    """异步执行 INSERT/UPDATE/DELETE，返回影响行数"""
    engine = _get_async_engine(database)
    async with engine.connect() as conn:
        result = await conn.execute(text(sql), params)
        await conn.commit()
        return result.rowcount


async def execute_last_id_async(sql: str, params: tuple = (), database: str = None) -> int:
    """异步执行 INSERT，返回自增ID"""
    engine = _get_async_engine(database)
    async with engine.connect() as conn:
        result = await conn.execute(text(sql), params)
        await conn.commit()
        return result.lastrowid


async def close_all_async():
    """关闭所有异步数据库引擎"""
    for name, engine in _async_engines.items():
        await engine.dispose()
        logger.info(f"异步数据库引擎已关闭: {name}")
    _async_engines.clear()
    _async_session_factories.clear()
