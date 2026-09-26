from playwright.sync_api import sync_playwright
import re


URL = "https://www.smythstoys.com/ch/de-ch/spielzeug/action-spielzeug/spielzeugautos-und-spielsets/hot-wheels/hot-wheels-premium-team-transport-auto-porsche-911-gt3-r-992-und-fleet-flyer-2er-set/p/222278095"


print("=" * 70)
print("SMYTHS TEST")
print("=" * 70)
print()
print(f"URL:")
print(URL)
print()


with sync_playwright() as p:

    print("Starte Chromium...")

    browser = p.chromium.launch(
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


    print("Öffne Smyths-Seite...")

    try:

        response = page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        if response:
            print(
                f"HTTP Status: {response.status}"
            )

    except Exception as e:

        print()
        print("FEHLER beim Laden:")
        print(e)


    print()
    print("Warte auf dynamische Inhalte...")

    try:

        page.wait_for_load_state(
            "networkidle",
            timeout=20000
        )

    except Exception:

        print(
            "NetworkIdle wurde nicht erreicht "
            "(kann bei Smyths normal sein)."
        )


    page.wait_for_timeout(5000)


    # --------------------------------------------------
    # Seitentitel
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SEITENTITEL")
    print("=" * 70)

    try:

        print(
            page.title()
        )

    except Exception as e:

        print(
            f"Fehler: {e}"
        )


    # --------------------------------------------------
    # URL nach dem Laden
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("AKTUELLE URL")
    print("=" * 70)

    print(
        page.url
    )


    # --------------------------------------------------
    # Gesamten sichtbaren Text holen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SEITENTEXT WIRD AUSGELESEN")
    print("=" * 70)

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
        f"Gesamtlänge des Seitentextes: "
        f"{len(body_text)} Zeichen"
    )


    # --------------------------------------------------
    # Nach interessanten Begriffen suchen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("GEFUNDENE BEGRIFFE")
    print("=" * 70)


    search_terms = [
        "Lieferung",
        "nicht vorrätig",
        "nicht verfügbar",
        "verfügbar",
        "lieferbar",
        "ausverkauft",
        "Warenkorb",
        "Kaufen",
        "Nach Hause",
        "Online",
        "Home Delivery",
        "In Stock",
        "Out of Stock",
        "Add to basket",
        "Add to cart"
    ]


    body_lower = body_text.lower()


    found_terms = []


    for term in search_terms:

        if term.lower() in body_lower:

            found_terms.append(term)

            print(
                f"✅ {term}"
            )

        else:

            print(
                f"❌ {term}"
            )


    # --------------------------------------------------
    # Textstellen rund um "Lieferung"
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("TEXTSTELLEN RUND UM 'LIEFERUNG'")
    print("=" * 70)


    lines = body_text.splitlines()


    found_delivery = False


    for index, line in enumerate(lines):

        if "liefer" in line.lower():

            found_delivery = True

            print()
            print(
                f"--- Zeile {index + 1} ---"
            )


            start = max(
                0,
                index - 4
            )

            end = min(
                len(lines),
                index + 5
            )


            for nearby_line in lines[start:end]:

                clean_line = nearby_line.strip()

                if clean_line:

                    print(
                        clean_line
                    )


    if not found_delivery:

        print(
            "❌ Kein Text mit 'Liefer...' gefunden."
        )


    # --------------------------------------------------
    # Textstellen rund um "vorrätig"
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("TEXTSTELLEN RUND UM 'VORRÄTIG'")
    print("=" * 70)


    found_stock = False


    for index, line in enumerate(lines):

        if "vorrätig" in line.lower():

            found_stock = True

            print()
            print(
                f"--- Zeile {index + 1} ---"
            )


            start = max(
                0,
                index - 4
            )

            end = min(
                len(lines),
                index + 5
            )


            for nearby_line in lines[start:end]:

                clean_line = nearby_line.strip()

                if clean_line:

                    print(
                        clean_line
                    )


    if not found_stock:

        print(
            "❌ Kein Text mit 'vorrätig' gefunden."
        )


    # --------------------------------------------------
    # Mögliche Buttons untersuchen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("BUTTONS")
    print("=" * 70)


    try:

        buttons = page.locator(
            "button"
        )

        count = buttons.count()

        print(
            f"Anzahl Buttons: {count}"
        )


        for i in range(
            min(count, 50)
        ):

            button = buttons.nth(i)

            try:

                text = button.inner_text(
                    timeout=1000
                ).strip()

            except Exception:

                text = ""


            try:

                disabled = button.get_attribute(
                    "disabled"
                )

            except Exception:

                disabled = None


            if text:

                print(
                    f"{i + 1}. "
                    f"{text[:200]} "
                    f"(disabled={disabled})"
                )


    except Exception as e:

        print(
            f"Button-Test fehlgeschlagen: {e}"
        )


    # --------------------------------------------------
    # HTML nach relevanten Begriffen durchsuchen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("HTML-SUCHE")
    print("=" * 70)


    try:

        html = page.content()

        html_lower = html.lower()


        html_terms = [
            "stockstatus",
            "stockstatuscode",
            "deliverytype",
            "homedelivery",
            "product-inventory",
            "productinventory",
            "instock",
            "outofstock",
            "green-check"
        ]


        for term in html_terms:

            if term.lower() in html_lower:

                print(
                    f"✅ HTML enthält: {term}"
                )

            else:

                print(
                    f"❌ HTML enthält NICHT: {term}"
                )


    except Exception as e:

        print(
            f"HTML-Test fehlgeschlagen: {e}"
        )


    # --------------------------------------------------
    # Ergebnis zusammenfassen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("ZUSAMMENFASSUNG")
    print("=" * 70)


    if found_terms:

        print()
        print(
            "Gefundene relevante Begriffe:"
        )

        for term in found_terms:

            print(
                f" - {term}"
            )

    else:

        print()
        print(
            "Keine der gesuchten "
            "Verfügbarkeitsformulierungen gefunden."
        )


    print()
    print("=" * 70)
    print("TEST ABGESCHLOSSEN")
    print("=" * 70)


    browser.close()
