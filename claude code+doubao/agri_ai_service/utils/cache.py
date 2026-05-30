"""
TTL 缓存工具
内存缓存，支持按时间自动过期，用于缓存天气、农药查询、知识问答等高频请求。
"""
import time
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("agri_ai.cache")


class TTLCache:
    """TTL 缓存（线程安全不需要额外锁，CPython GIL 保证 dict 操作原子性）"""

    def __init__(self, default_ttl: float = 300.0, max_size: int = 256):
        """
        Args:
            default_ttl: 默认过期时间（秒），默认 5 分钟
            max_size: 最大缓存条目数，超出时淘汰最旧的
        """
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._store: dict = {}  # key → (expire_at, value)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，已过期返回 None"""
        item = self._store.get(key)
        if item is None:
            return None
        expire_at, value = item
        if time.time() > expire_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """设置缓存"""
        expire_at = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._store[key] = (expire_at, value)
        self._evict_if_needed()

    def delete(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()

    def _evict_if_needed(self):
        """超出最大容量时淘汰最旧的 25%"""
        if len(self._store) > self._max_size:
            sorted_keys = sorted(self._store.keys(), key=lambda k: self._store[k][0])
            for k in sorted_keys[: self._max_size // 4]:
                del self._store[k]

    @property
    def size(self) -> int:
        return len(self._store)


class Cached:
    """
    装饰器风格的缓存包装，对函数结果进行 TTL 缓存。

    Usage:
        cache = TTLCache(default_ttl=600)

        @Cached(cache, ttl=120)
        def get_weather(region: str):
            # 实际请求...
            return result
    """

    def __init__(self, cache: TTLCache, ttl: Optional[float] = None, key_prefix: str = ""):
        self._cache = cache
        self._ttl = ttl
        self._key_prefix = key_prefix

    def __call__(self, func: Callable):
        def wrapper(*args, **kwargs):
            key = f"{self._key_prefix}{func.__name__}:{args}:{kwargs}"
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            # 不缓存失败结果（None、空dict等），避免故障持续
            if result is not None and result != {} and result != []:
                self._cache.set(key, result, self._ttl)
            return result
        return wrapper


# ====================== 全局缓存实例 ======================

# 天气查询缓存（3分钟，天气变化快）
weather_cache = TTLCache(default_ttl=180, max_size=64)

# 农药查询缓存（30分钟，农药数据几乎不变）
pesticide_cache = TTLCache(default_ttl=1800, max_size=128)

# 知识问答缓存（10分钟）
knowledge_cache = TTLCache(default_ttl=600, max_size=128)

# 视觉模型结果缓存（5分钟）
vision_cache = TTLCache(default_ttl=300, max_size=64)
