import re
import time
from playwright.sync_api import sync_playwright


WISHLIST_URL = (
    "https://www.smythstoys.com/ch/de-ch/"
    "wunschliste/0b76f8e4-0563-430b-9934-824cb14fcc5d"
)


print("=" * 70)
print("SMYTHS WUNSCHLISTE – LOKALER TEST")
print("=" * 70)
print()
print("Der Browser wird geöffnet.")
print()
print("Falls Smyths eine Anmeldung verlangt:")
print("Bitte ganz normal in deinem Browser anmelden.")
print()
print("Danach wird die Wunschliste untersucht.")
print()


with sync_playwright() as p:

    # --------------------------------------------------
    # Browser starten
    # --------------------------------------------------

    browser = p.chromium.launch(
        headless=False
    )

    context = browser.new_context(
        viewport={
            "width": 1440,
            "height": 1000
        },
        locale="de-CH",
        timezone_id="Europe/Zurich"
    )

    page = context.new_page()


    # --------------------------------------------------
    # Wunschliste öffnen
    # --------------------------------------------------

    print("Öffne Wunschliste...")

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

    except Exception as e:

        print(
            f"Fehler beim Öffnen: {e}"
        )


    # --------------------------------------------------
    # Zeit geben
    # --------------------------------------------------

    print()
    print("Warte 10 Sekunden...")

    time.sleep(10)


    # --------------------------------------------------
    # Aktuelle URL
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SEITE")
    print("=" * 70)

    print(
        f"URL: {page.url}"
    )

    try:

        print(
            f"Titel: {page.title()}"
        )

    except Exception:
        pass


    # --------------------------------------------------
    # Sichtbaren Text auslesen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SEITENTEXT")
    print("=" * 70)

    try:

        text = page.locator(
            "body"
        ).inner_text(
            timeout=10000
        )

        print(
            f"Textlänge: {len(text)}"
        )

        print()
        print(
            text[:20000]
        )

    except Exception as e:

        print(
            f"Text konnte nicht gelesen werden: {e}"
        )

        text = ""


    # --------------------------------------------------
    # Produktlinks suchen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("PRODUKTE")
    print("=" * 70)

    try:

        links = page.locator(
            "a"
        ).all()

        product_links = set()

        for link in links:

            try:

                href = link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                if "/p/" in href:

                    if href.startswith("/"):

                        href = (
                            "https://www.smythstoys.com"
                            + href
                        )

                    product_links.add(
                        href
                    )

            except Exception:
                continue


        if product_links:

            print(
                f"Gefundene Produkte: "
                f"{len(product_links)}"
            )

            for url in sorted(
                product_links
            ):

                print(
                    url
                )

        else:

            print(
                "Keine Produktlinks gefunden."
            )


    except Exception as e:

        print(
            f"Fehler beim Suchen der Produkte: {e}"
        )


    # --------------------------------------------------
    # HTML untersuchen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("BESTAND / VERFÜGBARKEIT")
    print("=" * 70)

    try:

        html = page.content().lower()

        keywords = [

            "verfügbar",
            "nicht verfügbar",
            "nicht vorrätig",
            "vorrätig",
            "lieferung",
            "online",
            "stock",
            "inventory",
            "available",
            "outofstock",
            "instock"

        ]

        found = []

        for keyword in keywords:

            if keyword in html:

                found.append(
                    keyword
                )

        if found:

            print(
                "Gefundene Begriffe:"
            )

            for keyword in found:

                print(
                    f"  ✅ {keyword}"
                )

        else:

            print(
                "Keine Bestandsbegriffe gefunden."
            )


    except Exception as e:

        print(
            f"HTML konnte nicht untersucht werden: {e}"
        )


    # --------------------------------------------------
    # Browser offen lassen
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("TEST FERTIG")
    print("=" * 70)

    print()
    print(
        "Der Browser bleibt geöffnet."
    )

    print(
        "Bitte kontrolliere die Wunschliste."
    )

    print()
    print(
        "Wenn alles sichtbar ist, kannst du "
        "dieses Fenster später schließen."
    )

    input(
        "\nENTER drücken zum Beenden..."
    )


    browser.close()
