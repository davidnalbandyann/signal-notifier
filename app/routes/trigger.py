import json
import time
import structlog
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request

from app.config.settings import Settings
from app.database import get_db
from app.models.schemas import AnalysisResult, Direction
from app.state import set_last_scan

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/trigger", tags=["trigger"])

def _signal_caption(body: dict) -> str:
    direction = body.get("direction", "?").upper()
    entry = body.get("entry_price")
    extra = body.get("extra", {})

    parts = [f"🤖 <b>C++ Trigger: {direction}</b>"]
    if entry:
        parts.append(f"@{entry}")
    dist = extra.get("distance_pct")
    if dist is not None:
        parts.append(f"Dist {dist*100:.2f}%")
    vr = extra.get("volume_ratio")
    if vr is not None:
        parts.append(f"VolR {vr:.2f}")
    zt = extra.get("zone_type")
    if zt is not None:
        parts.append(zt.capitalize())

    return " | ".join(parts) + "\n"


@router.post("")
async def trigger_signal(body: dict, request: Request):
    """Accept a structured signal from the C++ engine based on an active_strategy."""
    settings = Settings()
    if settings.TRIGGER_TOKEN:
        token = request.headers.get("X-Trigger-Token", "")
        if token != settings.TRIGGER_TOKEN:
            raise HTTPException(status_code=401, detail="bad trigger token")

    active_strategy_id = body.get("active_strategy_id")
    if not active_strategy_id:
        raise HTTPException(status_code=400, detail="active_strategy_id is required")

    db = get_db()
    # 1. Lookup active strategy
    row = db.execute("SELECT * FROM active_strategies WHERE id = ?", (active_strategy_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="active strategy not found")
    if not row["enabled"]:
        return {"ok": True, "skipped": True, "reason": "strategy disabled"}

    # 2. Check Cooldown
    now_dt = datetime.now(timezone.utc)
    if row["last_triggered_at"]:
        try:
            last_dt = datetime.fromisoformat(row["last_triggered_at"])
            cooldown_mins = row["cooldown_minutes"] or 15
            if now_dt - last_dt < timedelta(minutes=cooldown_mins):
                logger.info("trigger_cooldown", sid=active_strategy_id)
                return {"ok": True, "skipped": True, "reason": "cooldown"}
        except ValueError:
            pass

    # 3. Get linked Chart and AI Prompt
    chart = db.execute("SELECT * FROM charts WHERE id = ?", (row["chart_id"],)).fetchone()
    if not chart:
        raise HTTPException(status_code=400, detail="linked chart not found")

    ai_prompt = ""
    if row["ai_strategy_id"]:
        ai_row = db.execute("SELECT content FROM ai_strategies WHERE id = ?", (row["ai_strategy_id"],)).fetchone()
        if ai_row:
            ai_prompt = ai_row["content"]

    symbol = body.get("symbol", chart["symbol"] or chart["name"]).upper()
    direction = body.get("direction", "neutral")
    entry_price = body.get("entry_price")
    timeframe = body.get("timeframe", chart["timeframe"] or "15m")
    extra = body.get("extra", {})

    logger.info("trigger_received", sid=active_strategy_id, name=row["name"], symbol=symbol, direction=direction)

    browser = request.app.state.browser
    ai = request.app.state.ai
    telegram = request.app.state.telegram

    try:
        # Some components had signature capture(name, url) and some capture_chart(url)
        # Check signature or use capture(name, url) which is what was in trigger.py previously
        screenshot = await browser.capture(chart["name"], chart["url"])
    except Exception as e:
        logger.warning("trigger_screenshot_failed", sid=active_strategy_id, error=str(e))
        screenshot = b""

    mode = row["mode"]
    
    # 4. Evaluate Score
    if mode == "cpp_only" or not ai_prompt:
        analysis = AnalysisResult(
            score=0.0,
            direction=Direction(direction.upper()) if direction.upper() in ("LONG", "SHORT", "NEUTRAL") else Direction.NEUTRAL,
            reason=f"C++ triggered {direction.upper()} signal @ {entry_price}" if entry_price else f"C++ triggered {direction.upper()} signal",
            entry=str(entry_price) if entry_price else None,
            stop_loss=None,
            take_profit=None,
            error=None,
        )
        distance = float(extra.get("distance_pct", 0.03))
        vr = float(extra.get("volume_ratio", 1.5))
        zone_type = extra.get("zone_type", "")
        d_score = (1 - min(distance, 0.03) / 0.03) * 3
        v_score = (min(vr, 4.0) / 1.5 - 1) * 3
        z_score = 2 if (direction.upper() == "LONG" and zone_type == "support") or (direction.upper() == "SHORT" and zone_type == "resistance") else 0
        score = d_score + v_score + z_score
        analysis.score = round(min(10.0, max(0.0, score)), 1)
    else:
        try:
            analysis = await ai.analyze(screenshot, ai_prompt)
        except Exception as e:
            logger.error("trigger_pipeline_failed", sid=active_strategy_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # 5. Threshold Filter
    threshold = float(row["min_score"]) if row["min_score"] is not None else float(
        (db.execute("SELECT value FROM settings WHERE key = 'NOTIFICATION_THRESHOLD'").fetchone() or {"value": 7.0})["value"]
    )

    sent = analysis.score >= threshold and analysis.direction.value != "NEUTRAL"

    # 6. Persist to DB
    now_iso = now_dt.isoformat()
    chart_name = chart["name"]
    screenshot_filename = f"{chart_name.replace('/', '_')}_{int(time.time())}.png"
    screenshot_path = Path("data/screenshots") / screenshot_filename
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    if screenshot:
        screenshot_path.write_bytes(screenshot)

    signal_json = json.dumps(body)

    cur = db.execute(
        """INSERT INTO analyses 
        (chart_name, timestamp, score, direction, reason, entry, stop_loss, take_profit, sent, screenshot, error, signal_json, active_strategy_id, active_strategy_name) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            chart_name, now_iso, analysis.score, analysis.direction.value,
            analysis.reason, analysis.entry, analysis.stop_loss,
            analysis.take_profit, int(sent), screenshot_filename if screenshot else None,
            analysis.error, signal_json, row["id"], row["name"]
        ),
    )
    analysis_id = cur.lastrowid

    if sent:
        extra_caption = _signal_caption(body)
        caption = await telegram.notify(chart_name, analysis, screenshot or None, extra_caption=extra_caption, timeframe=timeframe, analysis_id=analysis_id)
        db.execute(
            """INSERT INTO notifications 
            (analysis_id, chart_name, timestamp, score, direction, status, caption, active_strategy_name) 
            VALUES (?, ?, ?, ?, ?, 'sent', ?, ?)""",
            (analysis_id, chart_name, now_iso, analysis.score, analysis.direction.value, caption, row["name"]),
        )
        
        # Update cooldown timer
        db.execute("UPDATE active_strategies SET last_triggered_at = ? WHERE id = ?", (now_iso, row["id"]))

    db.commit()
    set_last_scan()

    return {
        "ok": True,
        "score": analysis.score,
        "direction": analysis.direction.value,
        "sent": sent,
    }
