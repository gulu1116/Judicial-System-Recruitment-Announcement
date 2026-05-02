import requests
import re
from sources import SOURCES
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from feishu_api import add_record, get_existing_links, get_token


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

def parse_list(html: str, source: dict) -> list:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.select("a[href]"):
        title = a.get_text(" ", strip=True)
        href = a.get("href", "").strip()

        if not title or not href:
            continue

        # 必须包含招聘类关键词
        if not any(k in title for k in ["招聘", "招募", "招录", "录用"]):
            continue

        # 排除非招聘公告（保留「拟录用人员公示」等招聘结果公告）
        if any(k in title for k in ["名单", "成绩", "体检", "递补", "资格审核"]):
            continue

        full_url = urljoin(source["url"], href)
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
            "发布机关": source["发布机关"],
            "机关类型": source["机关类型"],
            "地区": source["地区"],
        })

    dedup = {}
    for item in results:
        dedup[item["公告链接"]] = item
    return list(dedup.values())


def parse_total_pages(html: str) -> int:
    """从分页区域解析总页数，如 '页次:1/10' → 10"""
    m = re.search(r"页次:\s*\d+/(\d+)", html)
    if m:
        return int(m.group(1))
    return 1


def page_url(base_url: str, page: int) -> str:
    """根据 base_url 和页码生成分页 URL。
    第 1 页: base_url 本身（或 base_url + 'index.html'）
    第 N 页: base_url + 'index{N-1}.html'
    """
    if page <= 1:
        return base_url
    # 确保 base_url 以 / 结尾
    if not base_url.endswith("/"):
        base_url += "/"
    return f"{base_url}index{page - 1}.html"

def main():
    token = get_token()

    existing_links = get_existing_links(token)

    all_items = []

    for source in SOURCES:
        print("正在抓取来源:", source["name"])
        html = fetch_list_page(source["url"])
        total_pages = parse_total_pages(html)
        print(f"  共 {total_pages} 页")
        items = parse_list(html, source)
        all_items.extend(items)

        # 抓取剩余分页（遇到整页都是旧年份则提前终止）
        current_year = datetime.now().year
        for page in range(2, total_pages + 1):
            p_url = page_url(source["url"], page)
            print(f"  抓取第 {page} 页: {p_url}")
            try:
                html = fetch_list_page(p_url)
                items = parse_list(html, source)
            except Exception as e:
                print(f"  第 {page} 页抓取失败: {e}")
                continue
            if not items:
                print(f"  第 {page} 页无匹配条目，停止翻页")
                break
            # 检查本页最新记录的年份
            page_years = []
            for it in items:
                try:
                    if it["发布时间"]:
                        page_years.append(datetime.strptime(it["发布时间"], "%Y-%m-%d").year)
                except ValueError:
                    pass
            if page_years and max(page_years) < current_year - 1:
                print(f"  第 {page} 页最新年份 {max(page_years)} < {current_year - 1}，停止翻页")
                break
            all_items.extend(items)

    filtered_items = []
    new_count = 0
    current_year = datetime.now().year

    for item in all_items:
        raw_date = item.get("发布时间", "")
        if not raw_date:
            print(f"跳过（无发布时间）: {item.get('公告标题', '')} {item.get('公告链接', '')}")
            continue
        try:
            year = datetime.strptime(raw_date, "%Y-%m-%d").year
        except ValueError:
            print(f"跳过（发布时间解析失败 {raw_date!r}）: {item.get('公告标题', '')}")
            continue
        if year >= current_year - 1:
            filtered_items.append(item)
    print(f"抓到 {len(filtered_items)} 条")

    for item in filtered_items:
        link = item["公告链接"]
        if link in existing_links:
            print("跳过已存在:", item["公告标题"])
            continue
        print("新增:", item["公告标题"])
        add_record(token, item)
        new_count += 1
        existing_links.add(link)

    print(f"新增 {new_count} 条")

if __name__ == "__main__":
    main()