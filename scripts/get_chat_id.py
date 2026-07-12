"""Helper script to get your Telegram chat ID.

1. Open Telegram and send a message to your bot (any message)
2. Run this script
3. Copy the chat ID into your .env file
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config.settings import Settings

settings = Settings()

if not settings.TELEGRAM_TOKEN:
    print("TELEGRAM_TOKEN not set in .env")
    sys.exit(1)

import requests

resp = requests.get(
    f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/getUpdates",
    timeout=10,
)
data = resp.json()

if not data.get("ok") or not data.get("result"):
    print("No updates found. Send a message to your bot on Telegram first, then run this again.")
    sys.exit(1)

for update in data["result"]:
    message = update.get("message") or update.get("my_chat_member", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "unknown")
    title = chat.get("title") or chat.get("first_name", "")
    print(f"Chat: {title} ({chat_type}) -> ID: {chat_id}")
    print(f"\nAdd this to your .env:\nTELEGRAM_CHAT_ID={chat_id}")
