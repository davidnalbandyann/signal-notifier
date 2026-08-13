import asyncio
import time
import structlog
from datetime import datetime, timezone, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import Settings
from app.database import get_db
from app.state import get_paused, set_last_scan
from app.services.ai import AIService
from app.services.browser import BrowserService
from app.services.telegram import TelegramService

logger = structlog.get_logger(__name__)

class SchedulerService:
    def __init__(
        self,
        settings: Settings,
        browser: BrowserService,
        ai: AIService,
        telegram: TelegramService,
    ) -> None:
        self.settings = settings
        self.browser = browser
        self.ai = ai
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

        db = get_db()
        # Fetch enabled ai_only active strategies
        rows = db.execute(
            "SELECT * FROM active_strategies WHERE enabled = 1 AND mode = 'ai_only' ORDER BY id ASC"
        ).fetchall()
        
        if not rows:
            logger.info("cycle_skipped_no_ai_strategies")
            set_last_scan()
            return

        active_strategies = [dict(r) for r in rows]
        logger.info("cycle_started", strategies_count=len(active_strategies))
        start_time = asyncio.get_event_loop().time()
        
        now_dt = datetime.now(timezone.utc)

        for strategy in active_strategies:
            try:
                # 1. Cooldown check
                if strategy["last_triggered_at"]:
                    try:
                        last_dt = datetime.fromisoformat(strategy["last_triggered_at"])
                        cooldown_mins = strategy["cooldown_minutes"] or 15
                        if now_dt - last_dt < timedelta(minutes=cooldown_mins):
                            logger.info("scheduler_cooldown_skipped", sid=strategy["id"])
                            continue
                    except ValueError:
                        pass
                
                # 2. Get chart and ai prompt
                chart = db.execute("SELECT * FROM charts WHERE id = ?", (strategy["chart_id"],)).fetchone()
                if not chart:
                    continue
                    
                ai_prompt = ""
                if strategy["ai_strategy_id"]:
                    ai_row = db.execute("SELECT content FROM ai_strategies WHERE id = ?", (strategy["ai_strategy_id"],)).fetchone()
                    if ai_row:
                        ai_prompt = ai_row["content"]
                        
                if not ai_prompt:
                    logger.warning("ai_strategy_empty", sid=strategy["id"])
                    continue
                
                await self._process_strategy(strategy, chart, ai_prompt)
            except Exception as e:
                logger.error(
                    "strategy_processing_failed",
                    sid=strategy["id"],
                    error=str(e),
                )
            await asyncio.sleep(self.settings.AI_CALL_DELAY)

        set_last_scan()
        elapsed = asyncio.get_event_loop().time() - start_time
        logger.info("cycle_completed", duration_seconds=round(elapsed, 2))


    async def _process_strategy(self, strategy: dict, chart, ai_prompt: str) -> None:
        logger.info("processing_strategy", sid=strategy["id"], name=strategy["name"], chart=chart["name"])

        # Capture Screenshot
        screenshot = await self.browser.capture(chart["name"], chart["url"])
        
        # Analyze using MiniMax AI
        analysis = await self.ai.analyze(screenshot, ai_prompt)
        
        now = datetime.now(timezone.utc).isoformat()
        db = get_db()
        
        # Threshold Evaluation
        threshold = float(strategy["min_score"]) if strategy["min_score"] is not None else float(
            (db.execute("SELECT value FROM settings WHERE key = 'NOTIFICATION_THRESHOLD'").fetchone() or {"value": 7.0})["value"]
        )
        
        sent = analysis.score >= threshold and analysis.direction.value != "NEUTRAL"

        # Persist Image
        screenshot_filename = f"{chart['name'].replace('/', '_')}_{int(time.time())}.png"
        screenshot_path = Path("data/screenshots") / screenshot_filename
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(screenshot)
        
        # Insert Analysis
        cur = db.execute(
            """INSERT INTO analyses 
            (chart_name, timestamp, score, direction, reason, entry, stop_loss, take_profit, sent, screenshot, error, active_strategy_id, active_strategy_name) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chart["name"], now, analysis.score, analysis.direction.value,
                analysis.reason, analysis.entry, analysis.stop_loss,
                analysis.take_profit, int(sent), screenshot_filename,
                analysis.error, strategy["id"], strategy["name"]
            ),
        )
        analysis_id = cur.lastrowid

        if sent:
            timeframe = chart["timeframe"] or "15m"
            # We don't have C++ body for AI Only, so no extra caption
            caption = await self.telegram.notify(chart["name"], analysis, screenshot, timeframe=timeframe, analysis_id=analysis_id)
            db.execute(
                """INSERT INTO notifications 
                (analysis_id, chart_name, timestamp, score, direction, status, caption, active_strategy_name) 
                VALUES (?, ?, ?, ?, ?, 'sent', ?, ?)""",
                (analysis_id, chart["name"], now, analysis.score, analysis.direction.value, caption, strategy["name"]),
            )
            db.execute("UPDATE active_strategies SET last_triggered_at = ? WHERE id = ?", (now, strategy["id"]))
        else:
            logger.info(
                "threshold_not_met",
                chart=chart["name"],
                score=analysis.score,
                threshold=threshold,
            )

        db.commit()
