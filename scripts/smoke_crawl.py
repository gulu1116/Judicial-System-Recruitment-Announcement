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

from crawl_gzcourt_jobs import fetch_list_page, parse_list
from sources import SOURCES


def main() -> None:
    print("=" * 72)
    print("真实抓取冒烟测试")
    print("=" * 72)

    for s in SOURCES:
        print(f"\n[源] {s['name']}  {s['url']}")
        try:
            html = fetch_list_page(s["url"])
            print(f"HTML 长度: {len(html)} 字节")
        except Exception as e:
            print(f"抓取失败: {type(e).__name__}: {e}")
            continue

        try:
            items = parse_list(html, s)
        except Exception as e:
            print(f"解析失败: {type(e).__name__}: {e}")
            continue

        print(f"解析到 {len(items)} 条招聘类公告")

        current_year = datetime.now().year
        year_hits = 0
        for it in items[:15]:
            year_str = ""
            try:
                if it["发布时间"]:
                    year = datetime.strptime(it["发布时间"], "%Y-%m-%d").year
                    year_str = str(year)
                    if year == current_year:
                        year_hits += 1
            except Exception:
                year_str = "?"
            date_col = it["发布时间"] or "no-date"
            print(f"  - [{date_col:>10}] {it['公告标题'][:40]}")
            print(f"    {it['公告链接']}")
        if len(items) > 15:
            print(f"  ... 共 {len(items)} 条（仅显示前 15 条）")
        print(f"前 15 条中属于当前年({current_year})的: {year_hits}")


if __name__ == "__main__":
    main()
