import json
import re
from playwright.sync_api import sync_playwright


PRODUCT_URL = (
    "https://www.smythstoys.com/ch/de-ch/"
    "spielzeug/action-spielzeug/"
    "spielzeugautos-und-spielsets/hot-wheels/"
    "hot-wheels-premium-team-transport-auto-porsche-911-gt3-r-992-und-fleet-flyer-2er-set/"
    "p/222278095"
)

PRODUCT_ID = "222278095"


print("=" * 80)
print("SMYTHS INVENTORY API TEST")
print("=" * 80)
print()
print(f"Produkt-ID: {PRODUCT_ID}")
print(f"Produkt-URL: {PRODUCT_URL}")
print()


with sync_playwright() as p:

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
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    )

    page = context.new_page()

    # --------------------------------------------------
    # Smyths-Seite öffnen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("1. SMYTHS-SEITE ÖFFNEN")
    print("=" * 80)

    try:

        response = page.goto(
            PRODUCT_URL,
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
            f"Fehler beim Öffnen: {e}"
        )

    print()
    print("Warte auf Smyths-Session...")

    page.wait_for_timeout(8000)

    print(
        f"Finale URL: {page.url}"
    )

    try:

        print(
            f"Titel: {page.title()}"
        )

    except Exception:
        pass


    # --------------------------------------------------
    # JavaScript-Fetch innerhalb der Smyths-Seite
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("2. PRODUCT-INVENTORY TEST")
    print("=" * 80)

    result = page.evaluate(
        """
        async (productId) => {

            const candidates = [

                `/product-inventory?productCode=${productId}`,

                `/product-inventory/${productId}`,

                `/product-inventory?productId=${productId}`,

                `/api/product-inventory?productCode=${productId}`,

                `/api/product-inventory/${productId}`

            ];

            const results = [];

            for (const url of candidates) {

                try {

                    const response = await fetch(
                        url,
                        {
                            method: "GET",
                            credentials: "include",
                            headers: {
                                "Accept": "application/json, text/plain, */*"
                            }
                        }
                    );

                    const text = await response.text();

                    results.push({
                        url: url,
                        status: response.status,
                        contentType:
                            response.headers.get(
                                "content-type"
                            ),
                        body: text.substring(0, 5000)
                    });

                } catch (error) {

                    results.push({
                        url: url,
                        error: String(error)
                    });
                }
            }

            return results;
        }
        """,
        PRODUCT_ID
    )


    print()

    for item in result:

        print("-" * 80)

        print(
            f"URL: {item.get('url')}"
        )

        if "error" in item:

            print(
                f"ERROR: {item['error']}"
            )

            continue

        print(
            f"HTTP Status: {item.get('status')}"
        )

        print(
            f"Content-Type: {item.get('contentType')}"
        )

        body = item.get(
            "body",
            ""
        )

        print()
        print(
            "Antwort:"
        )

        print(
            body
        )


    # --------------------------------------------------
    # Automatisch interessante Antworten markieren
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("3. AUSWERTUNG")
    print("=" * 80)

    interesting = []

    for item in result:

        body = item.get(
            "body",
            ""
        )

        body_lower = body.lower()

        if any(
            word in body_lower
            for word in [
                "stock",
                "inventory",
                "available",
                "availability",
                "delivery",
                "quantity",
                "online"
            ]
        ):

            interesting.append(item)


    if interesting:

        print(
            f"✅ {len(interesting)} interessante "
            "Antwort(en) gefunden."
        )

        for item in interesting:

            print()
            print(
                f"→ {item.get('url')}"
            )

    else:

        print(
            "❌ Keine Antwort mit offensichtlichen "
            "Bestandsinformationen gefunden."
        )


    # --------------------------------------------------
    # Cookies anzeigen
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("4. COOKIES")
    print("=" * 80)

    try:

        cookies = context.cookies()

        print(
            f"Cookies: {len(cookies)}"
        )

        for cookie in cookies:

            name = cookie.get(
                "name",
                ""
            )

            if any(
                word in name.lower()
                for word in [
                    "imperva",
                    "incap",
                    "reese",
                    "session",
                    "smyth"
                ]
            ):

                print(
                    f"{name} = "
                    f"{str(cookie.get('value', ''))[:120]}"
                )

    except Exception as e:

        print(
            f"Cookie-Test fehlgeschlagen: {e}"
        )


    # --------------------------------------------------
    # Ende
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("TEST ABGESCHLOSSEN")
    print("=" * 80)

    browser.close()
