"""针对 feishu_api.convert_publication_date_to_timestamp 的单元测试。

用于守护后续重构时不误伤时间戳转换逻辑（对应写入飞书的「发布时间」字段）。
"""

import datetime

import pytest

from feishu_api import convert_publication_date_to_timestamp


CN_TZ = datetime.timezone(datetime.timedelta(hours=8))


def test_none_returns_none():
    assert convert_publication_date_to_timestamp(None) is None


def test_int_returned_as_is():
    assert convert_publication_date_to_timestamp(1717171717000) == 1717171717000


def test_float_truncated_to_int():
    assert convert_publication_date_to_timestamp(1717171717000.5) == 1717171717000


def test_date_object_converts_to_ms_timestamp_at_midnight_cn():
    d = datetime.date(2026, 5, 1)
    expected = int(
        datetime.datetime(2026, 5, 1, 0, 0, 0, tzinfo=CN_TZ).timestamp() * 1000
    )
    assert convert_publication_date_to_timestamp(d) == expected


def test_string_yyyy_mm_dd_converts_to_ms_timestamp():
    expected = int(
        datetime.datetime(2026, 5, 1, 0, 0, 0, tzinfo=CN_TZ).timestamp() * 1000
    )
    assert convert_publication_date_to_timestamp("2026-05-01") == expected


def test_string_with_time_suffix_only_uses_first_10_chars():
    expected = int(
        datetime.datetime(2026, 5, 1, 0, 0, 0, tzinfo=CN_TZ).timestamp() * 1000
    )
    assert convert_publication_date_to_timestamp("2026-05-01T12:34:56") == expected


def test_invalid_string_returns_none():
    assert convert_publication_date_to_timestamp("not-a-date") is None


def test_unknown_type_returns_none():
    assert convert_publication_date_to_timestamp([2026, 5, 1]) is None
