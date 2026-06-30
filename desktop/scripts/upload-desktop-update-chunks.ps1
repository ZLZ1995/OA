param(
  [Parameter(Mandatory = $true)]
  [string]$AccessToken,
  [string]$BackendBaseUrl = 'https://zhongqinoa.zeabur.app',
  [string]$PublishDir = 'D:\1\OA-main-routing-pr2\desktop\out-update-publish',
  [int]$ChunkSizeMb = 8
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Net.Http

if ($ChunkSizeMb -le 0) {
  throw 'ChunkSizeMb must be greater than 0'
}

$chunkSize = $ChunkSizeMb * 1024 * 1024
$publishRoot = Resolve-Path $PublishDir

$smallFiles = @(
  (Join-Path $publishRoot 'latest.yml'),
  (Join-Path $publishRoot 'release.json')
)

$largeFiles = Get-ChildItem -Path $publishRoot -File |
  Where-Object { $_.Extension -eq '.exe' -or $_.Name -like '*.exe.blockmap' } |
  Sort-Object Name

$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromMinutes(30)
$client.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue('Bearer', $AccessToken)

function Get-Sha256Hex {
  param([string]$Path)
  $hash = Get-FileHash -LiteralPath $Path -Algorithm SHA256
  return $hash.Hash.ToLowerInvariant()
}

function Invoke-SmallFileUpload {
  param([string]$Path)
  $name = [System.IO.Path]::GetFileName($Path)
  Write-Host "Uploading small file: $name"
  $form = New-Object System.Net.Http.MultipartFormDataContent
  $stream = [System.IO.File]::OpenRead($Path)
  try {
    $content = New-Object System.Net.Http.StreamContent($stream)
    $content.Headers.ContentType = New-Object System.Net.Http.Headers.MediaTypeHeaderValue('application/octet-stream')
    $form.Add($content, 'upload', $name)
    $response = $client.PostAsync("$BackendBaseUrl/api/v1/desktop-updates/upload", $form).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
      throw "Upload failed for $name => $($response.StatusCode): $body"
    }
    Write-Host $body
  } finally {
    $stream.Dispose()
    $form.Dispose()
  }
}

function Invoke-LargeFileUpload {
  param([System.IO.FileInfo]$File)

  $fileName = $File.Name
  $sha256 = Get-Sha256Hex -Path $File.FullName
  $chunkCount = [int][Math]::Ceiling($File.Length / $chunkSize)
  Write-Host "Creating upload session: $fileName ($($File.Length) bytes, $chunkCount chunks)"

  $createPayload = @{
    file_name = $fileName
    total_size = $File.Length
    chunk_size = $chunkSize
    sha256 = $sha256
  } | ConvertTo-Json

  $createContent = New-Object System.Net.Http.StringContent($createPayload, [System.Text.Encoding]::UTF8, 'application/json')
  $createResponse = $client.PostAsync("$BackendBaseUrl/api/v1/desktop-updates/upload-session", $createContent).GetAwaiter().GetResult()
  $createBody = $createResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()
  if (-not $createResponse.IsSuccessStatusCode) {
    throw "Create session failed for $fileName => $($createResponse.StatusCode): $createBody"
  }

  $session = $createBody | ConvertFrom-Json
  $uploadId = $session.uploadId
  Write-Host "Upload session created: $uploadId"

  $stream = [System.IO.File]::OpenRead($File.FullName)
  try {
    $buffer = New-Object byte[] $chunkSize
    for ($chunkIndex = 0; $chunkIndex -lt $chunkCount; $chunkIndex++) {
      $remaining = $File.Length - $stream.Position
      $bytesToRead = [Math]::Min($chunkSize, $remaining)
      $bytesRead = $stream.Read($buffer, 0, $bytesToRead)
      if ($bytesRead -ne $bytesToRead) {
        throw "Unexpected bytes read for $fileName chunk $chunkIndex"
      }

      $form = New-Object System.Net.Http.MultipartFormDataContent
      try {
        $form.Add((New-Object System.Net.Http.StringContent($uploadId)), 'upload_id')
        $form.Add((New-Object System.Net.Http.StringContent([string]$chunkIndex)), 'chunk_index')

        $chunkBytes = New-Object byte[] $bytesRead
        [Array]::Copy($buffer, $chunkBytes, $bytesRead)
        $chunkContent = New-Object System.Net.Http.ByteArrayContent($chunkBytes)
        $chunkContent.Headers.ContentType = New-Object System.Net.Http.Headers.MediaTypeHeaderValue('application/octet-stream')
        $form.Add($chunkContent, 'upload', "$fileName.part")

        $chunkResponse = $client.PostAsync("$BackendBaseUrl/api/v1/desktop-updates/upload-chunk", $form).GetAwaiter().GetResult()
        $chunkBody = $chunkResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $chunkResponse.IsSuccessStatusCode) {
          throw "Chunk upload failed for $fileName chunk $chunkIndex => $($chunkResponse.StatusCode): $chunkBody"
        }
      } finally {
        $form.Dispose()
      }

      Write-Host ("Uploaded chunk {0}/{1}: {2}" -f ($chunkIndex + 1), $chunkCount, $fileName)
    }
  } finally {
    $stream.Dispose()
  }

  $completePayload = @{ upload_id = $uploadId } | ConvertTo-Json
  $completeContent = New-Object System.Net.Http.StringContent($completePayload, [System.Text.Encoding]::UTF8, 'application/json')
  $completeResponse = $client.PostAsync("$BackendBaseUrl/api/v1/desktop-updates/upload-complete", $completeContent).GetAwaiter().GetResult()
  $completeBody = $completeResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()
  if (-not $completeResponse.IsSuccessStatusCode) {
    throw "Complete upload failed for $fileName => $($completeResponse.StatusCode): $completeBody"
  }

  Write-Host "Upload completed: $fileName"
  Write-Host $completeBody
}

try {
  foreach ($file in $smallFiles) {
    if (-not (Test-Path $file)) {
      throw "Small file missing: $file"
    }
    Invoke-SmallFileUpload -Path $file
  }

  foreach ($file in $largeFiles) {
    Invoke-LargeFileUpload -File $file
  }
} finally {
  $client.Dispose()
}

Write-Host 'Desktop update publish upload completed.'
