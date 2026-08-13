"""Test BUG-06: Notifications rows must not advertise pointer cursor unless clickable.

Seam: rendered /notifications page. Rows without an analysis_id target should
not have cursor:pointer, because clicking them does nothing (router.push is
guarded by truthy check on analysis_id).
"""


def _seed_notification_without_analysis_id(backend_url):
    """Insert a notification with analysis_id=NULL directly via SQLite."""
    import sqlite3
    db_path = "/Users/davidnalbandyan/Desktop/Projects/trading-notifier/tcm.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "DELETE FROM notifications WHERE chart_name = 'TEST_NO_ANALYSIS'"
        )
        conn.execute(
            "INSERT INTO notifications (chart_name, timestamp, score, direction, status, caption, analysis_id) "
            "VALUES ('TEST_NO_ANALYSIS', '2026-08-07T00:00:00', 5.0, 'LONG', 'sent', 'No analysis target', NULL)"
        )
        conn.commit()
    finally:
        conn.close()


def test_non_clickable_row_does_not_have_pointer_cursor(browser, frontend_url):
    _seed_notification_without_analysis_id("http://localhost:8000")

    page = browser.new_page()
    try:
        page.goto(f"{frontend_url}/login", wait_until="networkidle")
        page.fill("input#lu", "davo")
        page.fill("input#lp", "davo")
        page.click("button[type=submit]")
        page.wait_for_url(f"{frontend_url}/", timeout=5000)
        page.goto(f"{frontend_url}/notifications", wait_until="networkidle")

        # Find the row whose caption we seeded.
        target = page.locator(".list-row").filter(has_text="TEST_NO_ANALYSIS")
        assert target.count() > 0, "seeded notification row not rendered"

        # Its computed cursor must NOT be 'pointer' (the bug was unconditional pointer).
        cursor = target.first.evaluate(
            "(el) => getComputedStyle(el).cursor"
        )
        assert cursor != "pointer", (
            f"row without analysis_id has cursor:pointer (misleading affordance): {cursor!r}"
        )
    finally:
        page.close()


def test_clickable_row_navigates_to_analysis(browser, frontend_url):
    # Insert an analysis + a notification with that analysis_id
    import sqlite3
    db_path = "/Users/davidnalbandyan/Desktop/Projects/trading-notifier/tcm.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM notifications WHERE chart_name = 'TEST_CLICK_NAV'")
        conn.execute("DELETE FROM analyses WHERE chart_name = 'TEST_CLICK_NAV'")
        conn.execute(
            "INSERT INTO analyses (chart_name, timestamp, score, direction, reason) "
            "VALUES ('TEST_CLICK_NAV', '2026-08-07T00:00:00', 7.5, 'LONG', 'click-nav test')"
        )
        aid = conn.execute(
            "SELECT id FROM analyses WHERE chart_name='TEST_CLICK_NAV' ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO notifications (chart_name, timestamp, score, direction, status, caption, analysis_id) "
            "VALUES ('TEST_CLICK_NAV', '2026-08-07T00:00:05', 7.5, 'LONG', 'sent', 'click-nav notification', ?)",
            (aid,),
        )
        conn.commit()
    finally:
        conn.close()

    page = browser.new_page()
    try:
        page.goto(f"{frontend_url}/login", wait_until="networkidle")
        page.fill("input#lu", "davo")
        page.fill("input#lp", "davo")
        page.click("button[type=submit]")
        page.wait_for_url(f"{frontend_url}/", timeout=5000)
        page.goto(f"{frontend_url}/notifications", wait_until="networkidle")

        target = page.locator(".list-row").filter(has_text="TEST_CLICK_NAV")
        assert target.count() > 0
        # Click the message area (not the delete button)
        target.first.locator(".col-msg").click()
        page.wait_for_url(lambda url: "/analysis/" in url, timeout=3000)
        assert "/analysis/" in page.url
    finally:
        page.close()