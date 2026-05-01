"""针对 update_status.parse_deadline 的单元测试。

重点覆盖 Asia/Shanghai 时区修复（见 B4）：
确保当毫秒时间戳对应北京时间 2026-05-01 00:00，无论机器所在时区为何，
都会被解读为 2026-05-01 而不是 2026-04-30。
"""

import datetime

import pytest

from update_status import parse_deadline


def test_parse_deadline_returns_none_for_none():
    assert parse_deadline(None) is None


def test_parse_deadline_returns_none_for_unknown_type():
    assert parse_deadline([1, 2, 3]) is None


def test_parse_deadline_parses_string_yyyy_mm_dd():
    assert parse_deadline("2026-05-01") == datetime.date(2026, 5, 1)


def test_parse_deadline_parses_string_with_time_suffix():
    # 飞书字符串形态下也可能带时间后缀，只取前 10 位
    assert parse_deadline("2026-05-01T12:00:00+08:00") == datetime.date(2026, 5, 1)


def test_parse_deadline_invalid_string_returns_none():
    assert parse_deadline("not-a-date") is None


def test_parse_deadline_timestamp_is_interpreted_in_asia_shanghai():
    # 2026-05-01 00:00:00 +08:00 对应的 UTC 毫秒戳
    # UTC 时间 = 2026-04-30 16:00:00 UTC
    ts_ms = int(
        datetime.datetime(
            2026, 5, 1, 0, 0, 0,
            tzinfo=datetime.timezone(datetime.timedelta(hours=8)),
        ).timestamp()
        * 1000
    )
    # 无论机器本地时区如何，都应解读为北京时间当天
    assert parse_deadline(ts_ms) == datetime.date(2026, 5, 1)


def test_parse_deadline_timestamp_edge_just_before_midnight_cn():
    # 北京时间 2026-05-01 23:59:59 -> 仍属于 5 月 1 日
    ts_ms = int(
        datetime.datetime(
            2026, 5, 1, 23, 59, 59,
            tzinfo=datetime.timezone(datetime.timedelta(hours=8)),
        ).timestamp()
        * 1000
    )
    assert parse_deadline(ts_ms) == datetime.date(2026, 5, 1)


def test_parse_deadline_timestamp_accepts_float():
    ts_ms = float(
        datetime.datetime(
            2026, 1, 1, 0, 0, 0,
            tzinfo=datetime.timezone(datetime.timedelta(hours=8)),
        ).timestamp()
        * 1000
    )
    assert parse_deadline(ts_ms) == datetime.date(2026, 1, 1)
