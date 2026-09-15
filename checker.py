import os
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATUS_FILE = "status.txt"
STOCK_FILE = "stock.txt"
OFFSET_FILE = "telegram_offset.txt"
URL_FILE = "urls.txt"


# --------------------------------------------------
# Telegram
# --------------------------------------------------

def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )


# --------------------------------------------------
# Dateien lesen / schreiben
# --------------------------------------------------

def read_file(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return default


def write_file(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


# --------------------------------------------------
# URLs aus urls.txt lesen
# Maximal 3 URLs
# --------------------------------------------------

def read_urls():
    try:
        with open(URL_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []

    # Genau 3 Plätze vorbereiten
    urls = lines[:3]

    while len(urls) < 3:
        urls.append("")

    return urls


def write_urls(urls):
    urls = urls[:3]

    while len(urls) < 3:
        urls.append("")

    with open(URL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(urls) + "\n")


# --------------------------------------------------
# Bestandsstatus für 3 URLs lesen / schreiben
# --------------------------------------------------

def read_stocks():
    try:
        with open(STOCK_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []

    stocks = lines[:3]

    while len(stocks) < 3:
        stocks.append("unknown")

    return stocks


def write_stocks(stocks):
    stocks = stocks[:3]

    while len(stocks) < 3:
        stocks.append("unknown")

    with open(STOCK_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(stocks) + "\n")


# --------------------------------------------------
# Produkt prüfen
# --------------------------------------------------

def check_stock(url):
    response = requests.get(
        url + ".js",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )

    response.raise_for_status()

    product = response.json()

    in_stock = any(
        variant.get("available", False)
        for variant in product["variants"]
    )

    return in_stock, product


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

urls = read_urls()
stocks = read_stocks()


for update in updates:

    update_id = update["update_id"]

    # Offset auf nächsten Update setzen
    offset = update_id + 1

    message = update.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text", "").strip()

    # Nur deinen eigenen Telegram-Chat akzeptieren
    if str(chat.get("id")) != str(CHAT_ID):
        continue


    # --------------------------------------------------
    # /pause
    # --------------------------------------------------

    if text == "/pause":

        status = "paused"
        write_file(STATUS_FILE, status)

        send_telegram(
            "⏸️ Bestandscheck pausiert.\n\n"
            "Mit /start kannst du ihn wieder aktivieren."
        )


    # --------------------------------------------------
    # /start
    # --------------------------------------------------

    elif text == "/start":

        status = "active"
        write_file(STATUS_FILE, status)

        send_telegram(
            "▶️ Bestandscheck wieder aktiviert."
        )


    # --------------------------------------------------
    # /url
    # Aktuelle URLs anzeigen
    # --------------------------------------------------

    elif text == "/url":

        message_lines = [
            "🔗 ÜBERWACHTE URLs\n"
        ]

        for i, url in enumerate(urls, start=1):

            if url:
                message_lines.append(
                    f"{i}. 🟢 {url}"
                )
            else:
                message_lines.append(
                    f"{i}. ⚪ leer"
                )

        message_lines.append(
            "\nÄndern mit:\n"
            "/url1 https://...\n"
            "/url2 https://...\n"
            "/url3 https://...\n\n"
            "Zum Löschen:\n"
            "/url1 leer"
        )

        send_telegram("\n".join(message_lines))


    # --------------------------------------------------
    # /url1
    # /url2
    # /url3
    # --------------------------------------------------

    elif text.startswith("/url1") or \
         text.startswith("/url2") or \
         text.startswith("/url3"):

        command = text.split()[0]

        if command == "/url1":
            index = 0
        elif command == "/url2":
            index = 1
        else:
            index = 2

        parts = text.split(maxsplit=1)

        # Nur /url1 ohne URL:
        if len(parts) == 1:

            if urls[index]:
                send_telegram(
                    f"🔗 URL {index + 1}:\n\n"
                    f"{urls[index]}"
                )
            else:
                send_telegram(
                    f"🔗 URL {index + 1} ist leer."
                )

            continue

        new_url = parts[1].strip()

        # URL löschen
        if new_url.lower() in ["leer", "clear", "delete", "löschen"]:

            urls[index] = ""

            # Alten Bestand zurücksetzen
            stocks[index] = "unknown"

            write_urls(urls)
            write_stocks(stocks)

            send_telegram(
                f"🗑️ URL {index + 1} wurde gelöscht."
            )

            continue

        # Einfache URL-Prüfung
        if not (
            new_url.startswith("https://")
            or new_url.startswith("http://")
        ):

            send_telegram(
                "⚠️ Ungültige URL.\n\n"
                "Bitte eine vollständige URL senden, "
                "z. B.:\n"
                "/url1 https://example.com/produkt"
            )

            continue

        # Neue URL speichern
        urls[index] = new_url

        # Wichtig:
        # Alten Bestandsstatus zurücksetzen,
        # damit kein falscher Restock-Alarm entsteht.
        stocks[index] = "unknown"

        write_urls(urls)
        write_stocks(stocks)

        send_telegram(
            f"✅ URL {index + 1} gespeichert.\n\n"
            f"{new_url}\n\n"
            "Der nächste Bestandscheck startet "
            "mit einem neuen Status."
        )


    # --------------------------------------------------
    # /status – LIVE-Abfrage aller Produkte
    # --------------------------------------------------

    elif text == "/status":

        if status == "paused":
            status_text = "⏸️ pausiert"
        else:
            status_text = "▶️ aktiv"

        status_lines = [
            "ℹ️ LIVE-STATUS\n",
            f"Bestandscheck: {status_text}\n"
        ]

        found_url = False

        for i, url in enumerate(urls, start=1):

            if not url:
                status_lines.append(
                    f"{i}. ⚪ kein Produkt"
                )
                continue

            found_url = True

            try:

                in_stock, product = check_stock(url)

                if in_stock:
                    stock_text = "🟢 VERFÜGBAR"
                else:
                    stock_text = "🔴 NICHT VERFÜGBAR"

                status_lines.append(
                    f"{i}. {stock_text}\n"
                    f"{product['title']}"
                )

            except Exception as e:

                status_lines.append(
                    f"{i}. ⚠️ Fehler bei der Abfrage\n"
                    f"{str(e)}"
                )

        if not found_url:
            status_lines.append(
                "\nKeine URLs eingerichtet."
            )

        send_telegram(
            "\n\n".join(status_lines)
        )


# --------------------------------------------------
# Offset speichern
# --------------------------------------------------

write_file(OFFSET_FILE, str(offset))


# --------------------------------------------------
# Bei Pause keinen normalen Bestandscheck durchführen
# --------------------------------------------------

if status == "paused":

    print("Bestandscheck ist pausiert.")
    exit()


# --------------------------------------------------
# Normalen Bestandscheck für bis zu 3 URLs durchführen
# --------------------------------------------------

urls = read_urls()
stocks = read_stocks()

for index, url in enumerate(urls):

    # Leere URL überspringen
    if not url:
        print(
            f"URL {index + 1}: leer – übersprungen."
        )
        continue

    try:

        print(
            f"Prüfe URL {index + 1}: {url}"
        )

        in_stock, product = check_stock(url)

        old_stock = stocks[index]


        # --------------------------------------------------
        # Produkt verfügbar
        # --------------------------------------------------

        if in_stock:

            new_stock = "in"

            # Nur bei echter Wiederverfügbarkeit alarmieren
            if old_stock == "out":

                message = (
                    "🚨 HOT WHEELS ALARM! 🚨\n\n"
                    f"Produkt {index + 1}\n\n"
                    f"{product['title']}\n\n"
                    f"💰 Preis: "
                    f"{product['price'] / 100:.2f} €\n\n"
                    f"👉 Jetzt prüfen und kaufen:\n"
                    f"{url}"
                )

                send_telegram(message)

                print(
                    f"Produkt {index + 1} wieder verfügbar – "
                    "Telegram-Nachricht gesendet!"
                )

            else:

                print(
                    f"Produkt {index + 1} verfügbar, "
                    "aber kein neuer Restock."
                )


        # --------------------------------------------------
        # Produkt nicht verfügbar
        # --------------------------------------------------

        else:

            new_stock = "out"

            print(
                f"Produkt {index + 1} noch nicht verfügbar."
            )


        # Status speichern
        stocks[index] = new_stock

    except Exception as e:

        print(
            f"Fehler bei Produkt {index + 1}: {e}"
        )

        # Alten Status bei einem Fehler behalten.
        # Dadurch wird ein vorübergehender Fehler
        # nicht fälschlicherweise als "out" gewertet.


# --------------------------------------------------
# Aktuellen Bestand für alle 3 URLs speichern
# --------------------------------------------------

write_stocks(stocks)

print("Bestandsprüfung abgeschlossen.")
