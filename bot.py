import os
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATUS_FILE = "status.txt"

def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text
        },
        timeout=20
    )

def get_status():
    if not os.path.exists(STATUS_FILE):
        return "active"

    with open(STATUS_FILE, "r") as f:
        return f.read().strip()

def set_status(status):
    with open(STATUS_FILE, "w") as f:
        f.write(status)

offset = None

while True:
    response = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/getUpdates",
        params={
            "offset": offset,
            "timeout": 30
        },
        timeout=40
    )

    data = response.json()

    for update in data.get("result", []):
        offset = update["update_id"] + 1

        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "").strip().lower()

        # Nur auf deine Telegram-ID reagieren
        if chat_id != CHAT_ID:
            continue

        if text == "/pause":
            set_status("paused")
            send_message("⏸️ Bestandsprüfung pausiert.")

        elif text == "/start":
            set_status("active")
            send_message("▶️ Bestandsprüfung wieder aktiviert.")

        elif text == "/status":
            status = get_status()

            if status == "paused":
                send_message("⏸️ Bestandsprüfung ist pausiert.")
            else:
                send_message("▶️ Bestandsprüfung ist aktiv.")
