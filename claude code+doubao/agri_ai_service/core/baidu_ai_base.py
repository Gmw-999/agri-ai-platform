import time
import requests
from typing import Optional
from config.settings import BAIDU_TOKEN_URL, BAIDU_DEFAULT_TIMEOUT
from utils.common import ensure_utf8_string, build_utf8_headers


class BaiduAIUtils:
    """百度AI工具基础类：获取/缓存access_token"""

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token: Optional[str] = None
        self.token_expire_time = 0  # token过期时间戳

    def get_access_token(self) -> str:
        """获取有效access_token（过期自动刷新）"""
        current_time = time.time()
        # 检查token是否有效（预留60秒缓冲）
        if self.access_token and current_time < self.token_expire_time - 60:
            return self.access_token

        # 重新获取token
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }

        try:
            response = requests.get(
                BAIDU_TOKEN_URL,
                params=params,
                timeout=BAIDU_DEFAULT_TIMEOUT
            )
            response.encoding = "utf-8"
            response.raise_for_status()
            response_data = response.json()

            if "access_token" not in response_data:
                error_desc = ensure_utf8_string(response_data.get("error_description", "未知错误"))
                raise ValueError(f"百度AI Token获取失败: {error_desc}")

            self.access_token = response_data["access_token"]
            self.token_expire_time = current_time + response_data["expires_in"]
            print(f"[百度AI] Token获取成功，有效期至: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.token_expire_time))}")
            return self.access_token

        except Exception as e:
            raise ValueError(f"百度AI Token请求失败: {str(e)}")