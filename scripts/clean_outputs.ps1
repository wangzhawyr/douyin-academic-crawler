param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

$directories = @(
    "exports\comments",
    "exports\audit",
    "exports\logs",
    "exports\reports"
)

if (-not $Force) {
    $answer = Read-Host "This will delete files under exports/comments, exports/audit, exports/logs, and exports/reports. Continue? (y/N)"
    if ($answer -ne "y" -and $answer -ne "Y") {
        Write-Host "Cancelled."
        exit 0
    }
}

foreach ($directory in $directories) {
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
        continue
    }
    Get-ChildItem $directory -File -ErrorAction SilentlyContinue | Remove-Item -Force
}

Write-Host "Outputs cleaned."
