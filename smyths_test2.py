import os
import re
from playwright.sync_api import sync_playwright


URL = "https://www.smythstoys.com/ch/de-ch/spielzeug/action-spielzeug/spielzeugautos-und-spielsets/hot-wheels/hot-wheels-premium-team-transport-auto-porsche-911-gt3-r-992-und-fleet-flyer-2er-set/p/222278095"

SCREENSHOT_FILE = "smyths_page.png"
HTML_FILE = "smyths_page.html"


print("=" * 80)
print("SMYTHS DIAGNOSE TEST 2")
print("=" * 80)
print()
print("URL:")
print(URL)
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

        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),

        locale="de-CH",

        timezone_id="Europe/Zurich",

        color_scheme="light",

        java_script_enabled=True,

        ignore_https_errors=False
    )


    page = context.new_page()


    # --------------------------------------------------
    # Requests protokollieren
    # --------------------------------------------------

    request_count = 0
    response_count = 0


    interesting_requests = []


    def on_request(request):

        nonlocal_request_count = None

        global request_count

        request_count += 1

        url = request.url.lower()


        interesting_words = [
            "inventory",
            "stock",
            "product",
            "availability",
            "delivery",
            "basket",
            "cart",
            "api"
        ]


        if any(
            word in url
            for word in interesting_words
        ):

            interesting_requests.append(
                (
                    "REQUEST",
                    request.method,
                    request.url
                )
            )


    def on_response(response):

        global response_count

        response_count += 1

        url = response.url.lower()


        interesting_words = [
            "inventory",
            "stock",
            "product",
            "availability",
            "delivery",
            "basket",
            "cart",
            "api"
        ]


        if any(
            word in url
            for word in interesting_words
        ):

            interesting_requests.append(
                (
                    "RESPONSE",
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
    # Navigation protokollieren
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("SEITE ÖFFNEN")
    print("=" * 80)


    try:

        response = page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )


        if response:

            print(
                f"Erste HTTP-Antwort: "
                f"{response.status}"
            )

            print(
                f"Antwort-URL: "
                f"{response.url}"
            )


    except Exception as e:

        print(
            "Fehler bei page.goto():"
        )

        print(e)


    # --------------------------------------------------
    # Warten
    # --------------------------------------------------

    print()
    print("Warte auf JavaScript / dynamische Inhalte...")


    try:

        page.wait_for_load_state(
            "load",
            timeout=30000
        )

    except Exception as e:

        print(
            f"load-State nicht erreicht: {e}"
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


    # Noch etwas Zeit für nachgeladene Inhalte

    page.wait_for_timeout(
        10000
    )


    # --------------------------------------------------
    # Basisinformationen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("BASISINFORMATIONEN")
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


    print(
        f"Requests insgesamt: {request_count}"
    )

    print(
        f"Responses insgesamt: {response_count}"
    )


    # --------------------------------------------------
    # Screenshot
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("SCREENSHOT")
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
    # HTML speichern
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("HTML")
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
    # Sichtbaren Text auslesen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("SICHTBARER SEITENTEXT")
    print("=" * 80)


    try:

        body_text = page.locator(
            "body"
        ).inner_text(
            timeout=10000
        )


        print(
            f"Textlänge: {len(body_text)} Zeichen"
        )


        if body_text.strip():

            print()
            print(
                body_text[:5000]
            )

        else:

            print(
                "❌ Kein sichtbarer Seitentext."
            )


    except Exception as e:

        print(
            f"Seitentext konnte nicht gelesen werden: {e}"
        )

        body_text = ""


    # --------------------------------------------------
    # Begriffe suchen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("BEGRIFFSSUCHE")
    print("=" * 80)


    combined_text = (
        body_text + "\n" + html
    ).lower()


    search_terms = [

        "lieferung",

        "nicht vorrätig",

        "nicht verfügbar",

        "verfügbar",

        "lieferbar",

        "ausverkauft",

        "warenkorb",

        "kaufen",

        "nach hause",

        "online",

        "home delivery",

        "in stock",

        "out of stock",

        "stockstatus",

        "stockstatuscode",

        "deliverytype",

        "homedelivery",

        "product-inventory",

        "productinventory",

        "inventory",

        "availability",

        "green-check",

        "cloudflare",

        "imperva",

        "access denied",

        "captcha",

        "robot",

        "bot"
    ]


    for term in search_terms:

        if term.lower() in combined_text:

            print(
                f"✅ {term}"
            )

        else:

            print(
                f"❌ {term}"
            )


    # --------------------------------------------------
    # Interessante Requests
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("INTERESSANTE REQUESTS / RESPONSES")
    print("=" * 80)


    if interesting_requests:

        for item in interesting_requests:

            print(
                f"{item[0]} | "
                f"{item[1]} | "
                f"{item[2]}"
            )

    else:

        print(
            "❌ Keine relevanten Requests gefunden."
        )


    # --------------------------------------------------
    # Alle Links mit Inventory/Stock/etc.
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("INTERESSANTE LINKS IM HTML")
    print("=" * 80)


    pattern = re.compile(
        r'https?://[^"\']+',
        re.IGNORECASE
    )


    try:

        links = pattern.findall(
            html
        )


        found_links = set()


        for link in links:

            link_lower = link.lower()


            if any(
                word in link_lower
                for word in [
                    "inventory",
                    "stock",
                    "availability",
                    "product"
                ]
            ):

                clean_link = link[:1000]

                if clean_link not in found_links:

                    found_links.add(
                        clean_link
                    )

                    print(
                        clean_link
                    )


        if not found_links:

            print(
                "Keine passenden URLs im HTML gefunden."
            )


    except Exception as e:

        print(
            f"Link-Suche fehlgeschlagen: {e}"
        )


    # --------------------------------------------------
    # Cookies
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("COOKIES")
    print("=" * 80)


    try:

        cookies = context.cookies()


        print(
            f"Anzahl Cookies: {len(cookies)}"
        )


        for cookie in cookies:

            print(
                f"{cookie.get('name')} "
                f"= "
                f"{str(cookie.get('value'))[:100]}"
            )


    except Exception as e:

        print(
            f"Cookies konnten nicht gelesen werden: {e}"
        )


    # --------------------------------------------------
    # Local Storage / Session Storage
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("BROWSER STORAGE")
    print("=" * 80)


    try:

        storage = page.evaluate(
            """
            () => ({
                localStorage: Object.keys(localStorage),
                sessionStorage: Object.keys(sessionStorage)
            })
            """
        )


        print(
            "LocalStorage:"
        )

        for key in storage["localStorage"]:

            print(
                f"  {key}"
            )


        print(
            "SessionStorage:"
        )

        for key in storage["sessionStorage"]:

            print(
                f"  {key}"
            )


    except Exception as e:

        print(
            f"Storage konnte nicht gelesen werden: {e}"
        )


    # --------------------------------------------------
    # Abschluss
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("TEST ABGESCHLOSSEN")
    print("=" * 80)

    print()
    print(
        "Die Dateien"
    )

    print(
        f"  {SCREENSHOT_FILE}"
    )

    print(
        f"  {HTML_FILE}"
    )

    print(
        "wurden für die weitere Analyse erzeugt."
    )


    browser.close()
