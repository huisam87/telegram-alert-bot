# Send AI news digest to Telegram using config + .env.

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $scriptDir ".env"
$configPath = Join-Path $scriptDir "ai_news_config.json"
$digestScript = Join-Path $scriptDir "ai_news_digest.py"

if (-not (Test-Path $envPath)) {
  throw "Missing .env file at $envPath."
}
if (-not (Test-Path $configPath)) {
  throw "Missing config at $configPath."
}
if (-not (Test-Path $digestScript)) {
  throw "Missing digest script at $digestScript."
}

# Ensure Python is available.
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd -and $pythonCmd.Source -like "*WindowsApps*") {
  $pythonCmd = $null
}
if (-not $pythonCmd) {
  $fallback = Join-Path $env:LOCALAPPDATA "Programs\\Python\\Python312\\python.exe"
  if (Test-Path $fallback) {
    $pythonCmd = Get-Item $fallback
  }
}
if (-not $pythonCmd) {
  throw "Python is not installed or not on PATH. Install Python and try again."
}

# Load .env lines in KEY=VALUE form.
Get-Content $envPath | ForEach-Object {
  $line = $_.Trim()
  if ($line -and -not $line.StartsWith("#")) {
    $parts = $line.Split("=", 2)
    if ($parts.Length -eq 2) {
      $key = $parts[0].Trim()
      $value = $parts[1].Trim()
      [Environment]::SetEnvironmentVariable($key, $value)
    }
  }
}

$token = [Environment]::GetEnvironmentVariable("TELEGRAM_BOT_TOKEN")
$chatId = [Environment]::GetEnvironmentVariable("TELEGRAM_CHAT_ID")

if (-not $token) { throw "TELEGRAM_BOT_TOKEN is missing in .env." }
if (-not $chatId) { throw "TELEGRAM_CHAT_ID is missing in .env." }

$pythonPath = if ($pythonCmd.PSObject.Properties.Name -contains "Source") { $pythonCmd.Source } else { $pythonCmd.FullName }
$env:PYTHONUTF8 = "1"
$message = & $pythonPath -X utf8 $digestScript --config $configPath
if ($message -is [System.Array]) {
  $message = $message -join "`n"
}
if (-not $message) { throw "Digest message is empty." }

$uri = "https://api.telegram.org/bot$token/sendMessage"
$body = @{
  chat_id = $chatId
  text    = $message
  parse_mode = "HTML"
  disable_web_page_preview = $true
}

Invoke-RestMethod -Method Post -Uri $uri -Body $body | Out-Null
Write-Host "Digest sent."
