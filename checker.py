import os
import requests

# URL = "https://diecasthunter.de/products/hot-wheels-2026-team-transport-porsche-rexy-911-gt3-r-992-fleet-flyer-1-64"
URL = "https://diecasthunter.de/products/hot-wheels-boulevard-155-2021-toyota-gr-supra-1-64"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

response = requests.get(
    URL + ".js",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=20
)

response.raise_for_status()

product = response.json()

in_stock = any(
    variant.get("available", False)
    for variant in product["variants"]
)

if in_stock:
    message = (
        "🚨 HOT WHEELS VERFÜGBAR! 🚨\n\n"
        f"{product['title']}\n\n"
        f"💰 Preis: {product['price'] / 100:.2f} €\n\n"
        f"👉 Jetzt prüfen und kaufen:\n{URL}"
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
