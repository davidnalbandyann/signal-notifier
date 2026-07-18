import json
import time
import structlog
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.config.settings import Settings
from app.database import get_db
from app.models.schemas import AnalysisResult, Direction
from app.state import set_last_scan

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/trigger", tags=["trigger"])

# Timeframe to TradingView interval mapping
TV_INTERVAL = {
    "1m": "1", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "2h": "120", "4h": "240", "1d": "1D",
}


def _resolve_chart(symbol: str, timeframe: str) -> tuple[str, str]:
    """Resolve a symbol (e.g. BTCUSDT) to a chart name and TradingView URL."""
    db = get_db()
    row = db.execute(
        "SELECT name, url FROM charts WHERE url LIKE ? LIMIT 1",
        (f"%BINANCE:{symbol}%",),
    ).fetchone()
    if row:
        return row["name"], row["url"]

    # Fallback: construct a TradingView URL with Bollinger Bands
    interval = TV_INTERVAL.get(timeframe, "15")
    name = symbol
    url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}&interval={interval}"
    return name, url


def _signal_caption(body: dict) -> str:
    """Build a compact caption line from the C++ trigger payload."""
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
    """Accept a structured signal from the C++ engine.

    Expected payload:
    {
        "symbol": "BTCUSDT",
        "timestamp": 1710450000,
        "direction": "long",
        "entry_price": 68350.0,
        "timeframe": "15m",
        "extra": {"distance_pct": 0.018, "volume_ratio": 2.3, "zone_level": 68500, "zone_type": "support"}
    }

    Returns:
        {"ok": true, "score": ..., "direction": ..., "sent": ...}
    """
    # Optional shared-secret auth
    settings = Settings()
    if settings.TRIGGER_TOKEN:
        token = request.headers.get("X-Trigger-Token", "")
        if token != settings.TRIGGER_TOKEN:
            raise HTTPException(status_code=401, detail="bad trigger token")

    symbol = body.get("symbol", "").upper()
    direction = body.get("direction", "neutral")
    entry_price = body.get("entry_price")
    timeframe = body.get("timeframe", "15m")
    extra = body.get("extra", {})

    if not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")

    name, url = _resolve_chart(symbol, timeframe)
    logger.info("trigger_received", symbol=symbol, direction=direction, entry=entry_price)

    db = get_db()
    telegram = request.app.state.telegram

    # Check if C++ bypass AI gate is enabled
    bypass_row = db.execute("SELECT value FROM settings WHERE key = ?", ("CPP_BYPASS_AI",)).fetchone()
    cpp_bypass = bypass_row and bypass_row["value"].lower() in ("true", "1", "yes")

    browser = request.app.state.browser
    try:
        screenshot = await browser.capture(name, url)
    except Exception as e:
        logger.warning("trigger_screenshot_failed", symbol=symbol, error=str(e))
        screenshot = b""

    if cpp_bypass:
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
        nvidia = request.app.state.nvidia
        try:
            analysis = await nvidia.analyze(screenshot)
        except Exception as e:
            logger.error("trigger_pipeline_failed", symbol=symbol, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # Load threshold from DB setting or defaults
    row = db.execute("SELECT value FROM settings WHERE key = ?", ("NOTIFICATION_THRESHOLD",)).fetchone()
    threshold = float(row["value"]) if row else settings.NOTIFICATION_THRESHOLD

    sent = analysis.score >= threshold and analysis.direction.value != "NEUTRAL"

    # Persist to DB (mirrors scheduler._process_chart)
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    screenshot_filename = f"{name.replace('/', '_')}_{int(time.time())}.png"
    screenshot_path = Path("data/screenshots") / screenshot_filename
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    if screenshot:
        screenshot_path.write_bytes(screenshot)

    signal_json = json.dumps(body)

    cur = db.execute(
        "INSERT INTO analyses (chart_name, timestamp, score, direction, reason, entry, stop_loss, take_profit, sent, screenshot, error, signal_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            name, now, analysis.score, analysis.direction.value,
            analysis.reason, analysis.entry, analysis.stop_loss,
            analysis.take_profit, int(sent), screenshot_filename if screenshot else None,
            analysis.error, signal_json,
        ),
    )
    analysis_id = cur.lastrowid

    if sent:
        extra_caption = _signal_caption(body)
        caption = await telegram.notify(name, analysis, screenshot or None, extra_caption=extra_caption, timeframe=timeframe, analysis_id=analysis_id)
        db.execute(
            "INSERT INTO notifications (analysis_id, chart_name, timestamp, score, direction, status, caption) "
            "VALUES (?, ?, ?, ?, ?, 'sent', ?)",
            (analysis_id, name, now, analysis.score, analysis.direction.value, caption),
        )

    db.commit()
    set_last_scan()

    return {
        "ok": True,
        "score": analysis.score,
        "direction": analysis.direction.value,
        "sent": sent,
    }
