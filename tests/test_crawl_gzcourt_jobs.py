"""针对 crawl_gzcourt_jobs.parse_list 的单元测试。

用真实风格的最小 HTML 片段覆盖：
- 命中关键词 + 符合详情页 URL 模式的条目能被抽取
- 公示/名单/成绩等非招聘类标题被过滤
- 不匹配详情页 URL 模式的链接被过滤
- 同一链接的重复条目被去重
- 标题/链接为空的 a 标签被跳过
- 相对路径会被 urljoin 拼成绝对路径
"""

from crawl_gzcourt_jobs import parse_list


SOURCE = {
    "name": "广州法院系统招录公告",
    "url": "https://www.gzcourt.gov.cn/fygg/zpgg/",
    "发布机关": "广州法院系统",
    "机关类型": "法院",
    "地区": "广州",
    "detail_url_pattern": r"/\d{4}/\d{2}/\d+\.html$",
}


def _build_html(anchors: str) -> str:
    return f"<html><body><ul class='list'>{anchors}</ul></body></html>"


def test_hits_recruit_keyword_and_detail_url():
    html = _build_html(
        """
        <li>
          <a href="/fygg/zpgg/2026/05/100001.html">2026年书记员招聘公告</a>
          <span>2026-05-01</span>
        </li>
        """
    )
    items = parse_list(html, SOURCE)
    assert len(items) == 1
    it = items[0]
    assert it["公告标题"] == "2026年书记员招聘公告"
    assert it["公告链接"] == "https://www.gzcourt.gov.cn/fygg/zpgg/2026/05/100001.html"
    assert it["发布时间"] == "2026-05-01"
    assert it["发布机关"] == "广州法院系统"
    assert it["机关类型"] == "法院"
    assert it["地区"] == "广州"


def test_excludes_non_recruit_titles():
    html = _build_html(
        """
        <li><a href="/fygg/zpgg/2026/05/100002.html">2026年招聘公示名单</a><span>2026-05-02</span></li>
        <li><a href="/fygg/zpgg/2026/05/100003.html">2026年招聘成绩公告</a><span>2026-05-02</span></li>
        <li><a href="/fygg/zpgg/2026/05/100004.html">2026年体检递补公告</a><span>2026-05-02</span></li>
        """
    )
    items = parse_list(html, SOURCE)
    assert items == []


def test_excludes_non_detail_url():
    html = _build_html(
        """
        <li><a href="/fygg/zpgg/index.html">招聘专栏</a><span>2026-05-01</span></li>
        <li><a href="https://www.gzcourt.gov.cn/fygg/zpgg/2026/05/">招聘目录</a><span>2026-05-01</span></li>
        """
    )
    assert parse_list(html, SOURCE) == []


def test_dedup_same_link():
    html = _build_html(
        """
        <li><a href="/fygg/zpgg/2026/05/100005.html">2026年法院招聘公告</a><span>2026-05-01</span></li>
        <li><a href="/fygg/zpgg/2026/05/100005.html">2026年法院招聘公告(转)</a><span>2026-05-02</span></li>
        """
    )
    items = parse_list(html, SOURCE)
    assert len(items) == 1
    # 最后一次写入覆盖
    assert items[0]["公告链接"].endswith("/100005.html")


def test_skips_anchor_without_title_or_href():
    html = _build_html(
        """
        <li><a href="">2026年招聘公告</a><span>2026-05-01</span></li>
        <li><a href="/fygg/zpgg/2026/05/100006.html"></a><span>2026-05-01</span></li>
        """
    )
    assert parse_list(html, SOURCE) == []


def test_relative_path_is_resolved_to_absolute():
    html = _build_html(
        """
        <li><a href="2026/05/100007.html">2026年招聘公告</a><span>2026-05-03</span></li>
        """
    )
    items = parse_list(html, SOURCE)
    assert len(items) == 1
    assert items[0]["公告链接"] == (
        "https://www.gzcourt.gov.cn/fygg/zpgg/2026/05/100007.html"
    )


def test_missing_date_still_returned_with_empty_string():
    # parse_list 本身不要求日期存在，日期过滤在主流程完成
    html = _build_html(
        """
        <li><a href="/fygg/zpgg/2026/05/100008.html">2026年招聘公告</a></li>
        """
    )
    items = parse_list(html, SOURCE)
    assert len(items) == 1
    assert items[0]["发布时间"] == ""
