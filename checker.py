import os
import requests

URL = "https://diecasthunter.de/products/hot-wheels-factory-set-2026-1-4-inkl-hot-wheels-datsun-510-gasser-chase-1-64"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

response = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=20
)

response.raise_for_status()
page = response.text.lower()

# Solange diese Begriffe auf der Seite stehen,
# gehen wir davon aus, dass der Artikel noch nicht verfügbar ist.
out_of_stock = (
    "nicht vorrätig" in page
    or "ausverkauft" in page
)

if not out_of_stock:
    message = (
        "🚨 HOT WHEELS VERFÜGBAR! 🚨\n\n"
        "Hot Wheels Boulevard #156 Enzo Ferrari | 1:64\n\n"
        "💰 Jetzt prüfen und kaufen:\n"
        f"{URL}"
    )

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    print("Artikel verfügbar – Telegram-Nachricht gesendet!")
else:
    print("Noch nicht verfügbar.")
