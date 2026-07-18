import asyncio
from fastapi import APIRouter, Request
from app.database import get_db
from app.state import get_paused, set_paused, set_last_scan, get_last_scan_ts
from app.utils import get_display_timezone

router = APIRouter(prefix="/api", tags=["dashboard"])


def _tz_range() -> tuple[str, str]:
    """Return UTC ISO strings for start/end of today in the configured display timezone."""
    import zoneinfo
    from datetime import datetime, timezone as dt_tz, timedelta

    tz_name = get_display_timezone()
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = dt_tz.utc

    now_local = datetime.now(tz)
    day_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end_local = day_start_local + timedelta(days=1)

    utc = dt_tz.utc
    start_utc = day_start_local.astimezone(utc)
    end_utc = day_end_local.astimezone(utc)

    return start_utc.isoformat(), end_utc.isoformat()


@router.get("/status")
async def get_status(request: Request):
    db = get_db()

    charts_row = db.execute("SELECT COUNT(*) as cnt FROM charts").fetchone()
    charts = charts_row["cnt"] if charts_row else 0
    if charts == 0:
        charts = _load_chart_count_from_app(request)

    tz_start, tz_end = _tz_range()

    row = db.execute(
        "SELECT COUNT(*) as total FROM analyses WHERE timestamp >= ? AND timestamp < ?",
        (tz_start, tz_end),
    ).fetchone()
    analyses_today = row["total"] if row else 0

    row = db.execute(
        "SELECT COUNT(*) as total FROM analyses WHERE sent = 1 AND timestamp >= ? AND timestamp < ?",
        (tz_start, tz_end),
    ).fetchone()
    signals_sent = row["total"] if row else 0

    row = db.execute(
        "SELECT AVG(score) as avg FROM analyses WHERE timestamp >= ? AND timestamp < ?",
        (tz_start, tz_end),
    ).fetchone()
    avg_score = round(row["avg"], 1) if row and row["avg"] else 0.0

    recent = db.execute(
        "SELECT * FROM analyses ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()
    recent_analyses = [_analysis_row(r) for r in recent]

    signals = [a for a in recent_analyses if a["score"] >= 8.0]

    scheduler = getattr(request.app.state, "scheduler", None)
    settings = getattr(request.app.state, "_settings", None)
    interval = settings.CHECK_INTERVAL_SECONDS if settings else 60
    elapsed = asyncio.get_event_loop().time() - get_last_scan_ts()
    next_scan = max(0, int(interval - elapsed)) if get_last_scan_ts() > 0 else interval

    return {
        "running": not get_paused(),
        "next_scan_seconds": next_scan,
        "charts_count": charts,
        "analyses_today": analyses_today,
        "signals_sent": signals_sent,
        "avg_score": avg_score,
        "recent_analyses": recent_analyses,
        "signals": signals,
    }


@router.post("/scan/trigger")
async def trigger_scan(request: Request):
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler:
        await scheduler._analysis_cycle()
    return {"ok": True}


@router.post("/scan/pause")
async def pause_scan():
    set_paused(True)
    return {"ok": True}


@router.post("/scan/resume")
async def resume_scan():
    set_paused(False)
    return {"ok": True}


def _analysis_row(r) -> dict:
    return {
        "id": r["id"],
        "chart_name": r["chart_name"],
        "timestamp": r["timestamp"],
        "score": r["score"],
        "direction": r["direction"],
        "reason": r["reason"],
        "entry": r["entry"],
        "stop_loss": r["stop_loss"],
        "take_profit": r["take_profit"],
        "sent": bool(r["sent"]),
        "signal_json": r["signal_json"] if r["signal_json"] else None,
    }


def _load_chart_count_from_app(request) -> int | None:
    try:
        scheduler = getattr(request.app.state, "scheduler", None)
        if scheduler:
            charts = scheduler._load_charts()
            return len(charts)
    except Exception:
        pass
    return None
