# Append a new daily section to 개인 작업용.md if missing.

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logPath = Join-Path $scriptDir "개인 작업용.md"

if (-not (Test-Path $logPath)) {
  throw "Missing log file at $logPath."
}

$today = (Get-Date).ToString("yyyy-MM-dd-dddd", [cultureinfo]"ko-KR")
$marker = "<summary>$today</summary>"

$content = Get-Content $logPath -Raw -Encoding UTF8
if ($content -match [regex]::Escape($marker)) {
  exit 0
}

$section = @"

<details open>
$marker

- 작업 요약:
  - 
- 결정 사항:
  - 
- 다음 할 일:
  - 

</details>
"@

Add-Content -Path $logPath -Value $section -Encoding UTF8
