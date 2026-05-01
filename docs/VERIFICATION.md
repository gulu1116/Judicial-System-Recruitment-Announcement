# 脚本运行与抓取验证指南

本文档描述如何从零验证 `crawl_gzcourt_jobs.py` 与 `update_status.py` 两个主脚本的运行正确性。验证分为 **4 个层级**，按开销从低到高排列，建议按顺序执行。

---

## 目录

- [验证分层总览](#验证分层总览)
- [Layer 1 — 单元测试（必跑）](#layer-1--单元测试必跑)
- [Layer 2 — 真实网站抓取冒烟（强烈建议）](#layer-2--真实网站抓取冒烟强烈建议)
- [Layer 3 — 飞书写入端到端（提 PR 前建议跑一次）](#layer-3--飞书写入端到端提-pr-前建议跑一次)
- [Layer 4 — CI 自动回归](#layer-4--ci-自动回归)
- [附录 A：环境准备一次性操作](#附录-a环境准备一次性操作)
- [附录 B：常见问题排查](#附录-b常见问题排查)

---

## 验证分层总览

| 层级 | 验证内容 | 是否需要飞书凭证 | 是否联网 | 典型耗时 |
|------|---------|----------------|---------|---------|
| Layer 1 | 纯函数单元测试 | 否 | 否 | ~2 秒 |
| Layer 2 | 真实站点抓取 + 列表解析 | 否 | 是 | ~5 秒 |
| Layer 3 | 完整写入飞书表 + 状态更新 | **是** | 是 | ~10 秒 |
| Layer 4 | GitHub Actions 自动跑 pytest | 否 | 否 | ~40 秒 |

---

## Layer 1 — 单元测试（必跑）

覆盖 3 个纯函数：`parse_list`、`parse_deadline`、`convert_publication_date_to_timestamp`。

### 运行

```powershell
# Windows PowerShell
$py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
& $py -m pip install -r requirements-dev.txt
& $py -m pytest tests/ -v
```

```bash
# Linux / macOS
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

### 预期输出

```
============================= test session starts =============================
collected 23 items

tests/test_crawl_gzcourt_jobs.py ....... [ 30%]
tests/test_feishu_api.py ........        [ 65%]
tests/test_update_status.py ........     [100%]

============================= 23 passed in 1.76s ==============================
```

### 失败时

- 任何一个红 × 都代表对应纯函数的输入输出契约被破坏，先读报错信息定位问题，不要忽略

---

## Layer 2 — 真实网站抓取冒烟（强烈建议）

使用 `scripts/smoke_crawl.py` 直接访问 `sources.py` 中配置的所有源站点，验证：

- 站点能正常响应（HTTP 200）
- `parse_list` 能从真实 HTML 中筛出招聘类公告
- 每条记录的 标题 / 发布时间 / 链接 字段内容合理

**不会**写任何数据到飞书。

### 运行

```powershell
# Windows PowerShell
$py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
$env:PYTHONIOENCODING = "utf-8"
# Python 在 import feishu_api 时会校验 4 个环境变量，给占位值即可
$env:FEISHU_APP_ID = "x"; $env:FEISHU_APP_SECRET = "x"
$env:FEISHU_APP_TOKEN = "x"; $env:FEISHU_TABLE_ID = "x"
& $py scripts/smoke_crawl.py
```

```bash
# Linux / macOS
export FEISHU_APP_ID=x FEISHU_APP_SECRET=x FEISHU_APP_TOKEN=x FEISHU_TABLE_ID=x
python scripts/smoke_crawl.py
```

### 预期输出（示例，以 2026 年的真实抓取为例）

```
========================================================================
真实抓取冒烟测试
========================================================================

[源] 广州法院系统招录公告  https://www.gzcourt.gov.cn/fygg/zpgg/
status: 200
final url: https://www.gzcourt.gov.cn/fygg/zpgg/
HTML 长度: 8550 字节
解析到 2 条招聘类公告
  - [2026-02-25] 广州市中级人民法院2026年公开招募就业见习人员公告
    http://www.gzcourt.gov.cn/fygg/zpgg/2026/02/25181728151.html
  - [2025-04-18] 广州市中级人民法院2025年公开招聘劳动合同制审判辅助人员笔试确认及笔试公告
    http://www.gzcourt.gov.cn/fygg/zpgg/2025/04/18173720595.html
前 15 条中属于当前年(2026)的: 1
```

### 如何解读

- **HTTP 200**：站点可达、没被拒绝
- **解析到 N 条**：`N` 至少大于 0；若为 0，说明目标站改版了选择器或关键词过滤太紧
- **标题不含公示/名单/成绩/体检/递补/资格审核**：过滤逻辑有效
- **链接匹配 `/\d{4}/\d{2}/\d+\.html$`**：URL 正则有效
- **前 15 条中属于当前年的数量**：这直接体现 B2 修复（动态当前年）的效果 —— 非当前年公告会被主流程正确忽略

### 失败时

| 现象 | 处理 |
|------|------|
| 连不上、超时 | 检查本地网络 / 代理（脚本主动禁用系统代理，若你的网络必须走代理可临时把 `crawl_gzcourt_jobs.py` 里的 `session.proxies = {...None}` 注释掉） |
| HTTP 403 / 429 | 可能被目标站限流，更换 User-Agent 或稍后重试 |
| 解析到 0 条 | 跳 `crawl_gzcourt_jobs.py` 的 `parse_list`，打印原始 HTML 片段看标签结构是否变化 |

---

## Layer 3 — 飞书写入端到端（提 PR 前建议跑一次）

这是最完整的验证，覆盖：
- 飞书 OAuth（`get_token`）
- 飞书 search（`get_records` 去重查询）
- 飞书 create（`add_record` 新增）
- 飞书 update（`update_record` 状态更新）
- **报名截止 → 已截止** 的自动扫描逻辑（B4 修复的时区守护）

### 3.0 ⛔ 安全原则

**永远不要在作者的生产飞书表上跑写入或更新操作**。否则：
- `crawl_gzcourt_jobs.py` 会真的往生产表新增记录 → 污染数据
- `update_status.py` 会真的修改生产记录的状态 → 业务风险

正确做法：使用独立的 sandbox。下面三条 sandbox 路径按你手头有的资源选择。

### 3.1 路径选择

| 路径 | 作者需要给你 | 你需要做 | 适用场景 |
|------|-------------|---------|---------|
| **A — 全自建 sandbox** | 飞书组织邀请链接 | 自建测试表 + 自建测试应用 | 最干净、最规范，**推荐** |
| **B — 用作者建的 sandbox 表** | 邀请链接 + sandbox 表的 `App Token` 和 `Table ID` | 自建测试应用 | 字段配置作者已搞定 |
| **C — 用作者全套测试凭证** | 完整 4 个 `FEISHU_*` 凭证 + sandbox 表 | 配 `.env` 跑脚本 | 最便捷但凭证管理复杂 |

下面以 **路径 A** 为基础给完整步骤，**B / C 的差异**在每节标注 → "路径 B/C 跳过本节"。

### 3.2 阶段 ① 加入作者的飞书组织（路径 A/B 必做）

1. 浏览器打开作者发的邀请链接（形如 `https://<tenant>.feishu.cn/invite/member/...`）
2. 用手机号/邮箱注册或登录飞书账号
3. 点击 **接受邀请 / 加入组织**
4. 进入组织工作台

> 路径 C 跳过：作者已给完整凭证，跳到 3.8

### 3.3 阶段 ② 在组织里创建你自己的 sandbox 多维表（仅路径 A）

> 路径 B 跳过：使用作者给的 sandbox 表，跳到 3.5

1. 飞书工作台左上角点 **➕** → **多维表格**
2. 选 **空白多维表格**
3. 命名为 `judicial-crawler-sandbox-<你的标识>`，方便区分
4. 进入表后把默认字段全部删除，按下面的字段契约新建

#### 字段契约 — 8 个字段，名字必须完全一致

| # | 字段名 | 字段类型 | 关键说明 |
|---|--------|---------|---------|
| 1 | `公告标题` | 文本 | |
| 2 | `发布时间` | 日期 | 格式不限，代码用毫秒时间戳写入 |
| 3 | `公告链接` | 超链接 | |
| 4 | `发布机关` | 文本 | 推荐文本（用单选要预设「广州法院系统」选项） |
| 5 | `机关类型` | 文本 | 同上 |
| 6 | `地区` | 文本 | 同上 |
| 7 | `当前状态` | **单选** | ⚠️ **必须**预设「未看」「已截止」两个选项 |
| 8 | `报名截止` | 日期 | |

> ⚠️ 第 7 个字段最容易踩坑：必须是「单选」类型，且选项里有「未看」「已截止」两个 **一字不差** 的值（无前后空格、无标点）。

### 3.4 阶段 ③ 创建你自己的测试飞书应用（路径 A/B）

> 路径 C 跳过：作者已给凭证，跳到 3.8

1. 打开 <https://open.feishu.cn/app>
2. 用刚加入组织的飞书账号登录
3. 右上角点 **创建企业自建应用**
4. 填写：
   - 应用名称：`judicial-crawler-sandbox-<你的标识>`
   - 应用描述：`司法招聘爬虫个人测试应用`
5. 点 **创建**
6. 进入应用详情页，左侧 **凭证与基础信息**
7. 复制并妥善保管：
   - `App ID`（形如 `cli_xxx`）
   - `App Secret`（点 "查看" 显示，**不要外发或截图**）

### 3.5 阶段 ④ 开通权限并发布（路径 A/B）

1. 应用详情页左侧 **权限管理** → **API 权限**
2. 搜索 `bitable`，勾选 `bitable:app`（"查看、评论、编辑和管理多维表格"）
3. 点 **保存**
4. 左侧 **版本管理与发布** → **创建版本**
5. 填版本号（如 `1.0.0`）和说明 → **保存并申请发布**

> 多数组织自建应用秒批；如卡审核 > 5 分钟，让作者批准。

### 3.6 阶段 ⑤ 把应用加为表的协作者（路径 A/B）

1. 回到 sandbox 多维表（路径 A 是你自建的，路径 B 是作者给的）
2. 右上角 **...** → **更多** → **添加文档应用**
3. 搜索你刚创建的应用名 → **添加**，权限选 **可编辑**

### 3.7 阶段 ⑥ 提取表的 `App Token` 和 `Table ID`（路径 A/B）

打开 sandbox 表，查看浏览器 URL：

```
https://xxx.feishu.cn/base/U4Xbb1xxxxxxxxxxxxxxxxxx?table=tblxxxxxxxxxxxxxx&view=vewxxx
                              ^^^^^^^^^^^^^^^^^^^^^^         ^^^^^^^^^^^^^^^^^^
                              FEISHU_APP_TOKEN              FEISHU_TABLE_ID
```

- `/base/` 后到 `?` 之间 → `FEISHU_APP_TOKEN`
- `table=` 后到 `&` 之间 → `FEISHU_TABLE_ID`

### 3.8 阶段 ⑦ 配置 `.env` 并跑脚本（路径 A/B/C 共用）

#### 3.8.1 建 `.env` 文件

```powershell
# Windows
Copy-Item .env.example .env
```

```bash
# Linux / macOS
cp .env.example .env
```

用 IDE 打开 `.env`，填入 4 个真实值：

```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_APP_TOKEN=U4Xbb1xxx
FEISHU_TABLE_ID=tblxxx
```

**确认 `.env` 不会被提交**：

```powershell
git status
# 必须看不到 .env
```

#### 3.8.2 跑脚本

由于项目代码当前用 `os.getenv()` 不自动读 `.env`，需手动 export。复制**整块**命令运行：

```powershell
# Windows PowerShell —— 自动从 .env 读值并 export 到当前会话
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        Set-Item -Path "env:$name" -Value $value
    }
}

$py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
$env:PYTHONIOENCODING = "utf-8"

# Step A: 抓取冒烟
& $py scripts/smoke_crawl.py
# Step B: 完整流程（抓 + 写入飞书）
& $py crawl_gzcourt_jobs.py
# Step C: 状态更新扫描
& $py update_status.py
```

```bash
# Linux / macOS
set -a; source .env; set +a   # 自动 export

python scripts/smoke_crawl.py
python crawl_gzcourt_jobs.py
python update_status.py
```

### 3.9 阶段 ⑧ 检查验证结果

#### 3.9.1 `crawl_gzcourt_jobs.py` 预期输出

```
get_token status: 200
get_records status: 200
已有记录数: 0
正在抓取来源: 广州法院系统招录公告
status: 200
抓到 N 条
新增: 广州市中级人民法院2026年公开招募就业见习人员公告
add_record status: 200
新增 N 条
```

#### 3.9.2 sandbox 表内容 checklist

切回飞书 sandbox 表：

- [ ] 多出 N 条记录（N ≥ 0；若当年没招聘公告则 0）
- [ ] 标题、发布时间、公告链接 与抓取数据一致
- [ ] 发布机关=「广州法院系统」、机关类型=「法院」、地区=「广州」
- [ ] 当前状态=「未看」
- [ ] 报名截止字段为空

#### 3.9.3 验证 B4 时区修复（关键回归点）

1. 在 sandbox 表给某条记录的 **报名截止** 字段填一个**已过去的日期**（如 `2025-01-01`）
2. 重跑 `update_status.py`
3. 预期输出多一段：
   ```
   准备更新: 广州市中级人民法院2026年公开招募就业见习人员公告
   update_record status: 200
   ```
4. 回 sandbox 表，这条的 **当前状态** 应从「未看」变为「已截止」 ✅

#### 3.9.4 验证去重

再跑一次 `crawl_gzcourt_jobs.py`：

```
已有记录数: N
...
跳过已存在: 广州市中级人民法院2026年公开招募就业见习人员公告
新增 0 条
```

sandbox 表**不应**新增重复记录，说明 `公告链接` 去重逻辑有效。

### 3.10 验证完成后清理

- 测试结束，如不再使用：在飞书开发者后台**删除测试应用**，避免凭证残留
- `.env` 留在本地（已被 `.gitignore`），后续验证可复用

---

## Layer 4 — CI 自动回归

仓库已配置 `.github/workflows/tests.yml`，以下情形自动触发：

- push 到 `main`
- 所有 pull_request（含来自 fork 的 cross-repo PR）
- 手动点击 `Run workflow`

### 查看 CI 结果

1. 打开 PR 页面
2. 下方 **Checks** 区看 `Tests / pytest` 是否 ✅
3. 点 **Details** 可查看完整 pytest 输出

### CI 未跑起来？

- 首次 push 到新分支：fork 上的 Actions 可能默认关闭，去 fork 仓库 **Actions** 标签页点 **Enable workflows**
- 本地没推：`git push origin <分支名>` 后 CI 自动触发

---

## 附录 A：环境准备一次性操作

### A.1 安装 Python 3.11

**Windows**：
```powershell
winget install --id Python.Python.3.11 -e --scope user --accept-source-agreements --accept-package-agreements
```

安装位置：`%LOCALAPPDATA%\Programs\Python\Python311\`

> 若 `python` 命令仍指向 Microsoft Store stub，到「设置 → 应用 → 高级应用设置 → 应用执行别名」关掉 `python.exe` 和 `python3.exe` 的别名。

**Linux / macOS**：
```bash
# macOS (homebrew)
brew install python@3.11

# Ubuntu / Debian
sudo apt install python3.11 python3.11-venv
```

### A.2 安装项目依赖

```powershell
# Windows
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" -m pip install -r requirements-dev.txt
```

```bash
# Linux / macOS
python3.11 -m pip install -r requirements-dev.txt
```

### A.3 一键验证脚本（可选）

新建 `scripts/verify.ps1`：

```powershell
$ErrorActionPreference = "Stop"
$py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[1/3] pytest..." -ForegroundColor Cyan
& $py -m pytest tests/ -v

Write-Host "[2/3] compileall..." -ForegroundColor Cyan
& $py -m compileall crawl_gzcourt_jobs.py update_status.py feishu_api.py sources.py

Write-Host "[3/3] 真实抓取冒烟..." -ForegroundColor Cyan
$env:FEISHU_APP_ID = "x"; $env:FEISHU_APP_SECRET = "x"
$env:FEISHU_APP_TOKEN = "x"; $env:FEISHU_TABLE_ID = "x"
& $py scripts/smoke_crawl.py

Write-Host "All non-Feishu checks passed." -ForegroundColor Green
```

运行：`pwsh scripts/verify.ps1`（或 PowerShell 5.1：`powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`）

---

## 附录 B：常见问题排查

### B.1 `ModuleNotFoundError: No module named 'crawl_gzcourt_jobs'`

脚本不是从项目根目录运行，或 `scripts/smoke_crawl.py` 未添加 `sys.path`。检查：

```powershell
# 应该在项目根目录运行
git rev-parse --show-toplevel
```

### B.2 `RuntimeError: 缺少飞书环境变量`

`feishu_api.py` 在 import 时校验环境变量。即使只做 Layer 2，也要至少设置 4 个占位值：

```powershell
$env:FEISHU_APP_ID = "x"; $env:FEISHU_APP_SECRET = "x"
$env:FEISHU_APP_TOKEN = "x"; $env:FEISHU_TABLE_ID = "x"
```

### B.3 控制台中文乱码

Windows 控制台默认 GBK，Python 脚本输出 UTF-8 会乱码。两种解决：

- 设置 `$env:PYTHONIOENCODING = "utf-8"`
- 或执行 `chcp 65001` 切到 UTF-8 代码页

### B.4 `add_record status: 400` + `InvalidFieldValue`

通常是 `当前状态` 单选字段没有「未看」选项，或字段名不完全匹配。检查多维表格：

- 字段名是否与 3.3 表格的中文字符**完全一致**（含空格、大小写）
- `当前状态` 的选项是否包含「未看」和「已截止」两项

### B.5 `get_token` 返回非 0 code

- App ID / App Secret 错
- 应用未发布（`权限管理` → `发布`）
- 应用被冻结（飞书后台查）

### B.6 `get_records status: 403`

应用没有被加为表的协作者，按 3.4 操作。

---

## 反馈

如验证过程中发现本文档描述的预期输出与实际不符，或新的故障模式，请在 PR 或 Issue 中补充，持续完善本指南。
