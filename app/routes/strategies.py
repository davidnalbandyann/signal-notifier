import json
import structlog
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.database import get_db
from app.services.cpp_strategies import (
    get_cpp_catalog,
    normalize_cpp_params,
    validate_strategy_type,
)
from app.routes.cpp_engine import SYSTEMD_SERVICE, _run_cmd

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

def _get_row_by_id(table: str, id_val: int):
    db = get_db()
    row = db.execute(f"SELECT * FROM {table} WHERE id = ?", (id_val,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"{table} record not found")
    return dict(row)

# ---------------------------------------------------------
# ENGINE CONFIG GENERATOR
# ---------------------------------------------------------

def _engine_config_path(request: Request) -> Path:
    settings = getattr(request.app.state, "_settings", None)
    path = getattr(settings, "CPP_ENGINE_CONFIG", "trading-signal-engine/config.json")
    return Path(path)

def _generate_and_write_cpp_config(request: Request):
    """Sync all enabled active_strategies (with cpp_strategy_id) into config.json."""
    config_path = _engine_config_path(request)
    if not config_path.parent.exists():
        return  # directory doesn't exist, assume not setup yet
    
    db = get_db()
    
    query = """
        SELECT a.id, a.name, a.chart_id, c.symbol, c.timeframe, 
               cpp.engine_type, cpp.params
        FROM active_strategies a
        JOIN charts c ON a.chart_id = c.id
        JOIN cpp_strategies cpp ON a.cpp_strategy_id = cpp.id
        WHERE a.enabled = 1 AND a.mode IN ('hybrid', 'cpp_only')
    """
    rows = db.execute(query).fetchall()
    
    strategies_list = []
    symbols_set = set()
    interval = "15m" # Default, could infer from rows if needed

    for r in rows:
        sym = r["symbol"]
        tf = r["timeframe"]
        if sym:
            symbols_set.add(sym)
            if tf:
                interval = tf # C++ engine currently uses a global interval, take the last one or default.
        
        strategies_list.append({
            "active_strategy_id": r["id"],
            "active_strategy_name": r["name"],
            "symbol": sym,
            "timeframe": tf,
            "type": r["engine_type"],
            "params": json.loads(r["params"] or "{}")
        })

    webhook_url = "http://127.0.0.1:8000/trigger"
    
    cfg = {
        "symbols": list(symbols_set),
        "interval": interval,
        "strategies": strategies_list,
        "webhook_url": webhook_url
    }
    
    try:
        config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        logger.info("cpp_config_synced", path=str(config_path), count=len(strategies_list))
    except Exception as e:
        logger.error("cpp_config_sync_failed", error=str(e))


async def _restart_engine_if_running(request: Request) -> bool:
    try:
        rc, out, _ = await _run_cmd("systemctl", "is-active", SYSTEMD_SERVICE)
    except (OSError, FileNotFoundError) as e:
        logger.warning("systemctl_unavailable", error=str(e))
        return False
    if rc != 0 or out.strip() != "active":
        return False
    try:
        rcr, outr, errr = await _run_cmd("sudo", "systemctl", "restart", SYSTEMD_SERVICE)
    except (OSError, FileNotFoundError) as e:
        logger.warning("systemctl_unavailable", error=str(e))
        return False
    if rcr != 0:
        logger.error("cpp_engine_restart_failed", error=errr.strip() or outr.strip())
        return False
    logger.info("cpp_engine_restarted")
    return True


# ---------------------------------------------------------
# CPP STRATEGIES LIBRARY (CRUD)
# ---------------------------------------------------------

@router.get("/cpp")
async def list_cpp_strategies():
    db = get_db()
    rows = db.execute("SELECT * FROM cpp_strategies ORDER BY id DESC").fetchall()
    return {"strategies": [dict(r) for r in rows]}

@router.get("/cpp/catalog")
async def cpp_strategy_catalog():
    return {"catalog": get_cpp_catalog()}

@router.get("/cpp/{sid}")
async def get_cpp_strategy(sid: int):
    return _get_row_by_id("cpp_strategies", sid)

@router.post("/cpp")
async def create_cpp_strategy(body: dict):
    name = (body.get("name") or "").strip()
    engine_type = body.get("engine_type", "")
    if not name or not engine_type:
        raise HTTPException(status_code=400, detail="name and engine_type are required")
    if not validate_strategy_type(engine_type):
        raise HTTPException(status_code=400, detail=f"unknown engine_type: {engine_type}")
    
    params = json.dumps(normalize_cpp_params(engine_type, body.get("params")))
    now = datetime.now(timezone.utc).isoformat()
    
    db = get_db()
    cur = db.execute(
        "INSERT INTO cpp_strategies (name, engine_type, params, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (name, engine_type, params, now, now)
    )
    db.commit()
    return _get_row_by_id("cpp_strategies", cur.lastrowid)

@router.put("/cpp/{sid}")
async def update_cpp_strategy(sid: int, body: dict, request: Request):
    row = _get_row_by_id("cpp_strategies", sid)
    name = (body.get("name") or "").strip() if "name" in body else row["name"]
    engine_type = body.get("engine_type", row["engine_type"])
    
    if not validate_strategy_type(engine_type):
        raise HTTPException(status_code=400, detail=f"unknown engine_type: {engine_type}")
    
    existing_params = row["params"] if isinstance(row["params"], dict) else json.loads(row["params"] or "{}")
    params = json.dumps(normalize_cpp_params(engine_type, body.get("params", existing_params)))
    now = datetime.now(timezone.utc).isoformat()
    
    db = get_db()
    db.execute(
        "UPDATE cpp_strategies SET name = ?, engine_type = ?, params = ?, updated_at = ? WHERE id = ?",
        (name, engine_type, params, now, sid)
    )
    db.commit()
    
    # Sync config because an active pipeline might use this
    _generate_and_write_cpp_config(request)
    await _restart_engine_if_running(request)
    
    return _get_row_by_id("cpp_strategies", sid)

@router.delete("/cpp/{sid}")
async def delete_cpp_strategy(sid: int):
    db = get_db()
    try:
        db.execute("DELETE FROM cpp_strategies WHERE id = ?", (sid,))
        db.commit()
    except Exception as e:
        if "FOREIGN KEY constraint failed" in str(e) or "RESTRICT" in str(e):
            raise HTTPException(status_code=400, detail="Cannot delete C++ strategy because it is used by an active pipeline.")
        raise
    return {"ok": True}


# ---------------------------------------------------------
# AI STRATEGIES LIBRARY (CRUD)
# ---------------------------------------------------------

@router.get("/ai")
async def list_ai_strategies():
    db = get_db()
    rows = db.execute("SELECT * FROM ai_strategies ORDER BY id DESC").fetchall()
    return {"strategies": [dict(r) for r in rows]}

@router.get("/ai/{sid}")
async def get_ai_strategy(sid: int):
    return _get_row_by_id("ai_strategies", sid)

@router.post("/ai")
async def create_ai_strategy(body: dict):
    name = (body.get("name") or "").strip()
    content = body.get("content", "")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
        
    now = datetime.now(timezone.utc).isoformat()
    db = get_db()
    cur = db.execute(
        "INSERT INTO ai_strategies (name, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (name, content, now, now)
    )
    db.commit()
    return _get_row_by_id("ai_strategies", cur.lastrowid)

@router.put("/ai/{sid}")
async def update_ai_strategy(sid: int, body: dict):
    row = _get_row_by_id("ai_strategies", sid)
    name = (body.get("name") or "").strip() if "name" in body else row["name"]
    content = body.get("content") if "content" in body else row["content"]
    now = datetime.now(timezone.utc).isoformat()
    
    db = get_db()
    db.execute(
        "UPDATE ai_strategies SET name = ?, content = ?, updated_at = ? WHERE id = ?",
        (name, content, now, sid)
    )
    db.commit()
    return _get_row_by_id("ai_strategies", sid)

@router.delete("/ai/{sid}")
async def delete_ai_strategy(sid: int):
    db = get_db()
    try:
        db.execute("DELETE FROM ai_strategies WHERE id = ?", (sid,))
        db.commit()
    except Exception as e:
        if "FOREIGN KEY constraint failed" in str(e) or "RESTRICT" in str(e):
            raise HTTPException(status_code=400, detail="Cannot delete AI strategy because it is used by an active pipeline.")
        raise
    return {"ok": True}


# ---------------------------------------------------------
# ACTIVE STRATEGIES PIPELINE (CRUD)
# ---------------------------------------------------------

@router.get("/active")
async def list_active_strategies():
    db = get_db()
    rows = db.execute("SELECT * FROM active_strategies ORDER BY enabled DESC, id DESC").fetchall()
    return {"strategies": [dict(r) for r in rows]}

@router.get("/active/{sid}")
async def get_active_strategy(sid: int):
    return _get_row_by_id("active_strategies", sid)

@router.post("/active")
async def create_active_strategy(body: dict, request: Request):
    name = (body.get("name") or "").strip()
    mode = body.get("mode")
    enabled = int(body.get("enabled", 1))
    chart_id = body.get("chart_id")
    cpp_id = body.get("cpp_strategy_id")
    ai_id = body.get("ai_strategy_id")
    min_score = body.get("min_score")
    cooldown = int(body.get("cooldown_minutes", 15))
    
    if not name or not mode or not chart_id:
        raise HTTPException(status_code=400, detail="name, mode, and chart_id are required")
    if mode not in ("hybrid", "ai_only", "cpp_only"):
        raise HTTPException(status_code=400, detail="mode must be hybrid, ai_only, or cpp_only")
        
    now = datetime.now(timezone.utc).isoformat()
    db = get_db()
    cur = db.execute(
        """INSERT INTO active_strategies 
           (name, mode, enabled, chart_id, cpp_strategy_id, ai_strategy_id, min_score, cooldown_minutes, created_at, updated_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, mode, enabled, chart_id, cpp_id, ai_id, min_score, cooldown, now, now)
    )
    db.commit()
    
    _generate_and_write_cpp_config(request)
    if enabled and cpp_id:
        await _restart_engine_if_running(request)
        
    return _get_row_by_id("active_strategies", cur.lastrowid)

@router.put("/active/{sid}")
async def update_active_strategy(sid: int, body: dict, request: Request):
    row = _get_row_by_id("active_strategies", sid)
    
    name = (body.get("name") or "").strip() if "name" in body else row["name"]
    mode = body.get("mode", row["mode"])
    enabled = int(body.get("enabled", row["enabled"]))
    chart_id = body.get("chart_id", row["chart_id"])
    cpp_id = body.get("cpp_strategy_id", row["cpp_strategy_id"])
    ai_id = body.get("ai_strategy_id", row["ai_strategy_id"])
    min_score = body.get("min_score", row["min_score"])
    cooldown = int(body.get("cooldown_minutes", row["cooldown_minutes"]))
    
    if mode not in ("hybrid", "ai_only", "cpp_only"):
        raise HTTPException(status_code=400, detail="mode must be hybrid, ai_only, or cpp_only")

    now = datetime.now(timezone.utc).isoformat()
    db = get_db()
    db.execute(
        """UPDATE active_strategies 
           SET name=?, mode=?, enabled=?, chart_id=?, cpp_strategy_id=?, ai_strategy_id=?, min_score=?, cooldown_minutes=?, updated_at=?
           WHERE id=?""",
        (name, mode, enabled, chart_id, cpp_id, ai_id, min_score, cooldown, now, sid)
    )
    db.commit()
    
    _generate_and_write_cpp_config(request)
    await _restart_engine_if_running(request)
        
    return _get_row_by_id("active_strategies", sid)

@router.delete("/active/{sid}")
async def delete_active_strategy(sid: int, request: Request):
    db = get_db()
    db.execute("DELETE FROM active_strategies WHERE id = ?", (sid,))
    db.commit()
    
    _generate_and_write_cpp_config(request)
    await _restart_engine_if_running(request)
    
    return {"ok": True}

@router.post("/active/{sid}/duplicate")
async def duplicate_active_strategy(sid: int, request: Request):
    row = _get_row_by_id("active_strategies", sid)
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    new_name = f"{row['name']} (copy)"
    
    cur = db.execute(
        """INSERT INTO active_strategies 
           (name, mode, enabled, chart_id, cpp_strategy_id, ai_strategy_id, min_score, cooldown_minutes, created_at, updated_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (new_name, row["mode"], 0, row["chart_id"], row["cpp_strategy_id"], row["ai_strategy_id"], row["min_score"], row["cooldown_minutes"], now, now)
    )
    db.commit()
    return _get_row_by_id("active_strategies", cur.lastrowid)

@router.post("/active/{sid}/test-run")
async def test_run_active_strategy(sid: int, request: Request):
    row = _get_row_by_id("active_strategies", sid)
    
    db = get_db()
    chart = db.execute("SELECT * FROM charts WHERE id = ?", (row["chart_id"],)).fetchone()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
        
    ai_prompt = ""
    if row["ai_strategy_id"]:
        ai_row = db.execute("SELECT * FROM ai_strategies WHERE id = ?", (row["ai_strategy_id"],)).fetchone()
        if ai_row: ai_prompt = ai_row["content"]
        
    # We trigger the test run by communicating directly with the services
    # We bypass cooldown checks and telegram notifications
    
    app_state = request.app.state
    browser = app_state.browser
    ai = app_state.ai
    
    try:
        # Capture screenshot
        img_bytes = await browser.capture(chart["name"], chart["url"])
        
        # We don't have C++ engine output, so for hybrid/ai_only we just do AI logic
        # Run AI logic
        if row["mode"] in ("ai_only", "hybrid") and ai_prompt:
            result = await ai.analyze(img_bytes, ai_prompt)
            return {
                "success": True,
                "result": {
                    "score": result.score,
                    "direction": result.direction,
                    "reason": result.reason,
                    "entry": result.entry,
                    "stop_loss": result.stop_loss,
                    "take_profit": result.take_profit,
                    "error": result.error,
                },
                "mode_tested": row["mode"]
            }
        elif row["mode"] == "cpp_only":
            return {
                "success": True,
                "result": {
                    "score": 10.0,
                    "direction": "LONG",
                    "reason": "Test Run in C++ Only mode bypasses AI analysis entirely.",
                },
                "mode_tested": row["mode"]
            }
        else:
            raise HTTPException(status_code=400, detail="No AI prompt linked to perform test run.")
            
    except Exception as e:
        logger.error("test_run_failed", sid=sid, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
