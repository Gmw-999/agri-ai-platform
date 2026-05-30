"""
药品链接增强器测试：正则提取、链接内联插入
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agent.drug_enricher import (
    _extract_drug_names_fallback,
    _inline_insert_links,
    _proxy_image_url,
)


class TestDrugNameExtraction:
    """药品名称正则提取测试"""

    def test_extract_from_book_title(self):
        """从书名号中提取药品名"""
        text = "建议使用《吡虫啉》和《多菌灵》进行防治"
        names = _extract_drug_names_fallback(text)
        assert "吡虫啉" in names, f"应提取吡虫啉，实际: {names}"
        assert "多菌灵" in names, f"应提取多菌灵，实际: {names}"

    def test_extract_from_dosage_form(self):
        """从剂型关键词前提取药品名"""
        text = "使用25%吡唑醚菌酯乳油进行防治"
        names = _extract_drug_names_fallback(text)
        assert any("吡唑醚菌酯" in n for n in names), f"应提取吡唑醚菌酯，实际: {names}"

    def test_extract_from_percentage_pattern(self):
        """从百分比模式提取药品名"""
        text = "推荐使用25%吡唑醚菌酯"
        names = _extract_drug_names_fallback(text)
        assert any("吡唑醚菌酯" in n for n in names), f"应提取吡唑醚菌酯，实际: {names}"

    def test_skip_common_words(self):
        """应跳过常见农业词汇 - 这些词汇不应被误识别为药品名"""
        # 使用明确的农业术语，不应被提取为药品名
        text = "建议加强田间管理及时喷洒"
        names = _extract_drug_names_fallback(text)
        # 确保没有将通用农业词汇误识别为药品
        for name in names:
            assert name not in ["建议", "加强", "田间管理", "及时", "喷洒"], \
                f"通用词汇不应被识别为药品: {name}"


class TestInlineLinkInsertion:
    """内联链接插入测试"""

    def test_insert_purchase_link_after_drug_name(self):
        """应在药品名后插入购买链接"""
        text = "建议使用吡虫啉进行防治"
        drug_info = {"drug_name": "吡虫啉", "purchase_url": "http://buy.com/p1", "image_url": ""}
        result = _inline_insert_links(text, "吡虫啉", drug_info)
        assert "点击购买" in result, f"应包含购买链接，实际: {result}"
        assert "http://buy.com/p1" in result, f"应包含购买URL，实际: {result}"

    def test_skip_when_link_already_exists(self):
        """当药品名后已有链接时，不应重复插入"""
        text = "使用吡虫啉[点击购买](http://existing.com)防治"
        drug_info = {"drug_name": "吡虫啉", "purchase_url": "http://new.com", "image_url": ""}
        result = _inline_insert_links(text, "吡虫啉", drug_info)
        assert "http://new.com" not in result, f"已有链接不应再插入新链接"

    def test_no_drug_name_no_change(self):
        """药品名不在文本中时，应返回原文本"""
        text = "正常防治建议"
        drug_info = {"drug_name": "不存在的药", "purchase_url": "http://x.com", "image_url": ""}
        result = _inline_insert_links(text, "不存在的药", drug_info)
        assert result == text, f"药品名不存在时应返回原文，实际: {result}"


class TestProxyImageUrl:
    """图片代理 URL 测试"""

    def test_proxy_http_url(self):
        """HTTP 图片 URL 应被代理"""
        url = "http://example.com/img.jpg"
        result = _proxy_image_url(url)
        assert "/api/proxy/image?url=" in result, f"应为代理URL, 实际: {result}"

    def test_non_http_url_unchanged(self):
        """非 HTTP URL 不应被修改"""
        result = _proxy_image_url("")
        assert result == ""
        result = _proxy_image_url("not-a-url")
        assert result == "not-a-url"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
