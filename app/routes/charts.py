from fastapi import APIRouter, HTTPException
from app.database import get_db

router = APIRouter(prefix="/api/charts", tags=["charts"])


@router.get("")
async def list_charts():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM charts ORDER BY id ASC"
    ).fetchall()
    return [_chart_row(r) for r in rows]


@router.post("")
async def create_chart(body: dict):
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO charts (name, url, enabled) VALUES (?, ?, 1)",
            (body["name"], body["url"]),
        )
        db.commit()
    except Exception:
        raise HTTPException(status_code=409, detail="Chart with this name already exists")
    row = db.execute("SELECT * FROM charts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _chart_row(row)


@router.get("/{chart_id}")
async def get_chart(chart_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM charts WHERE id = ?", (chart_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Chart not found")
    return _chart_row(row)


@router.put("/{chart_id}")
async def update_chart(chart_id: int, body: dict):
    db = get_db()
    sets = []
    vals = []
    for field in ["name", "url", "enabled"]:
        if field in body:
            sets.append(f"{field} = ?")
            vals.append(body[field])
    if not sets:
        row = db.execute("SELECT * FROM charts WHERE id = ?", (chart_id,)).fetchone()
        return _chart_row(row) if row else {}
    vals.append(chart_id)
    db.execute(f"UPDATE charts SET {', '.join(sets)} WHERE id = ?", vals)
    db.commit()
    row = db.execute("SELECT * FROM charts WHERE id = ?", (chart_id,)).fetchone()
    return _chart_row(row) if row else {}


@router.delete("/{chart_id}")
async def delete_chart(chart_id: int):
    db = get_db()
    db.execute("DELETE FROM charts WHERE id = ?", (chart_id,))
    db.commit()
    return {"ok": True}


def _chart_row(r) -> dict:
    last_score_row = get_db().execute(
        "SELECT score, timestamp FROM analyses WHERE chart_name = ? ORDER BY timestamp DESC LIMIT 1",
        (r["name"],),
    ).fetchone()
    last_score = last_score_row["score"] if last_score_row else None
    last_scanned = last_score_row["timestamp"] if last_score_row else None
    enabled = r["enabled"] if "enabled" in r.keys() else 1
    return {
        "id": r["id"],
        "name": r["name"],
        "url": r["url"],
        "enabled": bool(enabled),
        "last_score": last_score,
        "last_scanned": last_scanned,
        "status": "ok" if bool(enabled) else "paused",
    }
