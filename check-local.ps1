$ErrorActionPreference = 'SilentlyContinue'

$Root = 'C:\Users\946355064\Desktop\OA-main'
$LogsDir = Join-Path $Root 'logs'
$PidFile = Join-Path $LogsDir 'local-services.json'
$BackendEnv = Join-Path $Root 'backend\.env'

$result = [ordered]@{
  frontend_port_5173 = $false
  backend_port_8080 = $false
  backend_openapi_ok = $false
  frontend_proxy_login_status = $null
  backend_env = $null
  pid_file = $null
}

$frontendConn = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$backendConn = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1

$result.frontend_port_5173 = [bool]$frontendConn
$result.backend_port_8080 = [bool]$backendConn

if (Test-Path $PidFile) {
  $result.pid_file = Get-Content $PidFile -Raw
}

if (Test-Path $BackendEnv) {
  $result.backend_env = Get-Content $BackendEnv -Raw
}

try {
  $openapi = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8080/openapi.json' -TimeoutSec 5
  $result.backend_openapi_ok = ($openapi.StatusCode -eq 200)
} catch {
}

try {
  $loginBody = @{ username = 'zhongqin123'; password = 'zhongqin123' } | ConvertTo-Json
  $loginResp = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5173/api/v1/auth/login' -Method Post -Body $loginBody -ContentType 'application/json' -TimeoutSec 8
  $result.frontend_proxy_login_status = $loginResp.StatusCode
} catch {
  if ($_.Exception.Response) {
    $result.frontend_proxy_login_status = $_.Exception.Response.StatusCode.value__
  } else {
    $result.frontend_proxy_login_status = $_.Exception.Message
  }
}

$result | ConvertTo-Json
