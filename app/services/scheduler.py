import asyncio
import base64
import re
import structlog
import time
import yaml
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import Settings
from app.database import get_db
from app.models.schemas import URLConfig, ChartConfig
from app.state import get_paused, set_last_scan
from app.services.browser import BrowserService
from app.services.gemini import NvidiaService
from app.services.telegram import TelegramService

logger = structlog.get_logger(__name__)


class SchedulerService:
    def __init__(
        self,
        settings: Settings,
        browser: BrowserService,
        gemini: NvidiaService,
        telegram: TelegramService,
    ) -> None:
        self.settings = settings
        self.browser = browser
        self.gemini = gemini
        self.telegram = telegram
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        trigger = IntervalTrigger(seconds=self.settings.CHECK_INTERVAL_SECONDS)
        self._scheduler.add_job(
            self._analysis_cycle,
            trigger=trigger,
            id="analysis_cycle",
            replace_existing=True,
            misfire_grace_time=30,
        )
        self._scheduler.start()
        logger.info(
            "scheduler_started",
            interval_seconds=self.settings.CHECK_INTERVAL_SECONDS,
        )

    async def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    async def _analysis_cycle(self) -> None:
        if get_paused():
            logger.info("cycle_skipped_paused")
            return

        # Check if C++ engine bypass is enabled — skip AI analysis cycle
        db = get_db()
        bypass_row = db.execute(
            "SELECT value FROM settings WHERE key = ?", ("CPP_BYPASS_AI",)
        ).fetchone()
        cpp_bypass = bypass_row and bypass_row["value"].lower() in ("true", "1", "yes")
        if cpp_bypass:
            logger.info("cycle_skipped_cpp_bypass")
            set_last_scan()
            return

        charts = self._load_charts()
        if not charts:
            logger.warning("no_charts_configured")
            return

        logger.info("cycle_started", chart_count=len(charts))
        start_time = asyncio.get_event_loop().time()

        for chart in charts:
            try:
                await self._process_chart(chart)
            except Exception as e:
                logger.error(
                    "chart_processing_failed",
                    chart=chart.name,
                    error=str(e),
                )
            await asyncio.sleep(self.settings.AI_CALL_DELAY)

        set_last_scan()
        elapsed = asyncio.get_event_loop().time() - start_time
        logger.info("cycle_completed", duration_seconds=round(elapsed, 2))

    def _load_charts(self) -> list[ChartConfig]:
        urls_file = Path(self.settings.URLS_FILE)
        if not urls_file.exists():
            logger.error("urls_file_not_found", path=str(urls_file))
            return []

        try:
            data = yaml.safe_load(urls_file.read_text(encoding="utf-8"))
            config = URLConfig(**data)
            return config.charts
        except Exception as e:
            logger.error("urls_file_parse_error", error=str(e))
            return []

    async def _process_chart(self, chart: ChartConfig) -> None:
        logger.info("processing_chart", chart=chart.name)

        screenshot = await self.browser.capture(chart.name, chart.url)
        logger.info(
            "screenshot_captured",
            chart=chart.name,
            size_bytes=len(screenshot),
        )

        analysis = await self.gemini.analyze(screenshot)
        logger.info(
            "analysis_received",
            chart=chart.name,
            score=analysis.score,
            direction=analysis.direction.value,
        )

        now = datetime.now(timezone.utc).isoformat()

        db = get_db()
        row = db.execute("SELECT value FROM settings WHERE key = ?", ("NOTIFICATION_THRESHOLD",)).fetchone()
        threshold = self.settings.NOTIFICATION_THRESHOLD
        if row:
            try:
                threshold = float(row["value"])
            except (ValueError, TypeError):
                logger.warning("invalid_threshold_setting", value=row["value"])
        sent = analysis.score >= threshold and analysis.direction.value != "NEUTRAL"

        db = get_db()
        screenshot_filename = f"{chart.name.replace('/', '_')}_{int(time.time())}.png"
        screenshot_path = Path("data/screenshots") / screenshot_filename
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(screenshot)
        cur = db.execute(
            "INSERT INTO analyses (chart_name, timestamp, score, direction, reason, entry, stop_loss, take_profit, sent, screenshot, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                chart.name, now, analysis.score, analysis.direction.value,
                analysis.reason, analysis.entry, analysis.stop_loss,
                analysis.take_profit, int(sent), screenshot_filename,
                analysis.error,
            ),
        )
        analysis_id = cur.lastrowid

        if sent:
            timeframe = _extract_timeframe(chart.url)
            caption = await self.telegram.notify(chart.name, analysis, screenshot, timeframe=timeframe, analysis_id=analysis_id)
            db.execute(
                "INSERT INTO notifications (analysis_id, chart_name, timestamp, score, direction, status, caption) "
                "VALUES (?, ?, ?, ?, ?, 'sent', ?)",
                (analysis_id, chart.name, now, analysis.score, analysis.direction.value, caption),
            )
        else:
            logger.info(
                "threshold_not_met",
                chart=chart.name,
                score=analysis.score,
                threshold=threshold,
            )

        db.commit()


TV_INTERVAL_MAP = {
    "1": "1m", "5": "5m", "15": "15m", "30": "30m",
    "60": "1h", "120": "2h", "240": "4h",
    "1D": "1d", "1W": "1w", "1M": "1M",
}


def _extract_timeframe(url: str) -> str:
    m = re.search(r"[?&]interval=(\w+)", url)
    if m:
        raw = m.group(1)
        return TV_INTERVAL_MAP.get(raw, raw)
    return ""
