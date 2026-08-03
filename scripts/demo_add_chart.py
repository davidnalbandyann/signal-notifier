import os
import sys
import time
import sqlite3
import subprocess
import requests
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = "/Users/davidnalbandyan/.gemini/antigravity-ide/brain/14b183b0-c186-403e-83a7-5804260f1ea8"
DB_PATH = "/Users/davidnalbandyan/Desktop/Projects/trading-notifier/tcm.db"

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
    print("Starting backend and frontend servers for Playwright Chart CRUD test...")

    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = "."
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    frontend_proc = subprocess.Popen(
        "npx vite --host 127.0.0.1 --port 5173",
        cwd="frontend",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        print("Waiting for backend (http://127.0.0.1:8000/health)...")
        if not wait_for_url("http://127.0.0.1:8000/health", timeout=15):
            print("Backend failed to start!")
            sys.exit(1)

        print("Waiting for frontend (http://127.0.0.1:5173)...")
        if not wait_for_url("http://127.0.0.1:5173", timeout=20):
            print("Frontend failed to start!")
            sys.exit(1)

        print("Servers ready! Launching Playwright browser test...")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()

            # Step 1: Open Login
            page.goto("http://127.0.0.1:5173/login")
            page.wait_for_selector("input[type='text']")
            page.fill("input[type='text']", "davo")
            page.fill("input[type='password']", "davo")
            page.click("button[type='submit']")
            page.wait_for_url("http://127.0.0.1:5173/", timeout=10000)
            print("Logged in successfully!")

            # Step 2: Navigate to /admin
            page.goto("http://127.0.0.1:5173/admin")
            page.wait_for_selector(".admin-view")
            time.sleep(1)

            # Step 3: Open New Chart Modal
            print("3. Clicking 'New Chart' button...")
            btn = page.locator(".header-actions button:has-text('New Chart')")
            btn.click()
            page.wait_for_selector("#field-name", timeout=10000)

            # Fill form
            page.fill("#field-name", "LINK/USDT")
            page.fill("#field-url", "https://www.tradingview.com/chart/?symbol=BINANCE:LINKUSDT")

            print("Submitting modal form for LINK/USDT...")
            save_btn = page.locator(".modal-actions button:has-text('Save Record')")
            save_btn.click()
            time.sleep(2)

            page.screenshot(path=os.path.join(ARTIFACT_DIR, "04_chart_added.png"))

            # Step 4: Verify LINK/USDT in data table
            page.wait_for_selector("text=LINK/USDT", timeout=10000)
            print("Chart LINK/USDT successfully added and displayed in data table!")

            # Step 5: Edit Chart record
            print("5. Editing LINK/USDT record...")
            row = page.locator("tr:has-text('LINK/USDT')")
            row.locator(".action-btn.edit").click()
            page.wait_for_selector("#field-url", timeout=10000)

            # Change URL
            page.fill("#field-url", "https://www.tradingview.com/chart/?symbol=BINANCE:LINKUSDT_UPDATED")
            page.locator(".modal-actions button:has-text('Save Record')").click()
            time.sleep(2)

            # Verify updated URL
            page.wait_for_selector("text=https://www.tradingview.com/chart/?symbol=BINANCE:LINKUSDT_UPDATED", timeout=10000)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "05_chart_edited.png"))
            print("Updated chart URL verified in data table!")

            browser.close()

        # Step 6: Verify directly in SQLite Database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, name, url, enabled FROM charts WHERE name = 'LINK/USDT'")
        row = cur.fetchone()
        conn.close()

        if row:
            print(f"SQLite DB Verification PASSED: Found record in tcm.db -> ID={row[0]}, Name='{row[1]}', URL='{row[2]}', Enabled={row[3]}")
        else:
            print("ERROR: Record not found in SQLite tcm.db!")
            sys.exit(1)

        print("ALL PLAYWRIGHT CRUD VERIFICATIONS PASSED SUCCESSFULLY!")

    finally:
        print("Stopping backend and frontend processes...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
