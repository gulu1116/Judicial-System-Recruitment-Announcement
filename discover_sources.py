# discover_sources.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

SEARCH_QUERIES = [
    "site:gov.cn 广州 法院 招聘",
    "site:gov.cn 广州 书记员 招聘",
    "site:gov.cn 广州 法官助理 招聘",
    "site:gov.cn 广州 司法辅助 招聘",
    "site:gov.cn 广州 司法局 招聘",
    "site:gov.cn 广州 法律援助中心 招聘",
    "site:gov.cn 广州 公共法律服务中心 招聘",
]

INCLUDE_KEYWORDS = [
    "招聘", "招录", "招募", "书记员", "法官助理", "司法辅助",
    "司法局", "法律援助", "公共法律服务"
]

EXCLUDE_KEYWORDS = [
    "培训", "采购", "中标", "公示名单", "成绩", "体检", "递补"
]

session = requests.Session()
session.trust_env = False
session.proxies = {
    "http": None,
    "https": None,
}


def is_candidate_url(url: str) -> bool:
    parsed = urlparse(url)

    if not parsed.netloc:
        return False

    # 第一版只收官方/政府倾向来源
    if not (
        parsed.netloc.endswith(".gov.cn")
        or "court" in parsed.netloc
        or "jcy" in parsed.netloc
    ):
        return False

    return True


def is_candidate_title(title: str) -> bool:
    if not title:
        return False

    if not any(k in title for k in INCLUDE_KEYWORDS):
        return False

    if any(k in title for k in EXCLUDE_KEYWORDS):
        return False

    return True


def search_bing(query: str) -> list[dict]:
    """
    第一版用 Bing 搜索页面做候选发现。
    注意：搜索页面结构可能变化，所以它只适合作为“发现候选”，不适合作为核心稳定数据源。
    """
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for item in soup.select("li.b_algo"):
        a = item.select_one("h2 a[href]")
        if not a:
            continue

        title = a.get_text(" ", strip=True)
        link = a.get("href", "").strip()

        if not is_candidate_title(title):
            continue

        if not is_candidate_url(link):
            continue

        results.append({
            "title": title,
            "url": link,
            "query": query,
        })

    return results


def main():
    all_results = []

    for query in SEARCH_QUERIES:
        print("搜索:", query)
        try:
            results = search_bing(query)
            all_results.extend(results)
        except Exception as e:
            print("搜索失败:", query, e)

    dedup = {}
    for item in all_results:
        dedup[item["url"]] = item

    candidates = list(dedup.values())

    print(f"发现候选链接 {len(candidates)} 条")
    for item in candidates:
        print("-" * 80)
        print("标题:", item["title"])
        print("链接:", item["url"])
        print("关键词:", item["query"])


if __name__ == "__main__":
    main()