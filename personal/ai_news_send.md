## AI 뉴스 알림 실행 방법

### 구성 방식
- 네이버 뉴스 RSS와 유튜브 RSS를 읽어 간단 요약을 만든다.
- 요약 결과를 텍스트로 생성하고 텔레그램으로 전송한다.
- 비밀값은 `.env`에만 저장해 코드에 직접 넣지 않는다.

### 준비
1) `.env`에 아래 값을 채운다.
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2) `ai_news_config.json`에서 키워드/툴/채널을 필요에 맞게 수정한다.

### 실행
```powershell
powershell -ExecutionPolicy Bypass -File C:\codex\personal\ai_news_send.ps1
```

### 코드 동작 설명
- `ai_news_digest.py`가 뉴스/유튜브 RSS를 가져와 도구별 섹션으로 요약한다.
- `ai_news_send.ps1`이 요약 텍스트를 받아 텔레그램 API(HTML 모드)로 전송한다.
- 유튜브 채널 ID는 한 번 조회 후 `.cache/channel_ids.json`에 캐시된다.
