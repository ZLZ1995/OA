$ErrorActionPreference = 'SilentlyContinue'

$Root = 'C:\Users\946355064\Desktop\OA-main'
$LogsDir = Join-Path $Root 'logs'
$PidFile = Join-Path $LogsDir 'local-services.json'

function Stop-PortProcess {
  param([int]$Port)
  $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force
  }
}

if (Test-Path $PidFile) {
  try {
    $state = Get-Content $PidFile -Raw | ConvertFrom-Json
    foreach ($pid in @($state.frontend_pid, $state.backend_pid)) {
      if ($pid) {
        Stop-Process -Id $pid -Force
      }
    }
  } catch {
  }
  Remove-Item $PidFile -Force
}

Stop-PortProcess -Port 5173
Stop-PortProcess -Port 8080

Write-Output 'local services stopped'
