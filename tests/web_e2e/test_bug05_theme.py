"""Test BUG-05: Theme toggle behavior.

Sub-slice 5a — first click flips data-theme.
Sub-slice 5b — light theme changes the body background to a light value.
"""


def test_theme_toggle_first_click_flips_data_theme(browser, frontend_url):
    page = browser.new_page()
    try:
        # Login first
        page.goto(f"{frontend_url}/login", wait_until="networkidle")
        page.fill("input#lu", "davo")
        page.fill("input#lp", "davo")
        page.click("button[type=submit]")
        page.wait_for_url(f"{frontend_url}/", timeout=5000)

        # Clear any prior theme preference so we start from a known state.
        page.evaluate("localStorage.removeItem('tcm:theme')")

        # Reload to ensure clean state
        page.goto(f"{frontend_url}/", wait_until="networkidle")

        # Snapshot initial theme
        initial = page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert initial == "dark", f"expected initial data-theme=dark, got {initial!r}"

        # Click the theme toggle button once
        toggle = page.get_by_title("Switch to light")
        toggle.click()

        # Wait for the attribute to update
        page.wait_for_function(
            "document.documentElement.getAttribute('data-theme') === 'light'",
            timeout=2000,
        )
        after = page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert after == "light", f"expected data-theme=light after one click, got {after!r}"
    finally:
        page.close()


def test_light_theme_changes_body_background_to_light(browser, frontend_url):
    page = browser.new_page()
    try:
        page.goto(f"{frontend_url}/login", wait_until="networkidle")
        page.fill("input#lu", "davo")
        page.fill("input#lp", "davo")
        page.click("button[type=submit]")
        page.wait_for_url(f"{frontend_url}/", timeout=5000)

        page.evaluate("localStorage.removeItem('tcm:theme')")
        page.goto(f"{frontend_url}/", wait_until="networkidle")

        # Capture the --bg token under the dark theme
        dark_var = page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()"
        )
        # Toggle to light
        page.get_by_title("Switch to light").click()
        page.wait_for_function(
            "document.documentElement.getAttribute('data-theme') === 'light'",
            timeout=2000,
        )
        light_var = page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()"
        )

        # The two values must be different
        assert dark_var != light_var, (
            f"--bg did not change between themes (still {dark_var!r})"
        )
        # Both must be defined as oklch()
        assert "oklch" in light_var.lower(), (
            f"light --bg is not oklch: {light_var!r}"
        )
        # The L (lightness) component of light must be much higher than dark.
        # oklch() syntax is "oklch(L C H)" or "oklch(L% C H)" — extract L.
        import re
        def lightness_oklch(s):
            m = re.search(r"oklch\(\s*([\d.]+)%?\s+", s)
            if not m:
                return None
            v = float(m.group(1))
            return v if v <= 1 else v  # 0–100 if %, 0–1 if decimal

        dark_l = lightness_oklch(dark_var)
        light_l = lightness_oklch(light_var)
        assert dark_l is not None and light_l is not None, (
            f"could not parse oklch L from values: dark={dark_var!r}, light={light_var!r}"
        )
        assert light_l > 0.5, (
            f"light theme --bg lightness ({light_l}) should be > 0.5 (got {light_var!r})"
        )
        assert light_l > dark_l, (
            f"light theme lightness ({light_l}) should exceed dark ({dark_l})"
        )
    finally:
        page.close()