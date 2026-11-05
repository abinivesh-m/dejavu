# One-command local run.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run.ps1
#
# Starts Hindsight (if it is not already running), seeds SQLite, pushes the
# corpus into the memory bank if needed, then starts the app.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

function Test-Port($port) {
    try { return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop) }
    catch { return $false }
}

$python = "python"
if (Test-Path ".venv\Scripts\python.exe") { $python = ".venv\Scripts\python.exe" }

Write-Host "`n  Deja Vu" -ForegroundColor Yellow
Write-Host "  on-call memory, backed by Hindsight`n" -ForegroundColor DarkGray

# ---------------------------------------------------------------- Hindsight
if (Test-Port 8888) {
    Write-Host "  [ok]   Hindsight already listening on :8888" -ForegroundColor Green
} elseif (Test-Path ".venv-hindsight\Scripts\hindsight-api.exe") {
    Write-Host "  [..]   starting Hindsight on :8888" -ForegroundColor DarkGray
    $env:HINDSIGHT_API_LLM_PROVIDER = "ollama"
    $env:HINDSIGHT_API_LLM_MODEL = "qwen3:4b-instruct"
    $env:HINDSIGHT_API_LLM_BASE_URL = "http://127.0.0.1:11434"
    Start-Process -FilePath ".venv-hindsight\Scripts\hindsight-api.exe" `
        -ArgumentList "--host", "127.0.0.1", "--port", "8888" `
        -WindowStyle Hidden
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        if (Test-Port 8888) { break }
    }
    if (Test-Port 8888) { Write-Host "  [ok]   Hindsight is up" -ForegroundColor Green }
    else { Write-Host "  [warn] Hindsight did not start; the app will use the BM25 mirror" -ForegroundColor Yellow }
} else {
    Write-Host "  [warn] hindsight-api not installed; the app will use the BM25 mirror" -ForegroundColor Yellow
}

# --------------------------------------------------------------------- data
if (-not (Test-Path "data\dejavu.db")) {
    Write-Host "  [..]   seeding 34 incidents" -ForegroundColor DarkGray
    & $python -m dejavu.seed
}

# ------------------------------------------------------------------ memory
if (Test-Port 8888) {
    Write-Host "  [..]   syncing the bank (skips documents already retained)" -ForegroundColor DarkGray
    & $python -m scripts.push_memories --skip-existing | Out-Host
}

# --------------------------------------------------------------------- app
Write-Host "  [ok]   app on http://127.0.0.1:8011`n" -ForegroundColor Green
& $python -m dejavu.web --port 8011
