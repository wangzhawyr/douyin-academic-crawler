$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

$latestCsv = Get-ChildItem exports\comments -Filter *.csv -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestXlsx = Get-ChildItem exports\comments -Filter *.xlsx -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestReport = Get-ChildItem exports\reports -Filter *_quality_report.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "Latest CSV: $($latestCsv.FullName)"
Write-Host "Latest XLSX: $($latestXlsx.FullName)"
Write-Host "Latest quality report: $($latestReport.FullName)"

if (Test-Path exports\audit\audit.jsonl) {
    Write-Host "Latest audit record:"
    Get-Content exports\audit\audit.jsonl -Tail 1 -Encoding UTF8
} else {
    Write-Host "Audit JSONL not found."
}
