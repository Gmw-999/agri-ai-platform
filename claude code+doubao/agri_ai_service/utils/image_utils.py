"""
图片预处理工具
- 图片格式验证、缩放、压缩
- Base64 编解码
- 超时兜底装饰器
- 预留：后续可接入 OpenCV 增强、归一化等预处理管线
"""
import base64
import io
import logging
import time
from functools import wraps
from typing import Callable, Optional, Tuple

logger = logging.getLogger("agri_ai.image")

# ====================== 超时兜底 ======================

def with_timeout(timeout_sec: float = 10.0):
    """超时兜底装饰器：超时则返回降级结果"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import threading
            result = [None]
            error = [None]

            def runner():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e

            t = threading.Thread(target=runner, daemon=True)
            t.start()
            t.join(timeout_sec)

            if t.is_alive():
                logger.warning(f"⏰ {func.__name__} 执行超时 ({timeout_sec}s)，返回降级结果")
                return {
                    "success": False,
                    "error": f"处理超时（>{timeout_sec}秒）",
                    "fallback": True,
                }

            if error[0]:
                raise error[0]

            return result[0]

        return wrapper

    return decorator


# ====================== 图片验证 ======================

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP"}
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB


def validate_image(image_data: bytes) -> Tuple[bool, str]:
    """验证图片格式和大小"""
    if not image_data:
        return False, "图片数据为空"

    if len(image_data) > MAX_IMAGE_SIZE:
        return False, f"图片过大（>{MAX_IMAGE_SIZE // 1024 // 1024}MB）"

    # 检查文件头
    magic = image_data[:8]
    if magic[:2] == b'\xff\xd8':
        pass  # JPEG
    elif magic[:8] == b'\x89PNG\r\n\x1a\n':
        pass  # PNG
    elif magic[:4] == b'RIFF':
        pass  # WEBP
    elif magic[:2] == b'BM':
        pass  # BMP
    else:
        return False, "不支持的图片格式（仅支持 JPEG/PNG/WEBP/BMP）"

    return True, ""


# ====================== 图片预处理 ======================

def preprocess_image(
    image_data: bytes,
    max_size: int = 1024,
    quality: int = 85,
    target_format: str = "JPEG",
) -> bytes:
    """
    图片预处理：缩放 + 压缩
    - max_size: 最长边最大像素
    - quality: JPEG 压缩质量 1-100
    - target_format: 输出格式
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_data))

        # 转为 RGB（RGBA → RGB）
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # 等比缩放
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # 压缩
        buf = io.BytesIO()
        img.save(buf, format=target_format, quality=quality, optimize=True)
        return buf.getvalue()

    except ImportError:
        logger.warning("PIL 未安装，跳过图片预处理")
        return image_data
    except Exception as e:
        logger.error(f"图片预处理失败: {e}")
        return image_data


# ====================== Base64 编解码 ======================

def image_to_base64(image_data: bytes, mime: str = "image/jpeg") -> str:
    """图片字节 → data URL"""
    return f"data:{mime};base64,{base64.b64encode(image_data).decode('utf-8')}"


def base64_to_image(b64_str: str) -> Tuple[Optional[bytes], Optional[str]]:
    """Base64 → 图片字节 + MIME 类型"""
    try:
        if "," in b64_str:
            header, data = b64_str.split(",", 1)
            mime = header.replace("data:", "").replace(";base64", "")
        else:
            data = b64_str
            mime = "image/jpeg"
        return base64.b64decode(data), mime
    except Exception as e:
        logger.error(f"Base64 解码失败: {e}")
        return None, None


# ====================== 图片信息提取 ======================

def get_image_info(image_data: bytes) -> dict:
    """提取图片元信息（尺寸、格式等）"""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_data))
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format or "unknown",
            "mode": img.mode,
            "size_bytes": len(image_data),
        }
    except Exception as e:
        logger.debug(f"图片信息提取失败: {e}")
        return {"error": str(e)}
