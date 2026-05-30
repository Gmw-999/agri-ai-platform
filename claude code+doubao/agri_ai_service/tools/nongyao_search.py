import re
import time
import random
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from config.settings import NONGYAO_BASE_URL, NONGYAO_SEARCH_PATH, NONGYAO_DEFAULT_TIMEOUT
from utils.common import ensure_utf8_string


class Nongyao001Searcher:
    """农药信息网搜索工具"""

    def __init__(self, timeout: int = NONGYAO_DEFAULT_TIMEOUT, use_proxy: bool = False):
        self.base_url = NONGYAO_BASE_URL
        self.search_path = NONGYAO_SEARCH_PATH
        self.timeout = timeout
        self.use_proxy = use_proxy
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        ]
        self.base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Connection": "keep-alive",
            "Referer": f"{self.base_url}/",
            "Upgrade-Insecure-Requests": "1",
            "Accept-Charset": "utf-8"
        }
        self.proxies = {
            'http': 'http://127.0.0.1:8080',
            'https': 'http://127.0.0.1:8080'
        } if use_proxy else None
        self.session = requests.Session()
        try:
            self.session.get(self.base_url, timeout=5, headers=self._get_headers())
        except:
            pass

    def _get_headers(self) -> Dict[str, str]:
        headers = self.base_headers.copy()
        headers["User-Agent"] = random.choice(self.user_agents)
        headers["Host"] = "www.nongyao001.com"
        return headers

    def _build_search_url(self, keyword: str) -> str:
        """构建搜索URL（UTF-8编码关键词）"""
        keyword = ensure_utf8_string(keyword)
        encoded_keyword = urllib.parse.quote(keyword)
        return f"{self.base_url}{self.search_path}?kw={encoded_keyword}"

    def _parse_first_product(self, soup: BeautifulSoup, search_url: str) -> Optional[Dict[str, str]]:
        """解析第一个商品信息"""
        product_items = soup.select("div.search-result-item") or soup.select("div.product-item")
        if not product_items:
            print("[解析失败] 未找到商品列表")
            return None

        first_item = product_items[0]
        # 提取商品名称
        name_tag = first_item.select_one("div.product-name a") or first_item.select_one("div.product-title a")
        if not name_tag:
            print("[解析失败] 未找到商品名称")
            return None
        product_name = name_tag.get_text(strip=True)

        # 提取商品链接
        link_tag = first_item.select_one("div.product-img a") or first_item.select_one("div.product-name a")
        if not link_tag:
            print("[解析失败] 未找到商品链接")
            return None
        product_url = link_tag.get("href", "")
        full_url = urllib.parse.urljoin(search_url, product_url)
        if "/product/" not in full_url:
            match = re.search(r'/product/(\d+)\.html', full_url) or re.search(r'productId=(\d+)', full_url)
            if match:
                full_url = f"{self.base_url}/product/{match.group(1)}.html"

        # 提取图片链接
        image_tag = first_item.select_one("div.product-img img")
        image_url = image_tag.get("src") or image_tag.get("data-src") or ""
        image_url = urllib.parse.urljoin(search_url, image_url) if image_url else ""

        return {
            "image_url": image_url,
            "purchase_url": full_url,
            "source": "农药信息网(nongyao001.com)",
            "product_name": product_name,
            "success": True
        }

    def search_first_product(self, keyword: str) -> Dict[str, Any]:
        """搜索并返回第一个商品信息"""
        keyword = ensure_utf8_string(keyword)
        print(f"[搜索] 关键词: {keyword}")
        search_url = self._build_search_url(keyword)

        for attempt in range(3):
            try:
                time.sleep(random.uniform(1, 2))
                response = self.session.get(
                    search_url,
                    headers=self._get_headers(),
                    timeout=self.timeout,
                    proxies=self.proxies
                )
                response.encoding = "utf-8"
                response.raise_for_status()

                if "搜索结果" not in response.text:
                    if any(word in response.text for word in ["登录", "注册"]):
                        return {"success": False, "error_message": "需要登录", "search_url": search_url}
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                result = self._parse_first_product(soup, search_url)
                if result:
                    return result
                time.sleep(2)

            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 403:
                    return {"success": False, "error_message": "被服务器拒绝", "search_url": search_url}
                time.sleep(3)
            except Exception as e:
                print(f"[错误] {str(e)}")
                time.sleep(3)

        return {
            "success": False,
            "error_message": "未找到商品",
            "product_name": keyword
        }