"""pytest 共享 fixture 与 import 前置处理。

`feishu_api` 模块在 import 时会校验 4 个 FEISHU_* 环境变量，缺失即 raise。
为了让纯函数（如 convert_publication_date_to_timestamp / parse_deadline）
可被单独测试，这里在任何 test module 被 collect 之前注入占位凭证。

这些凭证只在本地/CI 测试进程中生效，不会被脚本实际用于访问飞书接口
（因为相关测试不会触发网络调用）。
"""

import os
import sys
from pathlib import Path


# 让项目根目录可被 import（tests/ 同级的 feishu_api.py 等）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# 在任何 test 收集之前注入占位环境变量
os.environ.setdefault("FEISHU_APP_ID", "test_app_id")
os.environ.setdefault("FEISHU_APP_SECRET", "test_app_secret")
os.environ.setdefault("FEISHU_APP_TOKEN", "test_app_token")
os.environ.setdefault("FEISHU_TABLE_ID", "test_table_id")
