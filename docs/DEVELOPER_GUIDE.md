# Developer Guide

## Project Structure

```text
douyin_academic_crawler/
  api.py                 API adapter interfaces and safe request wrapper
  parser.py              Raw JSON to standard comment structures
  collector.py           BFS comment tree traversal and CSV appends
  service.py             Task execution orchestration and post-processing
  task_runner.py         Validation, status transitions, audit triggering
  storage.py             CSV/XLSX helpers and failure logging
  cleaner.py             Text cleaning and feature flags
  report.py              Data quality report generation
  audit.py               JSONL research audit logging
  gui.py                 Tkinter UI, delegates to task runner
  mock_client.py         Fixture-backed offline client
  local_json_client.py   Local JSON offline client
```

## Responsibilities

- GUI: collects user choices and creates tasks. It does not request, parse, crawl, or write CSV directly.
- task_runner: validates safety limits, sets task status, calls service, writes audit.
- service: builds output paths, calls collector, cleans data, exports XLSX, generates reports.
- collector: traverses standard `CommentPage` data with BFS and respects `max_depth` / `max_pages`.
- api_client: provides mock/local clients now; real request placeholders remain disabled.
- parser: converts JSON-like dictionaries into `CommentNode` / `CommentPage`.
- storage: writes UTF-8-SIG CSV and simple XLSX workbooks.
- audit: appends JSONL records for research traceability.

## Run Tests

```powershell
python -m unittest discover -s tests -v
python -m compileall douyin_academic_crawler tests
```

## Add an Input Mode

1. Add config validation for the mode.
2. Implement a client exposing `fetch_top_level_comments`, `fetch_replies`, and `fetch_comment_replies`.
3. Return standard `CommentPage` objects only.
4. Wire the client in `runtime.build_task_runner`.
5. Add tests proving no unintended network behavior.

## Safety Boundary

Do not add automatic login, captcha bypass, private endpoint discovery, rate-limit evasion, or inaccessible-data collection. Any future lawful input source must preserve low-frequency controls, `max_pages` limits, audit logging, and explicit user configuration.
