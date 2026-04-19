# discover_sources_selenium.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from urllib.parse import urlparse
import re

# 关键词列表
SEARCH_QUERIES = [
    "site:gz.gov.cn 书记员 招聘",
    "site:gz.gov.cn 法官助理 招聘",
    "site:gz.gov.cn 司法辅助 招聘",
    "site:gz.gov.cn 法律援助中心 招聘",
    "site:gz.gov.cn 公共法律服务中心 招聘",
]

# 包含/排除关键字
INCLUDE_KEYWORDS = ["招聘", "招录", "招募", "书记员", "法官助理", "司法辅助", "法律援助", "公共法律服务"]
EXCLUDE_KEYWORDS = ["培训", "采购", "中标", "公示名单", "成绩", "体检", "递补"]

def is_candidate_url(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc:
        return False
    return parsed.netloc.endswith(".gov.cn") or "court" in parsed.netloc

def is_candidate_title(title: str) -> bool:
    if not title:
        return False
    if not any(k in title for k in INCLUDE_KEYWORDS):
        return False
    if any(k in title for k in EXCLUDE_KEYWORDS):
        return False
    return True

def main():
    # Selenium 设置
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)

    all_candidates = []

    for query in SEARCH_QUERIES:
        print(f"搜索关键词: {query}")
        driver.get(f"https://www.bing.com/search?q={query}")

        # 等待加载页面后抓取结果
        results = driver.find_elements(By.CSS_SELECTOR, "li.b_algo h2 a")
        for a in results:
            title = a.text.strip()
            href = a.get_attribute("href").strip()
            if is_candidate_title(title) and is_candidate_url(href):
                candidate = {
                    "name": title,
                    "url": href,
                    "publisher": "待确认",  # 可人工或后续解析页面补充
                    "org_type": "待确认",
                    "region": "广州",
                }
                all_candidates.append(candidate)

    driver.quit()

    # 去重
    unique_candidates = {c["url"]: c for c in all_candidates}.values()

    print(f"\n发现候选来源 {len(unique_candidates)} 条:")
    for c in unique_candidates:
        print("-" * 80)
        print(f"name: '{c['name']}', url: '{c['url']}', publisher: '{c['publisher']}', org_type: '{c['org_type']}', region: '{c['region']}'")

    # 生成可直接加入 SOURCES.py 的格式
    print("\n复制下面的字典到 SOURCES.py：")
    for c in unique_candidates:
        print(f"""{{"name": "{c['name']}", "url": "{c['url']}", "publisher": "{c['publisher']}", "org_type": "{c['org_type']}", "region": "{c['region']}", "detail_url_pattern": r"/"}},""")

if __name__ == "__main__":
    main()