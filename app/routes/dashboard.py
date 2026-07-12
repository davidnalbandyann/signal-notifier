import asyncio
from fastapi import APIRouter, Request
from app.database import get_db
from app.state import get_paused, set_paused, set_last_scan, get_last_scan_ts

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/status")
async def get_status(request: Request):
    db = get_db()

    charts_row = db.execute("SELECT COUNT(*) as cnt FROM charts").fetchone()
    charts = charts_row["cnt"] if charts_row else 0
    if charts == 0:
        charts = _load_chart_count_from_app(request)

    row = db.execute(
        "SELECT COUNT(*) as total FROM analyses WHERE date(timestamp) = date('now')"
    ).fetchone()
    analyses_today = row["total"] if row else 0

    row = db.execute(
        "SELECT COUNT(*) as total FROM analyses WHERE sent = 1 AND date(timestamp) = date('now')"
    ).fetchone()
    signals_sent = row["total"] if row else 0

    row = db.execute(
        "SELECT AVG(score) as avg FROM analyses WHERE date(timestamp) = date('now')"
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
