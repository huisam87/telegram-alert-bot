# Telegram send test script.
# Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env in the same folder.

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $scriptDir ".env"

if (-not (Test-Path $envPath)) {
  throw "Missing .env file at $envPath. Create it based on .env.example."
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

$message = "텔레그램 봇 테스트 메시지입니다."
$uri = "https://api.telegram.org/bot$token/sendMessage"

$body = @{
  chat_id = $chatId
  text    = $message
}

Invoke-RestMethod -Method Post -Uri $uri -Body $body | Out-Null
Write-Host "Message sent."
