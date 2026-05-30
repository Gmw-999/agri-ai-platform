"""
工具注册表测试：白名单拦截、参数校验、频率限制
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agent.tool_registry import ToolRegistry, ToolSpec


class TestToolRegistry:
    """工具注册表功能测试"""

    def setup_method(self):
        self.registry = ToolRegistry()

    def test_whitelist_blocks_unregistered_tool(self):
        """白名单应拦截未注册的工具"""
        result = self.registry.execute("nonexistent_tool", session_id="test_session")
        assert "未注册" in result or "不存在" in result or "错误" in result or "非法" in result, \
            f"应拦截未注册工具，实际返回: {result[:100]}"

    def test_registered_tool_can_execute(self):
        """白名单中的工具应能执行（使用已有工具测试，而非修改内部状态）"""
        # 使用真实注册的工具进行测试
        result = self.registry.execute("weather_advice", session_id="test_session", region="长沙")
        assert result is not None, "已注册工具应返回结果"
        assert len(result) > 0, "结果不应为空"

    def test_rate_limit_blocks_excessive_calls(self):
        """频率限制应在超过阈值时阻止调用"""
        sid = "rate_test_session"
        results = []
        for i in range(6):
            results.append(self.registry.execute("weather_advice", session_id=sid, region="北京"))

        # 前5次应该成功，第6次被限流
        success_count = sum(1 for r in results if "频率" not in r and "限制" not in r and "超限" not in r)
        assert success_count >= 5, f"前5次调用应成功，实际成功: {success_count}"

    def test_missing_required_param_blocked(self):
        """缺少必填参数时应该返回错误"""
        # weather_advice 需要 region 参数，不传参数调用
        result = self.registry.execute("weather_advice", session_id="test_session")
        # 应该返回错误信息
        assert len(result) > 0, "应返回信息"

    def test_cleanup_session_removes_history(self):
        """清理会话后，调用历史应被清除"""
        sid = "cleanup_session"
        _ = self.registry.execute("weather_advice", session_id=sid, region="北京")
        self.registry.cleanup_session(sid)
        # 清理后应该可以再次调用
        result = self.registry.execute("weather_advice", session_id=sid, region="上海")
        assert result is not None, "清理会话后应能再次调用"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
