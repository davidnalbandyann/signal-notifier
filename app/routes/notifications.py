from fastapi import APIRouter, Query
from app.database import get_db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    page: int = Query(1),
    page_size: int = Query(50),
):
    db = get_db()
    total_row = db.execute("SELECT COUNT(*) as cnt FROM notifications").fetchone()
    total = total_row["cnt"] if total_row else 0

    offset = (page - 1) * page_size
    rows = db.execute(
        "SELECT * FROM notifications ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (page_size, offset),
    ).fetchall()

    items = []
    for r in rows:
        items.append(_notification_row(r))
    return {"items": items, "total": total}


@router.get("/{notification_id}")
async def get_notification(notification_id: int):
    db = get_db()
    row = db.execute(
        "SELECT * FROM notifications WHERE id = ?", (notification_id,)
    ).fetchone()
    if not row:
        return {}
    return _notification_row(row)


@router.delete("/{notification_id}")
async def delete_notification(notification_id: int):
    db = get_db()
    db.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
    db.commit()
    return {"ok": True}


def _notification_row(r) -> dict:
    return {
        "id": r["id"],
        "analysis_id": r["analysis_id"],
        "chart_name": r["chart_name"],
        "timestamp": r["timestamp"],
        "score": r["score"],
        "direction": r["direction"],
        "status": r["status"],
        "caption": r["caption"],
    }
