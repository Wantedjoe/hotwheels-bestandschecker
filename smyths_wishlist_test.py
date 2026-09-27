from playwright.sync_api import sync_playwright


WISHLIST_URL = (
    "https://www.smythstoys.com/ch/de-ch/"
    "wunschliste/0b76f8e4-0563-430b-9934-824cb14fcc5d"
)

SCREENSHOT_FILE = "smyths_wishlist.png"
HTML_FILE = "smyths_wishlist.html"


print("=" * 80)
print("SMYTHS WUNSCHLISTEN TEST")
print("=" * 80)
print()
print("Wunschliste:")
print(WISHLIST_URL)
print()


with sync_playwright() as p:

    # --------------------------------------------------
    # Chromium starten
    # --------------------------------------------------

    print("Starte Chromium...")

    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu"
        ]
    )

    context = browser.new_context(
        viewport={
            "width": 1440,
            "height": 1000
        },

        locale="de-CH",

        timezone_id="Europe/Zurich",

        java_script_enabled=True,

        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    )

    page = context.new_page()


    # --------------------------------------------------
    # Alle interessanten Requests sammeln
    # --------------------------------------------------

    requests_found = []

    responses_found = []


    def on_request(request):

        url = request.url.lower()

        interesting_words = [
            "wishlist",
            "wunschliste",
            "product",
            "inventory",
            "stock",
            "availability",
            "api",
            "basket",
            "cart"
        ]

        if any(
            word in url
            for word in interesting_words
        ):

            requests_found.append(
                (
                    request.method,
                    request.url
                )
            )


    def on_response(response):

        url = response.url.lower()

        interesting_words = [
            "wishlist",
            "wunschliste",
            "product",
            "inventory",
            "stock",
            "availability",
            "api",
            "basket",
            "cart"
        ]

        if any(
            word in url
            for word in interesting_words
        ):

            responses_found.append(
                (
                    response.status,
                    response.url
                )
            )


    page.on(
        "request",
        on_request
    )

    page.on(
        "response",
        on_response
    )


    # --------------------------------------------------
    # Wunschliste öffnen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("1. WUNSCHLISTE ÖFFNEN")
    print("=" * 80)

    try:

        response = page.goto(
            WISHLIST_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        if response:

            print(
                f"HTTP Status: {response.status}"
            )

            print(
                f"Antwort-URL: {response.url}"
            )

    except Exception as e:

        print(
            "Fehler beim Öffnen:"
        )

        print(e)


    # --------------------------------------------------
    # Auf JavaScript / dynamische Inhalte warten
    # --------------------------------------------------

    print()
    print("Warte auf dynamische Inhalte...")

    try:

        page.wait_for_load_state(
            "load",
            timeout=30000
        )

    except Exception:

        print(
            "load-State nicht erreicht."
        )


    try:

        page.wait_for_load_state(
            "networkidle",
            timeout=30000
        )

    except Exception:

        print(
            "networkidle nicht erreicht."
        )


    # Extra Zeit für Smyths

    page.wait_for_timeout(
        10000
    )


    # --------------------------------------------------
    # Basisinformationen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("2. SEITENINFORMATIONEN")
    print("=" * 80)

    print(
        f"Finale URL: {page.url}"
    )


    try:

        print(
            f"Titel: {page.title()}"
        )

    except Exception as e:

        print(
            f"Titel konnte nicht gelesen werden: {e}"
        )


    # --------------------------------------------------
    # Sichtbaren Text lesen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("3. SICHTBARER TEXT")
    print("=" * 80)


    try:

        body_text = page.locator(
            "body"
        ).inner_text(
            timeout=10000
        )

    except Exception as e:

        print(
            f"Fehler beim Auslesen: {e}"
        )

        body_text = ""


    print(
        f"Textlänge: {len(body_text)} Zeichen"
    )


    if body_text.strip():

        print()
        print(
            body_text[:10000]
        )

    else:

        print(
            "❌ Kein sichtbarer Text."
        )


    # --------------------------------------------------
    # HTML speichern
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("4. HTML")
    print("=" * 80)


    try:

        html = page.content()

        with open(
            HTML_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(html)

        print(
            f"HTML gespeichert: {HTML_FILE}"
        )

        print(
            f"HTML-Länge: {len(html)} Zeichen"
        )

    except Exception as e:

        print(
            f"HTML konnte nicht gespeichert werden: {e}"
        )

        html = ""


    # --------------------------------------------------
    # Begriffe suchen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("5. WICHTIGE BEGRIFFE")
    print("=" * 80)


    combined = (
        body_text + "\n" + html
    ).lower()


    terms = [

        "wunschliste",

        "wishlist",

        "wishlistbasket",

        "produkt",

        "products",

        "productid",

        "productcode",

        "lieferung",

        "verfügbar",

        "nicht verfügbar",

        "nicht vorrätig",

        "vorrätig",

        "warenkorb",

        "stock",

        "inventory",

        "availability",

        "available",

        "outofstock",

        "instock",

        "incap",

        "reese84",

        "cloudflare",

        "captcha",

        "access denied"
    ]


    for term in terms:

        if term.lower() in combined:

            print(
                f"✅ {term}"
            )

        else:

            print(
                f"❌ {term}"
            )


    # --------------------------------------------------
    # Produkt-Links aus HTML extrahieren
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("6. PRODUKT-LINKS")
    print("=" * 80)


    import re


    product_links = set()


    pattern = re.compile(
        r'https?://[^"\']+',
        re.IGNORECASE
    )


    for link in pattern.findall(html):

        if "/p/" in link:

            # HTML-Escapes / störende Zeichen entfernen

            clean = link.replace(
                "&amp;",
                "&"
            )

            clean = clean.rstrip(
                ".,);"
            )

            product_links.add(
                clean
            )


    if product_links:

        print(
            f"Gefundene Produkt-Links: "
            f"{len(product_links)}"
        )

        for link in sorted(
            product_links
        ):

            print(
                link[:1000]
            )

    else:

        print(
            "❌ Keine /p/-Produktlinks gefunden."
        )


    # --------------------------------------------------
    # Produkt-IDs im HTML suchen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("7. MÖGLICHE PRODUKT-IDS")
    print("=" * 80)


    product_ids = set()


    patterns = [

        r'/p/(\d+)',

        r'"productId"\s*:\s*"([^"]+)"',

        r'"productId"\s*:\s*(\d+)',

        r'"productCode"\s*:\s*"([^"]+)"',

        r'"productCode"\s*:\s*(\d+)',

        r'"sku"\s*:\s*"([^"]+)"'

    ]


    for pattern in patterns:

        try:

            matches = re.findall(
                pattern,
                html,
                flags=re.IGNORECASE
            )

            for match in matches:

                product_ids.add(
                    str(match)
                )

        except Exception:
            pass


    if product_ids:

        for product_id in sorted(
            product_ids
        ):

            print(
                f"→ {product_id}"
            )

    else:

        print(
            "❌ Keine offensichtlichen "
            "Produkt-IDs gefunden."
        )


    # --------------------------------------------------
    # Requests
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("8. INTERESSANTE REQUESTS")
    print("=" * 80)


    if requests_found:

        for method, url in requests_found:

            print(
                f"{method} | {url}"
            )

    else:

        print(
            "Keine interessanten Requests gefunden."
        )


    # --------------------------------------------------
    # Responses
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("9. INTERESSANTE RESPONSES")
    print("=" * 80)


    if responses_found:

        for status_code, url in responses_found:

            print(
                f"{status_code} | {url}"
            )

    else:

        print(
            "Keine interessanten Responses gefunden."
        )


    # --------------------------------------------------
    # Cookies
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("10. COOKIES")
    print("=" * 80)


    try:

        cookies = context.cookies()

        print(
            f"Anzahl Cookies: {len(cookies)}"
        )

        for cookie in cookies:

            name = cookie.get(
                "name",
                ""
            )

            # Werte NICHT ausgeben.
            # Wir wollen keine Session-Daten
            # im GitHub-Log haben.

            if any(
                word in name.lower()
                for word in [
                    "wishlist",
                    "session",
                    "smyth",
                    "incap",
                    "reese"
                ]
            ):

                print(
                    f"Cookie gefunden: {name}"
                )

    except Exception as e:

        print(
            f"Cookie-Test fehlgeschlagen: {e}"
        )


    # --------------------------------------------------
    # Screenshot
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("11. SCREENSHOT")
    print("=" * 80)


    try:

        page.screenshot(
            path=SCREENSHOT_FILE,
            full_page=True
        )

        print(
            f"Screenshot gespeichert: "
            f"{SCREENSHOT_FILE}"
        )

    except Exception as e:

        print(
            f"Screenshot fehlgeschlagen: {e}"
        )


    # --------------------------------------------------
    # Abschluss
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("TEST ABGESCHLOSSEN")
    print("=" * 80)


    browser.close()
