import os
import sys
import time
import subprocess
import requests
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = "/Users/davidnalbandyan/.gemini/antigravity-ide/brain/14b183b0-c186-403e-83a7-5804260f1ea8"

def wait_for_url(url, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    print("Starting backend and frontend servers...")

    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = "."
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    frontend_proc = subprocess.Popen(
        ["npx", "vite", "--host", "127.0.0.1", "--port", "5173"],
        cwd="frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        print("Waiting for backend (http://127.0.0.1:8000/health)...")
        if not wait_for_url("http://127.0.0.1:8000/health", timeout=15):
            print("Backend failed to start!")
            out, err = backend_proc.communicate(timeout=2)
            print("Backend log:", out.decode(), err.decode())
            sys.exit(1)

        print("Waiting for frontend (http://127.0.0.1:5173)...")
        if not wait_for_url("http://127.0.0.1:5173", timeout=20):
            print("Frontend failed to start!")
            out, err = frontend_proc.communicate(timeout=2)
            print("Frontend stdout:", out.decode())
            print("Frontend stderr:", err.decode())
            sys.exit(1)

        print("Servers ready! Running Playwright browser test...")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            # 1. Login
            page.goto("http://127.0.0.1:5173/login")
            page.wait_for_selector("input[type='text'], input[placeholder*='Username']")
            page.fill("input[type='text']", "davo")
            page.fill("input[type='password']", "davo")
            page.click("button[type='submit']")
            page.wait_for_url("http://127.0.0.1:5173/", timeout=10000)
            print("Successfully logged in!")

            # 2. Navigate to Admin panel
            page.goto("http://127.0.0.1:5173/admin")
            page.wait_for_selector(".admin-view")
            time.sleep(1)

            # Screenshot 1: Admin Panel Dashboard
            shot1 = os.path.join(ARTIFACT_DIR, "admin_panel_overview.png")
            page.screenshot(path=shot1)
            print(f"Saved screenshot: {shot1}")

            # 3. Test Tab Switching
            for tab_name in ["Analyses", "Notifications", "Settings", "Charts"]:
                page.click(f"button:has-text('{tab_name}')")
                time.sleep(0.5)
                print(f"Switched to model tab: {tab_name}")

            # Screenshot 2: Model tabs
            shot2 = os.path.join(ARTIFACT_DIR, "admin_model_tabs.png")
            page.screenshot(path=shot2)

            # 4. Create new Chart record
            page.click("button:has-text('New Chart')")
            page.wait_for_selector(".modal")
            page.fill("#field-name", "ADA/USDT")
            page.fill("#field-url", "https://tradingview.com/chart/ada")

            shot3 = os.path.join(ARTIFACT_DIR, "admin_create_modal.png")
            page.screenshot(path=shot3)
            print(f"Saved screenshot: {shot3}")

            page.click(".modal-actions button[type='submit']")
            time.sleep(1)
            print("Created new chart record: ADA/USDT")

            # Verify ADA/USDT appears in table
            page.wait_for_selector("text=ADA/USDT")
            print("Verified ADA/USDT record present in data table!")

            # 5. Edit Chart record
            row = page.locator("tr:has-text('ADA/USDT')")
            row.locator(".action-btn.edit").click()
            page.wait_for_selector(".modal")
            page.fill("#field-url", "https://tradingview.com/chart/ada-updated")
            page.click(".modal-actions button[type='submit']")
            time.sleep(1)
            print("Updated chart record URL!")

            # Verify updated URL
            page.wait_for_selector("text=https://tradingview.com/chart/ada-updated")
            print("Verified updated URL in data table!")

            # 6. Delete Chart record
            row = page.locator("tr:has-text('ADA/USDT')")
            page.on("dialog", lambda dialog: dialog.accept())
            row.locator(".action-btn.danger").click()
            time.sleep(1)
            print("Deleted test chart record!")

            shot4 = os.path.join(ARTIFACT_DIR, "admin_panel_final.png")
            page.screenshot(path=shot4)
            print(f"Saved screenshot: {shot4}")

            browser.close()
            print("PLAYWRIGHT E2E TEST PASSED SUCCESSFULLY!")

    finally:
        print("Stopping backend and frontend processes...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
