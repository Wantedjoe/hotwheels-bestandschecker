import os
import re
import requests

from playwright.sync_api import sync_playwright


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
# URLs
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
# Bestandsstatus
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
# Diecast Hunter
# --------------------------------------------------

def check_diecast_hunter(url):

    response = requests.get(
        url + ".js",
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=20
    )

    response.raise_for_status()

    product = response.json()

    in_stock = any(
        variant.get("available", False)
        for variant in product.get("variants", [])
    )

    return in_stock, {
        "title": product.get(
            "title",
            "Unbekanntes Produkt"
        ),
        "price": (
            product.get("price", 0) / 100
            if isinstance(product.get("price"), (int, float))
            else 0
        ),
        "url": url,
        "shop": "Diecast Hunter"
    }


# --------------------------------------------------
# Smyths – Browserprüfung
# --------------------------------------------------

def check_smyths_with_browser(page, url):

    print(f"Smyths wird geprüft: {url}")

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    # Smyths lädt Verfügbarkeitsinformationen teilweise
    # nach dem eigentlichen Seitenaufbau.
    try:
        page.wait_for_load_state(
            "networkidle",
            timeout=15000
        )
    except Exception:
        pass

    # Kurz warten, damit die dynamischen Produktdaten
    # vollständig in den DOM gelangen.
    page.wait_for_timeout(3000)

    title = "Smyths Produkt"

    try:
        title = page.locator("h1").first.inner_text(
            timeout=5000
        ).strip()
    except Exception:
        try:
            title = page.title()
        except Exception:
            pass


    # --------------------------------------------------
    # Preis suchen
    # --------------------------------------------------

    price = None

    try:

        price_meta = page.locator(
            'meta[property="product:price:amount"]'
        ).first

        if price_meta.count() > 0:

            value = price_meta.get_attribute(
                "content"
            )

            if value:
                price = float(
                    value.replace(",", ".")
                )

    except Exception:
        pass


    # --------------------------------------------------
    # 1. Wichtigster Smyths-Selector
    #
    # Home Delivery
    #
    # Ältere Smyths-Implementierungen verwenden:
    #
    # p.deliveryType.homeDelivery.js-stockStatus
    # --------------------------------------------------

    selectors = [
        "p.deliveryType.homeDelivery.js-stockStatus",
        ".homeDelivery.js-stockStatus",
        "[name='js-stockStatusCode']",
        "[data-stock-status]",
        "[data-stockstatus]"
    ]


    found_information = False


    for selector in selectors:

        try:

            locator = page.locator(selector)

            count = locator.count()

            if count == 0:
                continue


            for i in range(min(count, 5)):

                element = locator.nth(i)

                try:
                    text = element.inner_text(
                        timeout=2000
                    ).strip()
                except Exception:
                    text = ""


                try:
                    classes = (
                        element.get_attribute("class")
                        or ""
                    )
                except Exception:
                    classes = ""


                try:
                    value = (
                        element.get_attribute("value")
                        or ""
                    )
                except Exception:
                    value = ""


                try:
                    data_status = (
                        element.get_attribute(
                            "data-stock-status"
                        )
                        or ""
                    )
                except Exception:
                    data_status = ""


                combined = " ".join([
                    text,
                    classes,
                    value,
                    data_status
                ]).lower()


                print(
                    f"Smyths selector: {selector}"
                )
                print(
                    f"Smyths status data: {combined[:500]}"
                )


                # --------------------------------------------------
                # Eindeutig verfügbar
                # --------------------------------------------------

                if (
                    "in stock" in combined
                    or "instock" in combined
                    or "auf lager" in combined
                    or "auf lager" in combined
                    or "available" in combined
                    or "lieferbar" in combined
                ):

                    found_information = True

                    return True, {
                        "title": title,
                        "price": price,
                        "url": url,
                        "shop": "Smyths"
                    }


                # --------------------------------------------------
                # Eindeutig nicht verfügbar
                # --------------------------------------------------

                if (
                    "out of stock" in combined
                    or "outofstock" in combined
                    or "nicht auf lager" in combined
                    or "nicht verfügbar" in combined
                    or "unavailable" in combined
                    or "ausverkauft" in combined
                ):

                    found_information = True

                    return False, {
                        "title": title,
                        "price": price,
                        "url": url,
                        "shop": "Smyths"
                    }


        except Exception as e:

            print(
                f"Smyths Selector {selector} Fehler: {e}"
            )


    # --------------------------------------------------
    # 2. Prüfen auf grünes Check-Symbol
    #
    # Ein älterer Smyths-Checker verwendet beim
    # Home-Delivery-Element die Klasse:
    #
    # fa fa-check green-check
    # --------------------------------------------------

    try:

        home_delivery = page.locator(
            "p.deliveryType.homeDelivery.js-stockStatus"
        )

        if home_delivery.count() > 0:

            html = home_delivery.first.evaluate(
                "(element) => element.outerHTML"
            )

            html_lower = html.lower()

            print(
                "Smyths Home-Delivery HTML:"
            )

            print(
                html[:1000]
            )


            if "green-check" in html_lower:

                return True, {
                    "title": title,
                    "price": price,
                    "url": url,
                    "shop": "Smyths"
                }


            # --------------------------------------------------
            # Wenn das Home-Delivery-Element existiert,
            # aber ausdrücklich keinen grünen Check besitzt,
            # suchen wir nach einem eindeutigen OOS-Signal.
            # --------------------------------------------------

            if (
                "out of stock" in html_lower
                or "outofstock" in html_lower
                or "not available" in html_lower
                or "unavailable" in html_lower
            ):

                return False, {
                    "title": title,
                    "price": price,
                    "url": url,
                    "shop": "Smyths"
                }


    except Exception as e:

        print(
            f"Smyths Home-Delivery-Prüfung Fehler: {e}"
        )


    # --------------------------------------------------
    # 3. Kaufen/Warenkorb prüfen
    #
    # Nur wenn eindeutig ein Online-Kaufbutton
    # vorhanden ist.
    # --------------------------------------------------

    cart_selectors = [
        "button:has-text('Add to basket')",
        "button:has-text('Add to cart')",
        "button:has-text('In den Warenkorb')",
        "button:has-text('Zum Warenkorb')",
        "a:has-text('In den Warenkorb')",
        "a:has-text('Add to basket')"
    ]


    for selector in cart_selectors:

        try:

            locator = page.locator(selector)

            if locator.count() > 0:

                for i in range(
                    min(locator.count(), 5)
                ):

                    button = locator.nth(i)

                    if await_like_is_visible(
                        button
                    ):

                        disabled = button.get_attribute(
                            "disabled"
                        )

                        aria_disabled = (
                            button.get_attribute(
                                "aria-disabled"
                            )
                        )

                        classes = (
                            button.get_attribute(
                                "class"
                            )
                            or ""
                        ).lower()


                        if (
                            disabled is None
                            and aria_disabled != "true"
                            and "disabled" not in classes
                        ):

                            return True, {
                                "title": title,
                                "price": price,
                                "url": url,
                                "shop": "Smyths"
                            }

        except Exception:
            pass


    # --------------------------------------------------
    # 4. Gesamtseite nach eindeutigen Online-Signalen
    # --------------------------------------------------

    try:

        body_text = page.locator(
            "body"
        ).inner_text().lower()

    except Exception:

        body_text = ""


    # Nur eindeutige Online-Verfügbarkeit

    online_available = [
        "online verfügbar",
        "online lieferbar",
        "online auf lager",
        "lieferbar nach hause"
    ]


    for phrase in online_available:

        if phrase in body_text:

            return True, {
                "title": title,
                "price": price,
                "url": url,
                "shop": "Smyths"
            }


    online_unavailable = [
        "online nicht verfügbar",
        "online nicht lieferbar",
        "online ausverkauft",
        "nicht verfügbar für lieferung",
        "out of stock for home delivery"
    ]


    for phrase in online_unavailable:

        if phrase in body_text:

            return False, {
                "title": title,
                "price": price,
                "url": url,
                "shop": "Smyths"
            }


    # --------------------------------------------------
    # Nichts Eindeutiges gefunden
    #
    # NIEMALS als "out" speichern.
    # --------------------------------------------------

    raise RuntimeError(
        "Smyths: Keine eindeutige Information "
        "zur Online-Verfügbarkeit gefunden."
    )


# --------------------------------------------------
# Hilfsfunktion für Playwright Locator
# --------------------------------------------------

def await_like_is_visible(locator):

    try:
        return locator.is_visible(
            timeout=2000
        )
    except Exception:
        return False


# --------------------------------------------------
# Einheitliche Prüfung
# --------------------------------------------------

def check_stock(url, browser_page=None):

    if is_smyths(url):

        if browser_page is None:
            raise RuntimeError(
                "Smyths benötigt einen Browser."
            )

        return check_smyths_with_browser(
            browser_page,
            url
        )

    return check_diecast_hunter(url)


# --------------------------------------------------
# Telegram-Befehle
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


# --------------------------------------------------
# Browser starten
#
# Nur wenn Smyths-URLs vorhanden sind.
# --------------------------------------------------

needs_browser = any(
    is_smyths(url)
    for url in urls
    if url
)


playwright = None
browser = None
page = None


if needs_browser:

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled"
        ]
    )

    page = browser.new_page(
        viewport={
            "width": 1366,
            "height": 900
        },
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        locale="de-CH",
        timezone_id="Europe/Zurich"
    )


try:

    # --------------------------------------------------
    # Telegram Updates verarbeiten
    # --------------------------------------------------

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


        # Nur eigener Chat

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

                    shop = (
                        "Smyths"
                        if is_smyths(url)
                        else "Diecast Hunter"
                    )

                    message_lines.append(
                        f"{i}. 🟢 [{shop}]\n{url}"
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
                "\n".join(
                    message_lines
                )
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


            # Nur /url1

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


            # Löschen

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


            urls[index] = new_url
            stocks[index] = "unknown"

            write_urls(urls)
            write_stocks(stocks)


            shop = (
                "Smyths"
                if is_smyths(new_url)
                else "Diecast Hunter"
            )


            send_telegram(
                f"✅ URL {index + 1} gespeichert.\n\n"
                f"🏪 Shop: {shop}\n"
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
                        url,
                        page
                    )


                    if in_stock:
                        stock_text = "🟢 VERFÜGBAR"
                    else:
                        stock_text = "🔴 NICHT VERFÜGBAR"


                    status_lines.append(
                        f"{i}. {stock_text}\n"
                        f"🏪 {product.get('shop', 'Unbekannt')}\n"
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
                "\n\n".join(
                    status_lines
                )
            )


    # --------------------------------------------------
    # Offset speichern
    # --------------------------------------------------

    write_file(
        OFFSET_FILE,
        str(offset)
    )


    # --------------------------------------------------
    # Pause
    # --------------------------------------------------

    if status == "paused":

        print(
            "Bestandscheck ist pausiert."
        )

        raise SystemExit


    # --------------------------------------------------
    # Normaler Bestandscheck
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
                url,
                page
            )


            old_stock = stocks[index]


            # --------------------------------------------------
            # Verfügbar
            # --------------------------------------------------

            if in_stock:

                new_stock = "in"


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

            # Bei Fehler alten Status behalten.
            # Dadurch wird ein technischer Fehler
            # niemals als "out" gespeichert.


    # --------------------------------------------------
    # Status speichern
    # --------------------------------------------------

    write_stocks(stocks)

    print(
        "Bestandsprüfung abgeschlossen."
    )


finally:

    # --------------------------------------------------
    # Browser sauber schließen
    # --------------------------------------------------

    if browser is not None:

        try:
            browser.close()
        except Exception:
            pass


    if playwright is not None:

        try:
            playwright.stop()
        except Exception:
            pass
