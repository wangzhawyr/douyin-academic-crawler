# User Guide

## Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

The current runtime uses only the Python standard library for core flows.

## Start GUI

```powershell
python main.py
```

The GUI starts in offline acceptance mode. It does not perform real Douyin requests.

## Mock Mode

Run the built-in fixture workflow:

```powershell
python main.py --mock-run --config examples/sample_config.json
```

Mock mode reads `examples/mock_comment_tree.json`.

## Local JSON Mode

Run a local JSON import:

```powershell
python main.py --mock-run --config examples/local_json_config.json
```

Or pass a JSON file directly:

```powershell
python main.py --mock-run --local-json examples/local_comment_tree_sample.json
```

Local JSON mode reads a local file, parses comments, exports CSV/XLSX, and writes audit logs. It does not contact any platform.

## Outputs

```text
exports/
  comments/   CSV and XLSX exports
  audit/      audit.jsonl
  logs/       runtime.log
  reports/    quality_report.json files
```

CSV files use `utf-8-sig` encoding for Excel-friendly Chinese text.

## Output Purposes

- CSV: primary research dataset.
- XLSX: Excel-friendly copy with `comments` and `metadata` sheets.
- quality_report: row counts, depth distribution, duplicate IDs, missing text, and time range.
- audit.jsonl: task, safety, source, and compliance records.

## View UTF-8 Files in PowerShell

```powershell
Get-Content exports\audit\audit.jsonl -Tail 1 -Encoding UTF8
Get-Content exports\reports\task-xxxx_quality_report.json -Encoding UTF8
```

## One-Click Acceptance

```powershell
.\scripts\run_acceptance.ps1
.\scripts\show_latest_outputs.ps1
```

To clean old outputs:

```powershell
.\scripts\clean_outputs.ps1 -Force
```

## Academic Compliance

This tool is for academic research workflows using mock fixtures or local JSON files. It does not provide automatic login, captcha bypass, rate-limit evasion, private endpoint access, or collection of inaccessible data.
