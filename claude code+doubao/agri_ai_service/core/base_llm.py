"""
LLM 抽象基类
定义统一的大模型调用接口，所有大模型实现都必须继承此基类。
通过 LLMFactory 全局统一获取，后续换大模型只改配置，不动业务代码。
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional


class BaseLLM(ABC):
    """大模型抽象基类"""

    def __init__(self, **kwargs):
        # 接受 **kwargs 以兼容多继承场景下的协同 MRO
        super().__init__(**kwargs)

    @abstractmethod
    def chat(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """
        主对话方法 - 所有 LLM 调用的核心入口。

        Args:
            prompt: 输入提示词
            temperature: 温度参数（None 则使用实现类的默认值）
            max_tokens: 最大输出 token 数（None 则使用实现类的默认值）
            stop: 停止词列表
            **kwargs: 各实现类特有的额外参数

        Returns:
            模型生成的文本
        """
        ...

    @abstractmethod
    def chat_fast(self, prompt: str) -> str:
        """
        快速对话 - 低温度、短输出，适用于意图识别等简单场景。
        """
        ...

    @abstractmethod
    def chat_batch(self, prompts: List[str]) -> List[str]:
        """
        批量对话 - 依次处理多个 prompt，返回结果列表。
        """
        ...

    # ====================== 兼容旧接口 ======================
    # 项目中已有的调用方式：llm.invoke(prompt, temperature=0.3)
    # 和 self.llm(prompt, temperature=0) 全部代理到 chat()

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        """兼容已有代码中的 llm.invoke() 调用"""
        return self.chat(prompt, **kwargs)

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        """兼容已有代码中的 self.llm() 直接调用"""
        return self.chat(prompt, **kwargs)
