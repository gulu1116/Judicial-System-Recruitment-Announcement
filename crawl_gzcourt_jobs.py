import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from feishu_api import add_record, get_existing_links, get_token

LIST_URL = "https://www.gzcourt.gov.cn/fygg/zpgg/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.trust_env = False
session.proxies = {
    "http": None,
    "https": None,
}

def fetch_list_page(url: str) -> str:
    resp = session.get(url, headers=HEADERS, timeout=20)
    print("status:", resp.status_code)
    print("final url:", resp.url)
    resp.raise_for_status()

    if not resp.encoding or resp.encoding.lower() in {"iso-8859-1", "ascii"}:
        resp.encoding = resp.apparent_encoding

    return resp.text

def parse_list(html: str):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.select("a[href]"):
        title = a.get_text(" ", strip=True)
        href = a.get("href", "").strip()

        if not title or not href:
            continue

        # 必须包含招聘类关键词
        if not any(k in title for k in ["招聘", "招募", "招录"]):
            continue

        # 排除非招聘公告
        if any(k in title for k in ["公示", "名单", "成绩", "体检", "递补", "资格审核"]):
            continue

        full_url = urljoin(LIST_URL, href)
        # 只保留具体公告页
        if not re.search(r"/\d{4}/\d{2}/\d+\.html$", full_url):
            continue

        date_text = ""
        parent_text = a.parent.get_text(" ", strip=True)
        m = re.search(r"\d{4}-\d{2}-\d{2}", parent_text)
        if m:
            date_text = m.group(0)

        results.append({
            "公告标题": title,
            "发布时间": date_text,
            "公告链接": full_url,
            "发布机关": "广州法院系统",
        })

    dedup = {}
    for item in results:
        dedup[item["公告链接"]] = item
    return list(dedup.values())

def main():
    token = get_token()

    existing_links = get_existing_links(token)

    html = fetch_list_page(LIST_URL)
    items = parse_list(html)

    print(f"抓到 {len(items)} 条")

    new_count = 0

    for item in items:
        link = item["公告链接"]
        if link in existing_links:
            print("跳过已存在:", item["公告标题"])
            continue
        print("新增:", item["公告标题"])
        add_record(token, item)
        new_count += 1

    print(f"新增 {new_count} 条")

if __name__ == "__main__":
    main()