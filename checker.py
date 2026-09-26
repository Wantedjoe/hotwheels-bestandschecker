import os
import re
import requests
from bs4 import BeautifulSoup

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
# Bestandsstatus für 3 URLs
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
# Shop erkennen
# --------------------------------------------------

def is_smyths(url):
    return "smythstoys.com" in url.lower()


# --------------------------------------------------
# Diecast Hunter prüfen
# --------------------------------------------------

def check_diecast_hunter(url):

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

    return in_stock, {
        "title": product.get("title", "Unbekanntes Produkt"),
        "price": product.get("price", 0),
        "url": url,
        "shop": "Diecast Hunter"
    }


# --------------------------------------------------
# Smyths prüfen
#
# WICHTIG:
# Hier wird ausschließlich Online-Bestellbarkeit
# berücksichtigt.
#
# Filialbestand / Click & Collect wird NICHT
# als "verfügbar" gewertet.
# --------------------------------------------------

def check_smyths(url):

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
        "Referer": "https://www.smythstoys.com/ch/de-ch/"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    html = response.text

    soup = BeautifulSoup(html, "html.parser")

    # --------------------------------------------------
    # Produktname ermitteln
    # --------------------------------------------------

    title = None

    meta_title = soup.find(
        "meta",
        property="og:title"
    )

    if meta_title:
        title = meta_title.get("content")

    if not title:
        title_tag = soup.find("title")

        if title_tag:
            title = title_tag.get_text(
                " ",
                strip=True
            )

    if not title:
        title = "Smyths Produkt"


    # --------------------------------------------------
    # Preis ermitteln
    # --------------------------------------------------

    price = None

    meta_price = soup.find(
        "meta",
        property="product:price:amount"
    )

    if meta_price:
        try:
            price = float(
                meta_price.get("content")
            )
        except (TypeError, ValueError):
            pass


    # --------------------------------------------------
    # JSON-LD Produktdaten versuchen
    # --------------------------------------------------

    if price is None:

        for script in soup.find_all(
            "script",
            type="application/ld+json"
        ):

            try:
                import json

                data = json.loads(
                    script.string or
                    script.get_text()
                )

                candidates = []

                if isinstance(data, dict):
                    candidates.append(data)

                    if "@graph" in data:
                        candidates.extend(
                            data["@graph"]
                        )

                elif isinstance(data, list):
                    candidates.extend(data)

                for item in candidates:

                    if not isinstance(item, dict):
                        continue

                    if item.get("@type") == "Product":

                        if not title and item.get("name"):
                            title = item["name"]

                        offers = item.get(
                            "offers"
                        )

                        if isinstance(
                            offers,
                            dict
                        ):
                            value = offers.get(
                                "price"
                            )

                            if value is not None:
                                try:
                                    price = float(
                                        value
                                    )
                                except (
                                    TypeError,
                                    ValueError
                                ):
                                    pass

                        break

            except Exception:
                continue


    # --------------------------------------------------
    # ONLINE-VERFÜGBARKEIT
    #
    # Wir suchen bewusst nur nach eindeutigen
    # Online-Shop-Signalen.
    # --------------------------------------------------

    text = soup.get_text(
        " ",
        strip=True
    )

    text_lower = text.lower()


    # --------------------------------------------------
    # Eindeutige "nicht verfügbar"-Signale
    # --------------------------------------------------

    unavailable_patterns = [
        "online nicht verfügbar",
        "online nicht lieferbar",
        "nicht online verfügbar",
        "derzeit nicht verfügbar",
        "derzeit nicht lieferbar",
        "online ausverkauft",
        "ausverkauft online"
    ]

    for pattern in unavailable_patterns:

        if pattern in text_lower:

            return False, {
                "title": title,
                "price": price,
                "url": url,
                "shop": "Smyths"
            }


    # --------------------------------------------------
    # Eindeutige Online-Kaufsignale
    # --------------------------------------------------

    available_patterns = [
        "in den warenkorb",
        "zum warenkorb",
        "online auf lager",
        "online lieferbar",
        "online verfügbar",
        "lieferbar"
    ]

    for pattern in available_patterns:

        if pattern in text_lower:

            return True, {
                "title": title,
                "price": price,
                "url": url,
                "shop": "Smyths"
            }


    # --------------------------------------------------
    # Wenn wir kein eindeutiges Signal finden:
    # Fehler statt "out".
    #
    # Dadurch wird ein Website-Layout-Änderung nicht
    # fälschlicherweise als "ausverkauft" gespeichert.
    # --------------------------------------------------

    raise RuntimeError(
        "Smyths: Keine eindeutige Information zur "
        "Online-Verfügbarkeit gefunden."
    )


# --------------------------------------------------
# Einheitliche Produktprüfung
# --------------------------------------------------

def check_stock(url):

    if is_smyths(url):
        return check_smyths(url)

    return check_diecast_hunter(url)


# --------------------------------------------------
# Telegram-Befehle abholen
# --------------------------------------------------

offset_text = read_file(
    OFFSET_FILE,
    "0"
)

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

updates = response.json().get(
    "result",
    []
)

status = read_file(
    STATUS_FILE,
    "active"
)

urls = read_urls()
stocks = read_stocks()


for update in updates:

    update_id = update["update_id"]

    offset = update_id + 1

    message = update.get(
        "message",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    text = message.get(
        "text",
        ""
    ).strip()


    # Nur deinen eigenen Telegram-Chat akzeptieren

    if str(chat.get("id")) != str(CHAT_ID):
        continue


    # --------------------------------------------------
    # /pause
    # --------------------------------------------------

    if text == "/pause":

        status = "paused"

        write_file(
            STATUS_FILE,
            status
        )

        send_telegram(
            "⏸️ Bestandscheck pausiert.\n\n"
            "Mit /start kannst du ihn wieder aktivieren."
        )


    # --------------------------------------------------
    # /start
    # --------------------------------------------------

    elif text == "/start":

        status = "active"

        write_file(
            STATUS_FILE,
            status
        )

        send_telegram(
            "▶️ Bestandscheck wieder aktiviert."
        )


    # --------------------------------------------------
    # /url
    # --------------------------------------------------

    elif text == "/url":

        message_lines = [
            "🔗 ÜBERWACHTE URLs\n"
        ]

        for i, url in enumerate(
            urls,
            start=1
        ):

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

        send_telegram(
            "\n".join(message_lines)
        )


    # --------------------------------------------------
    # /url1 /url2 /url3
    # --------------------------------------------------

    elif (
        text.startswith("/url1")
        or text.startswith("/url2")
        or text.startswith("/url3")
    ):

        command = text.split()[0]

        if command == "/url1":
            index = 0

        elif command == "/url2":
            index = 1

        else:
            index = 2


        parts = text.split(
            maxsplit=1
        )


        # Nur /url1 ohne URL

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

        if new_url.lower() in [
            "leer",
            "clear",
            "delete",
            "löschen"
        ]:

            urls[index] = ""

            stocks[index] = "unknown"

            write_urls(urls)
            write_stocks(stocks)

            send_telegram(
                f"🗑️ URL {index + 1} wurde gelöscht."
            )

            continue


        # URL prüfen

        if not (
            new_url.startswith("https://")
            or new_url.startswith("http://")
        ):

            send_telegram(
                "⚠️ Ungültige URL.\n\n"
                "Bitte eine vollständige URL senden."
            )

            continue


        # Neue URL speichern

        urls[index] = new_url

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
    # /status
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


        for i, url in enumerate(
            urls,
            start=1
        ):

            if not url:

                status_lines.append(
                    f"{i}. ⚪ kein Produkt"
                )

                continue


            found_url = True


            try:

                in_stock, product = check_stock(
                    url
                )


                if in_stock:

                    stock_text = (
                        "🟢 VERFÜGBAR"
                    )

                else:

                    stock_text = (
                        "🔴 NICHT VERFÜGBAR"
                    )


                shop_text = product.get(
                    "shop",
                    "Unbekannt"
                )


                status_lines.append(
                    f"{i}. {stock_text}\n"
                    f"🏪 {shop_text}\n"
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

write_file(
    OFFSET_FILE,
    str(offset)
)


# --------------------------------------------------
# Bei Pause keinen normalen Bestandscheck
# --------------------------------------------------

if status == "paused":

    print(
        "Bestandscheck ist pausiert."
    )

    exit()


# --------------------------------------------------
# Normalen Bestandscheck durchführen
# --------------------------------------------------

urls = read_urls()
stocks = read_stocks()


for index, url in enumerate(urls):

    if not url:

        print(
            f"URL {index + 1}: leer – übersprungen."
        )

        continue


    try:

        print(
            f"Prüfe URL {index + 1}: {url}"
        )


        in_stock, product = check_stock(
            url
        )


        old_stock = stocks[index]


        # --------------------------------------------------
        # Verfügbar
        # --------------------------------------------------

        if in_stock:

            new_stock = "in"


            # Nur echter Restock

            if old_stock == "out":

                price = product.get(
                    "price"
                )


                if isinstance(
                    price,
                    (int, float)
                ):

                    price_text = (
                        f"{price:.2f}"
                    )

                else:

                    price_text = (
                        "Preis nicht verfügbar"
                    )


                message = (
                    "🚨 HOT WHEELS ALARM! 🚨\n\n"
                    f"Produkt {index + 1}\n"
                    f"🏪 {product.get('shop', 'Shop')}\n\n"
                    f"{product['title']}\n\n"
                    f"💰 Preis: {price_text}\n\n"
                    f"👉 Jetzt prüfen und kaufen:\n"
                    f"{url}"
                )


                send_telegram(
                    message
                )


                print(
                    f"Produkt {index + 1} wieder "
                    "verfügbar – Telegram-Nachricht "
                    "gesendet!"
                )


            else:

                print(
                    f"Produkt {index + 1} verfügbar, "
                    "aber kein neuer Restock."
                )


        # --------------------------------------------------
        # Nicht verfügbar
        # --------------------------------------------------

        else:

            new_stock = "out"

            print(
                f"Produkt {index + 1} "
                "noch nicht verfügbar."
            )


        stocks[index] = new_stock


    except Exception as e:

        print(
            f"Fehler bei Produkt {index + 1}: {e}"
        )

        # Bei einem technischen Fehler alten
        # Bestand NICHT verändern.
        #
        # Dadurch wird z.B. ein 403 von Smyths
        # nicht fälschlicherweise zu "out".


# --------------------------------------------------
# Bestandsstatus speichern
# --------------------------------------------------

write_stocks(
    stocks
)

print(
    "Bestandsprüfung abgeschlossen."
)
