# Judicial System Recruitment Announcement

司法系统招聘公告自动采集脚本。

## 当前功能

- 抓取广州法院系统招聘公告列表
- 过滤非招聘公告
- 按公告链接去重
- 写入飞书多维表格
- 根据报名截止日期自动更新状态为“已截止”

## 运行

```bash
pip install -r requirements.txt
python crawl_gzcourt_jobs.py
python update_status.py