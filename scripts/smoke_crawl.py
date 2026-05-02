"""真实抓取冒烟测试。

直接访问 sources.py 中配置的站点，检验：
- fetch_list_page 能拿到 HTML
- parse_list 能筛出招聘类公告
- 前若干条的字段是否符合预期（标题/日期/链接）

本脚本不写飞书表，仅验证抓取链路。
运行前请先 export 4 个 FEISHU_* 环境变量（可用占位值）。
"""

import sys
from datetime import datetime
from pathlib import Path

# Windows 控制台默认 GBK，输出中文会乱码；统一改成 utf-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawl_gzcourt_jobs import fetch_list_page, parse_list, parse_total_pages, page_url
from sources import SOURCES


def main() -> None:
    print("=" * 72)
    print("真实抓取冒烟测试")
    print("=" * 72)

    for s in SOURCES:
        print(f"\n[源] {s['name']}  {s['url']}")
        try:
            html = fetch_list_page(s["url"])
            print(f"第 1 页 HTML 长度: {len(html)} 字节")
        except Exception as e:
            print(f"抓取失败: {type(e).__name__}: {e}")
            continue

        total_pages = parse_total_pages(html)
        print(f"共 {total_pages} 页")

        all_items = parse_list(html, s)

        # 抓取剩余分页（冒烟测试只抓前 3 页，避免耗时过长）
        max_pages = min(total_pages, 3)
        for page in range(2, max_pages + 1):
            p_url = page_url(s["url"], page)
            print(f"  抓取第 {page} 页: {p_url}")
            try:
                html = fetch_list_page(p_url)
                items = parse_list(html, s)
                all_items.extend(items)
            except Exception as e:
                print(f"  第 {page} 页抓取失败: {e}")

        print(f"解析到 {len(all_items)} 条招聘类公告（前 {max_pages} 页）")

        current_year = datetime.now().year
        year_hits = 0
        for it in all_items[:20]:
            try:
                if it["发布时间"]:
                    year = datetime.strptime(it["发布时间"], "%Y-%m-%d").year
                    if year >= current_year - 1:
                        year_hits += 1
            except Exception:
                pass
            date_col = it["发布时间"] or "no-date"
            print(f"  - [{date_col:>10}] {it['公告标题'][:50]}")
            print(f"    {it['公告链接']}")
        if len(all_items) > 20:
            print(f"  ... 共 {len(all_items)} 条（仅显示前 20 条）")
        print(f"前 20 条中属于当年或去年的: {year_hits}")


if __name__ == "__main__":
    main()
