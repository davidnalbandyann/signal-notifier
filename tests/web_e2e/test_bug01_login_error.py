"""Test BUG-01: Login error message never displayed after wrong credentials.

Seam: rendered DOM at /login when POST /api/auth/login returns 401.
The frontend's `.error` block must contain the inline error message.
"""


def test_login_renders_error_message_for_wrong_credentials(browser, frontend_url):
    from playwright.sync_api import expect

    page = browser.new_page()
    try:
        page.goto(f"{frontend_url}/login", wait_until="networkidle")

        page.fill("input#lu", "wronguser")
        page.fill("input#lp", "wrongpass")

        page.click("button[type=submit]")

        # The .error block should appear with the inline error
        error_block = page.locator(".error")
        expect(error_block).to_be_visible(timeout=3000)
        expect(error_block).to_contain_text("Invalid credentials")

        # Should still be on /login (not redirected to /)
        assert "/login" in page.url
    finally:
        page.close()