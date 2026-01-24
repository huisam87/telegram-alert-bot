## 텔레그램 전송 테스트 스크립트 안내

### 구성 방식
- 비밀값(토큰, chat ID)을 코드에 직접 넣지 않고 `.env` 파일로 분리.
- PowerShell의 `Invoke-RestMethod`로 텔레그램 API에 POST 요청.
- 같은 폴더의 `.env`만 있으면 바로 실행 가능하도록 구성.

### 준비
1) `C:\codex\personal\.env.example`을 복사해 `.env`로 만들기.
2) `.env`에 아래 값을 채우기.
   - `TELEGRAM_BOT_TOKEN`: BotFather에서 받은 토큰
   - `TELEGRAM_CHAT_ID`: 내 계정 또는 채널의 chat ID

### 실행
```powershell
pwsh C:\codex\personal\telegram_send.ps1
```

### 코드 동작 설명
- `.env` 파일을 읽어 `KEY=VALUE` 형식만 파싱한다.
- `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`가 없으면 즉시 에러를 낸다.
- `https://api.telegram.org/bot{token}/sendMessage`로 POST 요청을 보낸다.
- 요청 바디에는 `chat_id`와 `text`만 전송한다.
- 성공 시 "Message sent."를 출력한다.
