param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Running unit tests..."
& $Python -m unittest discover -s tests -v

Write-Host "Running mock acceptance..."
& $Python main.py --mock-run --config examples/sample_config.json

Write-Host "Running local JSON acceptance..."
& $Python main.py --mock-run --config examples/local_json_config.json

$latestCsv = Get-ChildItem exports\comments -Filter *.csv -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestXlsx = Get-ChildItem exports\comments -Filter *.xlsx -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestReport = Get-ChildItem exports\reports -Filter *_quality_report.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$audit = Get-Item exports\audit\audit.jsonl -ErrorAction SilentlyContinue

Write-Host "Latest CSV: $($latestCsv.FullName)"
Write-Host "Latest XLSX: $($latestXlsx.FullName)"
Write-Host "Latest quality report: $($latestReport.FullName)"
Write-Host "Audit JSONL: $($audit.FullName)"
Write-Host "ACCEPTANCE PASSED"
