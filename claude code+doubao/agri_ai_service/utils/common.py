import json
import uuid
import sys
import io
from typing import Any, Dict, Union


def force_utf8_encoding():
    """强制标准输出/错误使用UTF-8编码"""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def ensure_utf8_string(text: Union[str, bytes]) -> str:
    """确保输入是UTF-8字符串"""
    if isinstance(text, bytes):
        return text.decode("utf-8", errors="replace")
    return text


def safe_json_loads(text: str) -> Dict[str, Any]:
    """安全解析JSON（处理UTF-8编码问题）"""
    try:
        return json.loads(text)
    except UnicodeDecodeError:
        text_utf8 = text.encode("utf-8", errors="replace").decode("utf-8")
        return json.loads(text_utf8)
    except json.JSONDecodeError:
        return {"raw": text, "error": "JSON解析失败"}


def generate_request_id() -> str:
    """生成唯一请求ID"""
    return str(uuid.uuid4())


def build_utf8_headers(content_type: str = "application/json") -> Dict[str, str]:
    """构建UTF-8编码的请求头"""
    headers = {
        "Content-Type": f"{content_type}; charset=utf-8",
        "Accept": "application/json; charset=utf-8",
        "Accept-Charset": "utf-8"
    }
    return headers