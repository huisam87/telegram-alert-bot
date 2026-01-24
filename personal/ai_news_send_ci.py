#!/usr/bin/env python3
import os
import subprocess
import sys
import urllib.parse
import urllib.request


def build_message():
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "ai_news_digest.py", "--config", "ai_news_config.json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Digest command failed.")
    message = result.stdout.strip()
    if not message:
        raise RuntimeError("Digest message is empty.")
    return message


def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is missing.")
    message = build_message()
    send_telegram(token, chat_id, message)
    print("Digest sent.")


if __name__ == "__main__":
    main()
