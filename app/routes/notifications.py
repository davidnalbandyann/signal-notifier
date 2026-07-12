from fastapi import APIRouter
from app.database import get_db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM notifications ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "analysis_id": r["analysis_id"],
            "chart_name": r["chart_name"],
            "timestamp": r["timestamp"],
            "score": r["score"],
            "direction": r["direction"],
            "status": r["status"],
            "caption": r["caption"],
        })
    return {"items": items, "total": len(items)}
