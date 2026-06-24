# Douyin Academic Crawler

## 当前版本状态

当前版本：`v0.1.0-local-acceptance`

当前支持：mock 模式、local_json 模式、四级评论树导出、CSV / XLSX 导出、文本清洗、quality_report、audit.jsonl、一键验收脚本。

当前不支持：真实平台请求、自动登录、验证码绕过、频控规避、视频下载、主页作品采集、关键词搜索采集。

面向学术研究的公开评论数据采集工具骨架。当前实现包含可测试的评论树采集服务、接口适配层、采集任务控制层、JSONL 审计日志、CSV/Excel 存储、脱敏、限速、异常日志和 GUI 层级选择辅助。

本项目不包含真实平台私有接口地址，不提供自动登录、破解、绕过验证码、绕过频控或模拟攻击能力。

## 本地运行与验收步骤

当前默认运行模式是 `mock_mode=true` 的本地验收模式。该模式使用 `examples/mock_comment_tree.json` 中的 fixture 四级评论树，不会发起任何真实抖音请求，也不会访问任何真实平台接口。

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动 GUI：

```powershell
python main.py
```

也可以使用模块入口：

```powershell
python -m douyin_academic_crawler
```

无界面运行一次 mock 验收任务：

```powershell
python main.py --mock-run --config examples/sample_config.json
```

无界面运行一次本地 JSON 导入任务：

```powershell
python main.py --mock-run --config examples/local_json_config.json
```

也可以通过命令行指定 JSON 文件：

```powershell
python main.py --mock-run --local-json examples/local_comment_tree_sample.json
```

GUI 验收步骤：

1. 启动 `python main.py`。
2. 保持默认视频 ID `video-fixture-001`。
3. 保持默认最大评论层级 `4 级评论`，或选择 `1` 到 `4`。
4. 点击“开始采集”。
5. 查看界面日志中的 `task_id`、任务状态和采集层级。

启动或运行 mock 任务时会自动创建本地输出目录：

```text
exports/
  comments/
  audit/
  logs/
```

mock 验收会生成：

- `exports/comments/comments_video-fixture-001_depth4_task-*_YYYYMMDD.csv`
- `exports/audit/audit.jsonl`
- `exports/logs/runtime.log`

查看 audit 日志：

```powershell
Get-Content exports\audit\audit.jsonl
```

`runtime.log` 会记录程序启动、任务创建、任务完成或任务失败等运行信息。

## 本地交付版使用流程

一键验收：

```powershell
.\scripts\run_acceptance.ps1
```

该脚本会运行单元测试、mock 验收、本地 JSON 验收，并输出最新 CSV、XLSX、quality report 和 audit 路径。成功时最后打印：

```text
ACCEPTANCE PASSED
```

查看最新输出：

```powershell
.\scripts\show_latest_outputs.ps1
```

清理旧输出：

```powershell
.\scripts\clean_outputs.ps1
```

如需跳过确认：

```powershell
.\scripts\clean_outputs.ps1 -Force
```

交付文档：

- `docs/FIELD_DICTIONARY.md`：导出字段字典。
- `docs/USER_GUIDE.md`：本地使用说明。
- `docs/DEVELOPER_GUIDE.md`：开发与扩展说明。
- `release_manifest.json`：版本、支持输入模式、安全默认值和验收命令清单。

## 本地 JSON 导入模式说明

本地 JSON 导入模式用于真实数据适配前的字段兼容测试、研究数据清洗和格式转换。它只读取研究者手动提供的本地 JSON 文件，由 `CommentParser` 解析为标准 `CommentNode` / `CommentPage`，然后复用现有 collector、storage 和 audit 流程导出 CSV 与审计日志。

配置示例：

```json
{
  "mock_mode": true,
  "input_mode": "local_json",
  "input_json_file": "examples/local_comment_tree_sample.json",
  "allow_real_requests": false
}
```

该模式的边界：

- 不发起真实请求。
- 不包含真实平台私有接口地址。
- 不支持自动登录。
- 不支持验证码绕过。
- 不支持频控规避。
- 不尝试获取不可访问数据。

适用场景：

- 将合法获得的 JSON 样本转换为 CSV。
- 验证字段解析兼容性。
- 验证四级评论树、`max_depth`、`max_pages`、脱敏和审计日志流程。

## 研究数据清洗与质量报告说明

默认配置会开启文本清洗和 Excel 导出：

```json
{
  "enable_text_cleaning": true,
  "remove_emoji": false,
  "remove_urls": true,
  "remove_mentions": false,
  "export_xlsx": true
}
```

清洗字段说明：

- `comment_text`：原始评论文本，保留不覆盖。
- `cleaned_comment_text`：清洗后的评论文本；默认会去除首尾空白、把换行折叠为空格，并移除 URL。
- `text_length`：`cleaned_comment_text` 的字符长度。
- `has_url`：原始文本中是否检测到 URL。
- `has_mention`：原始文本中是否检测到 `@用户名`。
- `has_emoji`：原始文本中是否检测到 emoji。

CSV 仍使用 `utf-8-sig` 编码，方便 Excel 直接打开中文内容。启用 `export_xlsx=true` 时，还会在 `exports/comments/` 下生成同名 `.xlsx` 文件，至少包含：

- `comments` sheet：评论数据。
- `metadata` sheet：任务 ID、视频 ID、清洗状态等元数据。

每次任务完成后会在 `exports/reports/` 下生成质量报告：

```text
exports/reports/task-xxxx_quality_report.json
```

质量报告字段包括：

- `task_id`
- `video_id`
- `total_rows`
- `depth_distribution`
- `missing_text_count`
- `duplicate_comment_id_count`
- `min_comment_time`
- `max_comment_time`
- `generated_at`
- `output_csv`
- `output_xlsx`

审计日志也会记录：

- `quality_report_file`
- `output_xlsx`
- `cleaning_enabled`

## 四级评论采集使用说明

评论采集入口是 `CommentTreeCollector.collect_comment_tree(video_id, max_depth=max_depth)`。采集深度由 `max_depth` 控制，支持 `1` 到 `4`：

- `depth=1`：一级评论
- `depth=2`：二级评论
- `depth=3`：三级评论
- `depth=4`：四级评论

采集器使用 BFS 队列遍历评论树。一级评论先写入 CSV，然后只在 `depth < max_depth` 时继续请求该评论可访问的回复页。每完成一个分页会立即追加写入，便于异常中断后保留已采集数据。再次运行时会读取已有 CSV 中的 `comment_id`，避免重复保存。

CSV / Excel 导出字段包括：

`video_id`, `comment_id`, `root_comment_id`, `parent_comment_id`, `reply_to_comment_id`, `reply_to_user_name`, `depth`, `comment_path`, `comment_user_name`, `comment_user_id_hash`, `comment_user_uid_hash`, `comment_time`, `comment_ip_location`, `comment_like_count`, `comment_text`, `crawl_time`

`comment_path` 表示评论在树中的位置，例如 `1`、`1.1`、`1.1.1`、`1.1.1.1`。

## 采集任务与审计日志说明

每次采集都应先创建 `CrawlTask`，再交给 `CrawlTaskRunner.run(task)` 执行。任务会生成或携带唯一 `task_id`，用于输出文件名、状态追踪和审计回溯。

任务状态包括：

- `pending`
- `running`
- `success`
- `failed`
- `cancelled`

本阶段支持的任务类型有：

- `comment_tree`：已实现任务结构和执行路径
- `profile_videos`：仅保留任务类型，不实现真实请求
- `search_videos`：仅保留任务类型，不实现真实请求

`CrawlTaskRunner` 会校验 `max_depth` 只能为 `1`、`2`、`3`、`4`，并校验 `max_pages` 必须为正整数或 `None`。执行成功或失败后都会写入 JSONL 审计日志，便于研究过程回溯。

默认审计日志字段包括：

`task_id`, `task_type`, `video_id`, `video_url`, `max_depth`, `max_pages`, `output_file`, `started_at`, `finished_at`, `status`, `total_saved_count`, `error_message`, `compliance_note`

审计日志示例：

```json
{"task_id":"task-success","task_type":"comment_tree","video_id":"video-fixture-001","video_url":"https://example.invalid/video-fixture-001","max_depth":4,"max_pages":null,"output_file":"exports/comments_video-fixture-001_depth4_task-success_20260624.csv","started_at":"2026-06-24T10:00:00","finished_at":"2026-06-24T10:00:00","status":"success","total_saved_count":4,"error_message":"","compliance_note":"本任务仅用于学术研究，仅保存研究者有权访问范围内平台正常返回的数据；不包含自动登录、破解、绕过验证码、规避频控或获取不可访问数据的逻辑。"}
```

输出文件名包含 `task_id`、`video_id` 和采集深度，例如：

```text
comments_video-fixture-001_depth4_task-success_20260624.csv
```

工具不会绕过平台限制或采集不可访问数据。如果平台接口限制评论层级、分页或返回字段，工具只保存平台正常返回且研究者有权访问的数据。

## 接口适配层说明

接口适配层由以下模块组成：

- `config.py`：读取 `cookie_file`、`output_dir`、`sleep_min_seconds`、`sleep_max_seconds`、`request_timeout`、`max_retry`、`user_agent` 等配置。
- `cookie.py`：只从本地 `cookie.txt` 读取用户自行合法获取的 Cookie 字符串。
- `api.py`：提供 `DouyinAPIClient.request()`，统一处理 headers、Cookie、timeout、retry、限速和明确异常。
- `parser.py`：提供 `CommentParser`，把原始 JSON 容错解析为标准 `CommentNode` / `CommentPage`。
- `collector.py`：只处理标准评论结构和评论树遍历，不直接解析平台 JSON。

默认限速配置：

```json
{
  "cookie_file": "cookie.txt",
  "output_dir": "exports",
  "sleep_min_seconds": 1.0,
  "sleep_max_seconds": 2.0,
  "request_timeout": 10.0,
  "max_retry": 2,
  "user_agent": "DouyinAcademicCrawler/0.1 research-only"
}
```

Cookie 使用边界：

- Cookie 需研究者自行合法获取，并放入 `cookie.txt`。
- 工具不会自动登录。
- 工具不会绕过验证码。
- 工具不会保存账号密码。
- 工具不会绕过平台访问控制或频控。

`DouyinAPIClient` 当前没有绑定任何真实抖音私有接口地址。以下方法仅作为后续合法适配的占位：

- `fetch_top_level_comments(video_id, cursor=None)`
- `fetch_comment_replies(video_id, comment_id, cursor=None)`
- `fetch_video_metadata(video_id)`

## 真实数据小样本适配前说明

当前默认配置仍然是本地 mock 验收模式：

```json
{
  "mock_mode": true,
  "allow_real_requests": false,
  "real_request_warning_ack": false,
  "max_pages_default": 1,
  "max_pages_hard_limit": 5,
  "max_depth_hard_limit": 4
}
```

安全开关含义：

- `mock_mode=true`：使用本地 fixture/mock client，不发起真实平台请求。
- `allow_real_requests=false`：禁止非 mock client 执行；如果运行时尝试使用非 mock client，会报错“当前处于 mock 验收模式，真实请求已被禁用。”
- `real_request_warning_ack=false`：为后续真实数据适配预留的人工确认开关，本阶段不启用真实请求。
- `max_pages_default=1`：未填写页数时只采集 1 页，默认小样本。
- `max_pages_hard_limit=5`：任何任务页数不能超过 5。
- `max_depth_hard_limit=4`：评论层级不能超过 4。

GUI 会显示当前安全模式：

```text
当前模式：Mock 验收模式
真实请求：已禁用
最大页数限制：5
最大评论层级限制：4
```

GUI 也提供“最大页数”输入框，默认值为 `1`，允许范围为 `1` 到 `5`。非法输入会在界面日志中提示错误，任务不会执行。

分页安全规则：

- `max_pages` 表示“每个分页入口的最大页数”，不是“最大评论数”。
- 例如 `max_depth=4`、`max_pages=1` 时，如果一级评论、二级回复、三级回复、四级回复都在各自第一页中，仍可采集 1 到 4 级评论。
- 一级评论分页受 `max_pages` 限制。
- 回复评论分页也受 `max_pages` 限制。
- 如果接口返回 `has_more=true` 但没有 `cursor`，采集器会记录 warning 并停止该分页循环。
- 不允许无限分页。

审计日志额外记录安全配置字段：

- `mock_mode`
- `allow_real_requests`
- `max_pages`
- `max_pages_hard_limit`
- `max_depth_hard_limit`
- `config_snapshot`

## GUI 使用说明

评论采集界面提供“最大评论层级”下拉框：

- `1 级评论`
- `2 级评论`
- `3 级评论`
- `4 级评论`

默认选择 `4 级评论`。用户点击“开始采集”后，GUI 会创建 `CrawlTask` 并交给 `CrawlTaskRunner` 执行；GUI 不直接请求、解析、递归采集或写 CSV。

运行日志会显示 `task_id` 和状态变化，例如：

```text
task_id：task-xxxxxxxxxxxx
任务状态：pending -> running
当前最大采集层级：4
正在采集一级评论
正在采集二级评论
正在采集三级评论
正在采集四级评论
任务状态：running -> success
```

如果用户选择 `1 级评论`，任务会传入 `max_depth=1`，collector 只保存一级评论；选择 `2 级评论` 时只保存一级、二级评论。

## 测试

项目测试全部基于 fixture/mock 数据，不会访问真实平台：

```powershell
python -m unittest discover -s tests -v
python -m compileall douyin_academic_crawler tests
```
