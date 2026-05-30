"""
火山方舟（豆包）大模型封装
- 继承 LangChain LLM 基类，保留完整 LangChain 兼容性
- 继承 BaseLLM 抽象基类，提供统一接口
- 通过 LLMFactory 全局管理实例
"""
import json
import requests
from typing import Any, List, Optional
from functools import lru_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# LangChain 核心导入
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

# 基类
from core.base_llm import BaseLLM

# 配置
from config.settings import (
    DOUBAO_API_BASE,
    DOUBAO_DEFAULT_TIMEOUT,
    DOUBAO_DEFAULT_TEMPERATURE,
    DOUBAO_DEFAULT_MAX_TOKENS,
)
from utils.common import (
    ensure_utf8_string,
    safe_json_loads,
    build_utf8_headers,
    generate_request_id,
)


# 全局会话复用（所有实例共享，减少连接建立开销）
@lru_cache(maxsize=1)
def _get_global_session() -> requests.Session:
    """创建并缓存全局请求会话，复用连接池"""
    session = requests.Session()

    retry_strategy = Retry(
        total=1,
        backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate",
    })
    return session


class DoubaoLLM(LLM, BaseLLM):
    """
    火山方舟（豆包）大模型实现
    - 通过 LangChain LLM 接口提供 _call() / invoke() 支持
    - 通过 BaseLLM 接口提供 chat() 支持
    - 两者共享底层 _perform_request() 实现
    """

    # LangChain Pydantic 字段声明
    api_key: str
    endpoint_id: str
    api_base: str = DOUBAO_API_BASE
    timeout: int = DOUBAO_DEFAULT_TIMEOUT
    debug: bool = False

    # 默认温度 / token 参数
    fast_temperature: float = DOUBAO_DEFAULT_TEMPERATURE
    fast_max_tokens: int = DOUBAO_DEFAULT_MAX_TOKENS

    # 私有属性
    _session: Optional[requests.Session] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session = _get_global_session()

        if not self.api_key:
            raise ValueError("豆包API Key未配置")
        if not self.endpoint_id:
            raise ValueError("推理接入点Endpoint ID未配置")

    @property
    def _llm_type(self) -> str:
        return "doubao"

    # ====================== 内部请求构建 ======================

    def _build_request_payload(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        stop: Optional[List[str]] = None,
    ) -> dict:
        """构建标准化请求体"""
        payload = {
            "model": self.endpoint_id,
            "messages": [{"role": "user", "content": ensure_utf8_string(prompt)}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "request_id": generate_request_id(),
        }
        if stop:
            payload["stop"] = stop
        return payload

    def _perform_request(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        stop: Optional[List[str]] = None,
    ) -> str:
        """底层 HTTP 请求（_call 和 chat 共享此方法）"""
        headers = build_utf8_headers()
        headers["Authorization"] = f"Bearer {self.api_key}"
        payload = self._build_request_payload(prompt, temperature, max_tokens, stop)

        if self.debug:
            print(
                f"[豆包LLM] 请求ID: {payload['request_id']} | "
                f"提示词长度: {len(prompt)}"
            )

        try:
            response = self._session.post(
                url=self.api_base,
                headers=headers,
                json=payload,
                timeout=self.timeout - 1,
                verify=True,
                stream=False,
            )

            response.raise_for_status()
            response_data = safe_json_loads(response.text)

            if "choices" in response_data and len(response_data["choices"]) > 0:
                content = ensure_utf8_string(
                    response_data["choices"][0]["message"]["content"].strip()
                )
                return content

            error_msg = ensure_utf8_string(
                response_data.get("error", {}).get("message", "未知错误")
            )
            raise ValueError(f"豆包大模型返回空结果: {error_msg}")

        except requests.exceptions.HTTPError as e:
            error_detail = (
                ensure_utf8_string(e.response.text)
                if e.response
                else "无响应详情"
            )
            error_code = e.response.status_code if e.response else 0
            error_map = {
                401: f"鉴权失败: {error_detail}",
                404: f"接入点不存在: {error_detail}",
                429: f"请求频率超限: {error_detail}",
                500: f"服务器内部错误: {error_detail}",
            }
            raise ValueError(
                error_map.get(error_code, f"HTTP错误: {error_code} - {error_detail}")
            )

        except requests.exceptions.Timeout:
            raise ValueError(f"请求超时（{self.timeout}秒）")

        except requests.exceptions.ConnectionError:
            raise ValueError("网络连接失败，请检查网络或API地址")

        except Exception as e:
            raise ValueError(f"豆包大模型调用失败: {str(e)[:100]}")

    # ====================== LangChain LLM 接口 ======================

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """LangChain 核心调用方法"""
        temperature = kwargs.get("temperature", self.fast_temperature)
        max_tokens = kwargs.get("max_tokens", self.fast_max_tokens)
        return self._perform_request(prompt, temperature, max_tokens, stop)

    # ====================== BaseLLM 接口 ======================

    def chat(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """BaseLLM 统一接口"""
        temp = self.fast_temperature if temperature is None else temperature
        tokens = self.fast_max_tokens if max_tokens is None else max_tokens
        return self._perform_request(prompt, temp, tokens, stop)

    def chat_fast(self, prompt: str) -> str:
        """快速对话 - 极低随机性，短输出"""
        return self._perform_request(prompt, 0.1, 512)

    def chat_batch(self, prompts: List[str]) -> List[str]:
        """批量对话"""
        results = []
        for prompt in prompts:
            try:
                results.append(self.chat_fast(prompt))
            except Exception as e:
                results.append(f"调用失败: {str(e)[:50]}")
        return results

    # ====================== 快捷方法（旧代码兼容） ======================

    def fast_invoke(self, prompt: str) -> str:
        """原有 fast_invoke 快捷方法（兼容旧代码）"""
        return self._perform_request(prompt, 0.1, 512)

    def batch_invoke(self, prompts: List[str]) -> List[str]:
        """原有 batch_invoke 快捷方法（兼容旧代码）"""
        return self.chat_batch(prompts)

    def __del__(self):
        """析构时释放会话资源"""
        if self._session:
            self._session.close()
