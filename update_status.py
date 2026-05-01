from feishu_api import get_records, get_token, update_record
import datetime

# 飞书多维表格的日期字段对外是 UTC 毫秒时间戳，但业务侧语义是“北京时间的某一天”。
# 因此统一使用 Asia/Shanghai (UTC+8) 做时间戳解码与 today 计算，避免 GitHub Actions
# 运行在 UTC 时区导致跨天误判（例如 UTC 16:00 对应北京次日 00:00）。
CN_TZ = datetime.timezone(datetime.timedelta(hours=8))


def parse_deadline(deadline_value):
    if deadline_value is None:
        return None

    # 飞书日期字段常见是毫秒时间戳
    if isinstance(deadline_value, (int, float)):
        return datetime.datetime.fromtimestamp(
            deadline_value / 1000, tz=CN_TZ
        ).date()

    # 有些情况下也可能是字符串
    if isinstance(deadline_value, str):
        try:
            return datetime.datetime.strptime(deadline_value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    return None


def today_in_cn() -> datetime.date:
    return datetime.datetime.now(tz=CN_TZ).date()


def main():
    token = get_token()
    records = get_records(token)

    today = today_in_cn()
    print("today(Asia/Shanghai):", today)

    for r in records:
        record_id = r["record_id"]
        fields = r["fields"]

        title = fields.get("公告标题")
        deadline_raw = fields.get("报名截止")
        status = fields.get("当前状态")

        print("record title:", title)
        print("deadline raw:", deadline_raw)
        print("status raw:", status)

        deadline_date = parse_deadline(deadline_raw)
        if deadline_date is None:
            continue

        if deadline_date < today and status != "已截止":
            print("准备更新:", title)
            update_record(token, record_id)

if __name__ == "__main__":
    main()