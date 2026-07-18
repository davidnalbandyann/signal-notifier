import base64
import structlog
import time
from pathlib import Path
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import Response, FileResponse
from app.database import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.get("")
async def list_analyses(
    chart: str = Query(""),
    direction: str = Query(""),
    min_score: float = Query(0.0),
    date_from: str = Query(""),
    date_to: str = Query(""),
    signals_only: bool = Query(False),
    page: int = Query(1),
    page_size: int = Query(20),
):
    db = get_db()
    conditions = []
    params = []

    if chart:
        conditions.append("chart_name = ?")
        params.append(chart)
    if direction:
        conditions.append("direction = ?")
        params.append(direction)
    if min_score > 0:
        conditions.append("score >= ?")
        params.append(min_score)
    if date_from:
        conditions.append("timestamp >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("timestamp <= ?")
        params.append(date_to)
    if signals_only:
        conditions.append("sent = 1")

    where = " AND ".join(conditions) if conditions else "1=1"

    total_row = db.execute(
        f"SELECT COUNT(*) as cnt FROM analyses WHERE {where}", params
    ).fetchone()
    total = total_row["cnt"] if total_row else 0

    offset = (page - 1) * page_size
    rows = db.execute(
        f"SELECT a.*, (SELECT n.id FROM notifications n WHERE n.analysis_id = a.id ORDER BY n.id DESC LIMIT 1) AS notification_id FROM analyses a WHERE {where} ORDER BY a.timestamp DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()

    return {
        "items": [_analysis_row(r) for r in rows],
        "total": total,
    }


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: int):
    db = get_db()
    row = db.execute(
        "SELECT a.*, (SELECT n.id FROM notifications n WHERE n.analysis_id = a.id ORDER BY n.id DESC LIMIT 1) AS notification_id FROM analyses a WHERE a.id = ?", (analysis_id,)
    ).fetchone()
    if not row:
        return {}
    return _analysis_row(row)


@router.get("/{analysis_id}/screenshot")
async def get_screenshot(analysis_id: int):
    db = get_db()
    row = db.execute(
        "SELECT screenshot FROM analyses WHERE id = ?", (analysis_id,)
    ).fetchone()
    if not row or not row["screenshot"]:
        return Response(status_code=404)

    screenshot_val = row["screenshot"]
    if screenshot_val.endswith(".png"):
        file_path = Path("data/screenshots") / screenshot_val
        if file_path.is_file():
            return FileResponse(file_path, media_type="image/png")
    try:
        return Response(content=base64.b64decode(screenshot_val), media_type="image/png")
    except Exception:
        return Response(status_code=404)


@router.delete("/{analysis_id}")
async def delete_analysis(analysis_id: int):
    db = get_db()
    db.execute("DELETE FROM notifications WHERE analysis_id = ?", (analysis_id,))
    db.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    db.commit()
    return {"ok": True}


@router.post("/{analysis_id}/resend")
async def resend_analysis(analysis_id: int, request: Request):
    telegram = getattr(request.app.state, "telegram", None)
    if telegram is None:
        raise HTTPException(status_code=503, detail="Telegram service not available")

    db = get_db()
    row = db.execute(
        "SELECT a.*, (SELECT n.id FROM notifications n WHERE n.analysis_id = a.id ORDER BY n.id DESC LIMIT 1) AS notification_id "
        "FROM analyses a WHERE a.id = ?", (analysis_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")

    screenshot_bytes = _load_screenshot_bytes(row)

    from app.models.schemas import AnalysisResult, Direction
    analysis = AnalysisResult(
        score=row["score"],
        direction=Direction(row["direction"]),
        reason=row["reason"],
        entry=row["entry"],
        stop_loss=row["stop_loss"],
        take_profit=row["take_profit"],
    )

    try:
        caption = await telegram.notify(row["chart_name"], analysis, screenshot_bytes, analysis_id=analysis_id)
    except Exception as e:
        logger.error("resend_failed", analysis_id=analysis_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to resend: {e}")

    db.execute(
        "INSERT INTO notifications (analysis_id, chart_name, timestamp, score, direction, status, caption) "
        "VALUES (?, ?, datetime('now'), ?, ?, 'resent', ?)",
        (analysis_id, row["chart_name"], row["score"], row["direction"], caption),
    )
    db.commit()
    logger.info("analysis_resent", analysis_id=analysis_id)
    return {"ok": True}


@router.post("/{analysis_id}/reanalyze")
async def reanalyze_analysis(analysis_id: int, request: Request):
    nvidia = getattr(request.app.state, "nvidia", None)
    if nvidia is None:
        raise HTTPException(status_code=503, detail="AI service not available")

    db = get_db()
    row = db.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")

    screenshot_bytes = _load_screenshot_bytes(row)
    if screenshot_bytes is None:
        raise HTTPException(status_code=404, detail="Screenshot not found for reanalysis")

    try:
        new_analysis = await nvidia.analyze(screenshot_bytes)
    except Exception as e:
        logger.error("reanalyze_failed", analysis_id=analysis_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Reanalysis failed: {e}")

    db.execute(
        "UPDATE analyses SET score = ?, direction = ?, reason = ?, entry = ?, stop_loss = ?, "
        "take_profit = ?, error = ? WHERE id = ?",
        (
            new_analysis.score, new_analysis.direction.value, new_analysis.reason,
            new_analysis.entry, new_analysis.stop_loss, new_analysis.take_profit,
            new_analysis.error, analysis_id,
        ),
    )
    db.commit()
    logger.info(
        "analysis_reanalyzed",
        analysis_id=analysis_id,
        new_score=new_analysis.score,
        new_direction=new_analysis.direction.value,
    )
    return {"ok": True}


def _load_screenshot_bytes(row) -> bytes | None:
    screenshot_val = row["screenshot"] if "screenshot" in row.keys() else None
    if not screenshot_val:
        return None
    if screenshot_val.endswith(".png"):
        file_path = Path("data/screenshots") / screenshot_val
        if file_path.is_file():
            return file_path.read_bytes()
    try:
        return base64.b64decode(screenshot_val)
    except Exception:
        return None


def _analysis_row(r) -> dict:
    data = {
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
    if "error" in r.keys() and r["error"]:
        data["error"] = r["error"]
    has_screenshot = r["screenshot"] if "screenshot" in r.keys() else None
    if has_screenshot:
        data["screenshot_url"] = f"/api/analyses/{r['id']}/screenshot"
    if "notification_id" in r.keys() and r["notification_id"] is not None:
        data["notification_id"] = r["notification_id"]
    return data
