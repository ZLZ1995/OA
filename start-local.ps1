$ErrorActionPreference = 'Stop'

$Root = 'D:\1\OA-main-routing-pr2'
$FrontendDir = Join-Path $Root 'frontend'
$BackendDir = Join-Path $Root 'backend'
$LogsDir = Join-Path $Root 'logs'
$FrontendLog = Join-Path $LogsDir 'frontend-local.log'
$BackendLog = Join-Path $LogsDir 'backend-local.log'
$PidFile = Join-Path $LogsDir 'local-services.json'
$DatabaseUrl = 'sqlite:///D:/1/OA-main-routing-pr2/backend/local-dev.db'
$StorageDir = 'D:/1/OA-main-routing-pr2/backend/uploads'

New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

function Stop-PortProcess {
  param([int]$Port)
  $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($conn) {
    try {
      Stop-Process -Id $conn.OwningProcess -Force -ErrorAction Stop
      Start-Sleep -Milliseconds 800
    } catch {
    }
  }
}

Stop-PortProcess -Port 5173
Stop-PortProcess -Port 8080

if (Test-Path $FrontendLog) { Remove-Item $FrontendLog -Force }
if (Test-Path $BackendLog) { Remove-Item $BackendLog -Force }

$frontendCmd = "npm.cmd run dev -- --host 127.0.0.1 --port 5173 > `"$FrontendLog`" 2>&1"
$frontendProc = Start-Process -FilePath 'C:\Windows\System32\cmd.exe' `
  -ArgumentList '/c', $frontendCmd `
  -WorkingDirectory $FrontendDir `
  -WindowStyle Hidden `
  -PassThru

$backendCmd = "set DATABASE_URL=$DatabaseUrl&& set LOCAL_STORAGE_DIR=$StorageDir&& D:\1\OA-main-routing-pr2\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080 > `"$BackendLog`" 2>&1"
$backendProc = Start-Process -FilePath 'C:\Windows\System32\cmd.exe' `
  -ArgumentList '/c', $backendCmd `
  -WorkingDirectory $BackendDir `
  -WindowStyle Hidden `
  -PassThru

Start-Sleep -Seconds 5

$status = [ordered]@{
  frontend_pid = $frontendProc.Id
  backend_pid = $backendProc.Id
  frontend_url = 'http://127.0.0.1:5173'
  backend_url = 'http://127.0.0.1:8080'
  database_url = $DatabaseUrl
  started_at = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
}

$status | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8
Write-Output ($status | ConvertTo-Json)
