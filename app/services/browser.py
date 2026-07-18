import asyncio
import structlog
from pathlib import Path

from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page

from app.config.settings import Settings

logger = structlog.get_logger(__name__)


class BrowserService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._persistent_context: BrowserContext | None = None
        self._persistent_dir: str | None = (
            settings.BROWSER_USER_DATA_DIR.strip() or None
        )

    async def start(self) -> None:
        self._playwright = await async_playwright().start()

        if self._persistent_dir:
            dir_path = Path(self._persistent_dir)
            dir_path.mkdir(parents=True, exist_ok=True)
            self._persistent_context = (
                await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(dir_path),
                    headless=self.settings.HEADLESS,
                    viewport={
                        "width": self.settings.BROWSER_VIEWPORT_WIDTH,
                        "height": self.settings.BROWSER_VIEWPORT_HEIGHT,
                    },
                )
            )
            logger.info("browser_started_persistent", dir=self._persistent_dir)
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=self.settings.HEADLESS,
            )
            logger.info("browser_started", headless=self.settings.HEADLESS)

    async def capture(self, name: str, url: str) -> bytes:
        started = self._browser is not None or self._persistent_context is not None
        if not started:
            raise RuntimeError("Browser not started. Call start() first.")

        last_exception: Exception | None = None
        for attempt in range(1, self.settings.BROWSER_RETRY_COUNT + 2):
            try:
                return await self._capture_once(url)
            except Exception as e:
                last_exception = e
                logger.warning(
                    "screenshot_failed",
                    chart=name,
                    attempt=attempt,
                    error=str(e),
                )
                if attempt <= self.settings.BROWSER_RETRY_COUNT:
                    await asyncio.sleep(self.settings.BROWSER_RETRY_DELAY)

        raise RuntimeError(
            f"Failed to capture screenshot for {name} after "
            f"{self.settings.BROWSER_RETRY_COUNT + 1} attempts: {last_exception}"
        )

    async def _capture_once(self, url: str) -> bytes:
        context: BrowserContext | None = None
        if self._persistent_context:
            page: Page = await self._persistent_context.new_page()
        else:
            context = await self._browser.new_context(
                viewport={
                    "width": self.settings.BROWSER_VIEWPORT_WIDTH,
                    "height": self.settings.BROWSER_VIEWPORT_HEIGHT,
                },
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(self.settings.PLAYWRIGHT_WAIT_TIME)
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            return screenshot_bytes
        finally:
            await page.close()
            if context:
                await context.close()

    async def stop(self) -> None:
        if self._persistent_context:
            await self._persistent_context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("browser_stopped")
