"""
LLM 工厂 - 全局统一管理大模型实例

使用方式：
    # 在应用启动时初始化（settings.py）
    LLMFactory.init_llm(provider="doubao", api_key="...", endpoint_id="...")

    # 在任何模块中获取 LLM 实例
    llm = LLMFactory.get_llm()

后续换大模型只需在 init_llm 时修改 provider 和对应参数，
所有业务代码无需改动。
"""
from typing import Optional
from core.base_llm import BaseLLM


class LLMFactory:
    """LLM 实例工厂（单例模式）"""

    _default_llm: Optional[BaseLLM] = None

    @classmethod
    def create_llm(cls, provider: str = "doubao", **kwargs) -> BaseLLM:
        """
        创建 LLM 实例（不注册为全局默认）。

        Args:
            provider: 大模型提供商，当前支持 "doubao"
            **kwargs: 传递给具体实现类的参数

        Returns:
            BaseLLM 实例
        """
        if provider == "doubao":
            from core.llm_wrapper import DoubaoLLM
            return DoubaoLLM(**kwargs)
        elif provider == "deepseek":
            from core.llm_deepseek import DeepSeekLLM
            return DeepSeekLLM(**kwargs)
        else:
            raise ValueError(
                f"不支持的 LLM 提供商: {provider}，当前支持: doubao, deepseek"
            )

    @classmethod
    def init_llm(cls, provider: str = "doubao", **kwargs) -> BaseLLM:
        """
        初始化全局默认 LLM 实例并返回。

        Args:
            provider: 大模型提供商
            **kwargs: 传递给具体实现类的参数

        Returns:
            创建的 BaseLLM 实例（同时也是全局默认实例）
        """
        cls._default_llm = cls.create_llm(provider, **kwargs)
        return cls._default_llm

    @classmethod
    def get_llm(cls) -> BaseLLM:
        """
        获取全局默认 LLM 实例。

        Returns:
            BaseLLM 实例

        Raises:
            RuntimeError: 如果尚未调用 init_llm()
        """
        if cls._default_llm is None:
            raise RuntimeError(
                "LLM 未初始化，请先在应用启动时调用 LLMFactory.init_llm()"
            )
        return cls._default_llm
