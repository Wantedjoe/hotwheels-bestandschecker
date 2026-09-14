import os
import requests

URL = "https://diecasthunter.de/products/hot-wheels-2026-team-transport-porsche-rexy-911-gt3-r-992-fleet-flyer-1-64"
# URL = "https://diecasthunter.de/products/hot-wheels-boulevard-155-2021-toyota-gr-supra-1-64"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATUS_FILE = "status.txt"
STOCK_FILE = "stock.txt"


def send_telegram(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()


def get_status():
    try:
        with open(STATUS_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "active"


def get_previous_stock():
    try:
        with open(STOCK_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


def save_stock(stock):
    with open(STOCK_FILE, "w") as f:
        f.write(stock)


# --------------------------------------------------
# 1. Prüfen, ob der Bestandschecker pausiert ist
# --------------------------------------------------

status = get_status()

if status == "paused":
    print("⏸️ Bestandsprüfung ist pausiert.")
    exit()


# --------------------------------------------------
# 2. Produktinformationen von Shopify abrufen
# --------------------------------------------------

response = requests.get(
    URL + ".js",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=20
)

response.raise_for_status()

product = response.json()


# --------------------------------------------------
# 3. Lagerbestand prüfen
# --------------------------------------------------

in_stock = any(
    variant.get("available", False)
    for variant in product["variants"]
)


current_stock = "in" if in_stock else "out"
previous_stock = get_previous_stock()

print(f"Vorheriger Status: {previous_stock}")
print(f"Aktueller Status:  {current_stock}")


# --------------------------------------------------
# 4. Nur bei einem echten RESTOCK alarmieren
# --------------------------------------------------

if current_stock == "in" and previous_stock == "out":

    message = (
        "🚨 HOT WHEELS ALARM! 🚨\n\n"
        f"{product['title']}\n\n"
        f"💰 Preis: {product['price'] / 100:.2f} €\n\n"
        "👉 Jetzt prüfen und kaufen:\n"
        f"{URL}"
    )

    send_telegram(message)

    print("🚨 Artikel wieder verfügbar – Telegram-Nachricht gesendet!")

elif current_stock == "in":
    print("Artikel ist verfügbar, aber bereits bekannt.")

else:
    print("Noch nicht verfügbar.")


# --------------------------------------------------
# 5. Aktuellen Status speichern
# --------------------------------------------------

save_stock(current_stock)
