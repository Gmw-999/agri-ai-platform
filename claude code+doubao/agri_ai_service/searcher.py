import requests
import json
import logging

logger = logging.getLogger(__name__)

class Searcher:
    """
    联网搜索工具（真实可用，给你直接写好完整版）
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 5

    def search_first_product(self, query: str):
        """
        联网搜索病虫害、农药、植保信息（真实联网）
        """
        try:
            # 这里用公开的搜索接口，给你直接可用
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
            resp = self.session.get(url, timeout=5)
            data = resp.json()

            result = ""
            if data.get("Abstract"):
                result += data["Abstract"] + "\n"

            for item in data.get("RelatedTopics", [])[:2]:
                if item.get("Text"):
                    result += "- " + item["Text"] + "\n"

            if not result:
                return "暂无联网搜索结果，将根据农业植保专家经验生成方案"

            return result.strip()

        except Exception as e:
            logger.warning(f"搜索异常: {e}")
            return "搜索服务暂时不可用，使用农业专家经验"