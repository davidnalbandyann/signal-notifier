from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from app.database import get_db, infer_chart_type

router = APIRouter(prefix="/api/charts", tags=["charts"])


class ChartCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1)
    type: Optional[str] = None
    enabled: Optional[bool] = True

    @field_validator("name", "url")
    @classmethod
    def _strip_and_require(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("must not be blank")
        return v


@router.get("")
async def list_charts(type: Optional[str] = Query(None)):
    db = get_db()
    if type:
        rows = db.execute(
            "SELECT * FROM charts WHERE type = ? ORDER BY id ASC", (type,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM charts ORDER BY id ASC"
        ).fetchall()
    return [_chart_row(r) for r in rows]


@router.post("")
async def create_chart(body: ChartCreate):
    db = get_db()
    chart_type = body.type or infer_chart_type(body.name, body.url)
    try:
        cur = db.execute(
            "INSERT INTO charts (name, url, type, enabled) VALUES (?, ?, ?, 1)",
            (body.name, body.url, chart_type),
        )
        db.commit()
    except Exception:
        raise HTTPException(status_code=409, detail="Chart with this name already exists")
    row = db.execute("SELECT * FROM charts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _chart_row(row)


@router.post("/seed")
async def seed_charts_endpoint():
    from app.database import seed_charts
    inserted = seed_charts()
    db = get_db()
    rows = db.execute("SELECT * FROM charts ORDER BY id ASC").fetchall()
    return {"ok": True, "inserted": inserted, "charts": [_chart_row(r) for r in rows]}


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
    for field in ["name", "url", "type", "enabled"]:
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
    chart_type = r["type"] if ("type" in r.keys() and r["type"]) else infer_chart_type(r["name"], r["url"])
    return {
        "id": r["id"],
        "name": r["name"],
        "url": r["url"],
        "type": chart_type,
        "enabled": bool(enabled),
        "last_score": last_score,
        "last_scanned": last_scanned,
        "status": "ok" if bool(enabled) else "paused",
    }

