"""Test BUG-04: Engine start failure must surface an error toast.

Seam: click 'Start engine' on /engine with a 400 response from /api/cpp-engine/start.
The frontend must call toast.err(...) so the user sees feedback.
"""


def test_engine_start_failure_shows_error_toast(browser, frontend_url):
    from playwright.sync_api import expect

    page = browser.new_page()
    try:
        # Login first
        page.goto(f"{frontend_url}/login", wait_until="networkidle")
        page.fill("input#lu", "davo")
        page.fill("input#lp", "davo")
        page.click("button[type=submit]")
        page.wait_for_url(f"{frontend_url}/", timeout=5000)

        # Intercept the engine start endpoint and force a 400
        def handler(route):
            route.fulfill(
                status=400,
                content_type="application/json",
                body='{"detail":"sudo: a terminal is required to read the password"}',
            )
        page.route("**/api/cpp-engine/start", handler)

        # Go to engine page
        page.goto(f"{frontend_url}/engine", wait_until="networkidle")

        # Find and click the Start engine button (not the Stop variant)
        start_button = page.get_by_role("button", name="Start engine")
        expect(start_button).to_be_visible(timeout=5000)
        start_button.click()

        # The error toast must appear with the detail text
        toast = page.locator(".toast")
        expect(toast).to_be_visible(timeout=2000)
        expect(toast).to_contain_text("sudo")
    finally:
        page.close()