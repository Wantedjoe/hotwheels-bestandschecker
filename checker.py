import os
import requests

URL = "https://diecasthunter.de/products/hot-wheels-2026-team-transport-porsche-rexy-911-gt3-r-992-fleet-flyer-1-64"
# URL = "https://diecasthunter.de/products/hot-wheels-boulevard-155-2021-toyota-gr-supra-1-64"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATUS_FILE = "status.txt"
STOCK_FILE = "stock.txt"
OFFSET_FILE = "telegram_offset.txt"


def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )


def read_file(filename, default):
    try:
        with open(filename, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return default


def write_file(filename, content):
    with open(filename, "w") as f:
        f.write(content)


# --------------------------------------------------
# Telegram-Befehle abholen
# --------------------------------------------------

offset_text = read_file(OFFSET_FILE, "0")
offset = int(offset_text)

response = requests.get(
    f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
    params={
        "offset": offset,
        "timeout": 5
    },
    timeout=15
)

response.raise_for_status()

updates = response.json().get("result", [])

status = read_file(STATUS_FILE, "active")

for update in updates:
    update_id = update["update_id"]

    # Offset auf nächsten Update setzen
    offset = update_id + 1

    message = update.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text", "").strip()

    # Nur Befehle von DEINEM Chat akzeptieren
    if str(chat.get("id")) != str(CHAT_ID):
        continue

    if text == "/pause":
        status = "paused"
        write_file(STATUS_FILE, status)

        send_telegram(
            "⏸️ Bestandscheck pausiert.\n\n"
            "Mit /start kannst du ihn wieder aktivieren."
        )

    elif text == "/start":
        status = "active"
        write_file(STATUS_FILE, status)

        send_telegram(
            "▶️ Bestandscheck wieder aktiviert."
        )

    elif text == "/status":
        stock = read_file(STOCK_FILE, "unknown")

        if status == "paused":
            status_text = "⏸️ pausiert"
        else:
            status_text = "▶️ aktiv"

        if stock == "in":
            stock_text = "🟢 verfügbar"
        elif stock == "out":
            stock_text = "🔴 nicht verfügbar"
        else:
            stock_text = "⚪ noch unbekannt"

        send_telegram(
            f"ℹ️ Status\n\n"
            f"Bestandscheck: {status_text}\n"
            f"Artikel: {stock_text}"
        )


# Offset speichern
write_file(OFFSET_FILE, str(offset))


# --------------------------------------------------
# Prüfen, ob der Bestandscheck pausiert ist
# --------------------------------------------------

if status == "paused":
    print("Bestandscheck ist pausiert.")
    exit()


# --------------------------------------------------
# Produkt prüfen
# --------------------------------------------------

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


# --------------------------------------------------
# Alten Bestand auslesen
# --------------------------------------------------

old_stock = read_file(STOCK_FILE, "unknown")


# --------------------------------------------------
# Nur bei echter Wiederverfügbarkeit alarmieren
# --------------------------------------------------

if in_stock:
    new_stock = "in"

    if old_stock == "out":
        message = (
            "🚨 HOT WHEELS ALARM! 🚨\n\n"
            f"{product['title']}\n\n"
            f"💰 Preis: {product['price'] / 100:.2f} €\n\n"
            f"👉 Jetzt prüfen und kaufen:\n{URL}"
        )

        send_telegram(message)

        print("Artikel wieder verfügbar – Telegram-Nachricht gesendet!")

    else:
        print("Artikel verfügbar, aber kein neuer Restock.")

else:
    new_stock = "out"
    print("Noch nicht verfügbar.")


# --------------------------------------------------
# Aktuellen Bestand speichern
# --------------------------------------------------

write_file(STOCK_FILE, new_stock)
