"""Test BUG-07: Admin table must not cause document-level horizontal scroll on tablet/mobile.

Seam: viewport resize to 768x1024 on /admin. The document must not overflow
horizontally — table-internal scroll is acceptable.
"""


def test_admin_table_no_document_overflow_at_768(browser, frontend_url):
    page = browser.new_page(viewport={"width": 768, "height": 1024})
    try:
        # Login
        page.goto(f"{frontend_url}/login", wait_until="networkidle")
        page.fill("input#lu", "davo")
        page.fill("input#lp", "davo")
        page.click("button[type=submit]")
        page.wait_for_url(f"{frontend_url}/", timeout=5000)

        # Go to admin page
        page.goto(f"{frontend_url}/admin", wait_until="networkidle")

        # Document must not horizontally overflow
        body_overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert body_overflow is False, (
            "document overflows horizontally at 768px viewport — table wrapper should constrain overflow"
        )
    finally:
        page.close()


def test_admin_table_no_document_overflow_at_390(browser, frontend_url):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    try:
        page.goto(f"{frontend_url}/login", wait_until="networkidle")
        page.fill("input#lu", "davo")
        page.fill("input#lp", "davo")
        page.click("button[type=submit]")
        page.wait_for_url(f"{frontend_url}/", timeout=5000)

        page.goto(f"{frontend_url}/admin", wait_until="networkidle")

        body_overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert body_overflow is False, (
            "document overflows horizontally at 390px viewport"
        )
    finally:
        page.close()