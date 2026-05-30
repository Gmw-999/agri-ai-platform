"""
DeepSeek 大模型封装（OpenAI 兼容接口）
- 通过 LangChain LLM 基类提供 invoke() 支持
- 通过 BaseLLM 抽象基类提供 chat() 支持
"""
import json
import requests
from typing import Any, List, Optional
from functools import lru_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

from core.base_llm import BaseLLM
from utils.common import ensure_utf8_string, safe_json_loads, build_utf8_headers, generate_request_id

DEEPSEEK_API_BASE = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_DEFAULT_TIMEOUT = 60
DEEPSEEK_DEFAULT_TEMPERATURE = 0.7
DEEPSEEK_DEFAULT_MAX_TOKENS = 2048


@lru_cache(maxsize=1)
def _get_global_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=1, backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"Connection": "keep-alive", "Accept-Encoding": "gzip, deflate"})
    return session


class DeepSeekLLM(LLM, BaseLLM):
    """DeepSeek 大模型实现（OpenAI 兼容接口）"""

    api_key: str
    model: str = "deepseek-chat"
    api_base: str = DEEPSEEK_API_BASE
    timeout: int = DEEPSEEK_DEFAULT_TIMEOUT

    _session: Optional[requests.Session] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session = _get_global_session()
        if not self.api_key:
            raise ValueError("DeepSeek API Key 未配置")

    @property
    def _llm_type(self) -> str:
        return "deepseek"

    def _build_payload(self, prompt: str, temperature: float, max_tokens: int, stop: Optional[List[str]] = None) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": ensure_utf8_string(prompt)}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop
        return payload

    def _perform_request(self, prompt: str, temperature: float, max_tokens: int, stop: Optional[List[str]] = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }
        payload = self._build_payload(prompt, temperature, max_tokens, stop)

        try:
            response = self._session.post(
                url=self.api_base, headers=headers, json=payload,
                timeout=self.timeout - 1, verify=False, stream=False,
            )
            response.raise_for_status()
            data = safe_json_loads(response.text)

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "").strip()
                if content:
                    return ensure_utf8_string(content)

            err_msg = data.get("error", {}).get("message", "空结果")
            raise ValueError(f"DeepSeek 返回空结果: {err_msg}")

        except requests.exceptions.HTTPError as e:
            detail = ensure_utf8_string(e.response.text) if e.response else ""
            code = e.response.status_code if e.response else 0
            errors = {401: f"鉴权失败: {detail}", 429: f"频率超限: {detail}"}
            raise ValueError(errors.get(code, f"HTTP {code}: {detail}"))
        except requests.exceptions.Timeout:
            raise ValueError(f"DeepSeek 请求超时 ({self.timeout}秒)")
        except requests.exceptions.ConnectionError:
            raise ValueError("DeepSeek 网络连接失败")
        except Exception as e:
            raise ValueError(f"DeepSeek 调用失败: {str(e)[:200]}")

    # ---- LangChain LLM 接口 ----
    def _call(self, prompt: str, stop: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs) -> str:
        temp = kwargs.get("temperature", 0.3)
        tokens = kwargs.get("max_tokens", 1024)
        return self._perform_request(prompt, temp, tokens, stop)

    # ---- BaseLLM 接口 ----
    def chat(self, prompt: str, temperature: float = None, max_tokens: int = None, stop: Optional[List[str]] = None, **kwargs) -> str:
        return self._perform_request(
            prompt,
            temperature if temperature is not None else 0.7,
            max_tokens if max_tokens is not None else 2048,
            stop,
        )

    def chat_fast(self, prompt: str) -> str:
        return self._perform_request(prompt, 0.1, 512)

    def chat_batch(self, prompts: List[str]) -> List[str]:
        return [self.chat_fast(p) for p in prompts]
