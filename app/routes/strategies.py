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

VALID_TYPES = ("prompt", "cpp")


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "content": row["content"] or "",
        "engine_type": row["engine_type"],
        "params": json.loads(row["params"] or "{}"),
        "active": bool(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _get_strategy(sid: int):
    db = get_db()
    row = db.execute("SELECT * FROM strategies WHERE id = ?", (sid,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="strategy not found")
    return row


def _engine_config_path(request: Request) -> Path:
    settings = getattr(request.app.state, "_settings", None)
    path = getattr(settings, "CPP_ENGINE_CONFIG", "trading-signal-engine/config.json")
    return Path(path)


def _write_cpp_config(request: Request, strategy_row) -> None:
    """Sync the active C++ strategy into the engine's config.json."""
    config_path = _engine_config_path(request)
    if not config_path.exists():
        logger.warning("cpp_config_not_found", path=str(config_path))
        return
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        cfg["strategy"] = {
            "type": strategy_row["engine_type"],
            "params": json.loads(strategy_row["params"] or "{}"),
        }
        config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        logger.info("cpp_config_synced", path=str(config_path), type=strategy_row["engine_type"])
    except Exception as e:
        logger.error("cpp_config_sync_failed", error=str(e))


def _sync_active_cpp_config(request: Request) -> None:
    db = get_db()
    row = db.execute(
        "SELECT * FROM strategies WHERE type = 'cpp' AND active = 1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        _write_cpp_config(request, row)


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


@router.get("")
async def list_strategies(type: str | None = None):
    db = get_db()
    if type:
        if type not in VALID_TYPES:
            raise HTTPException(status_code=400, detail="type must be 'prompt' or 'cpp'")
        rows = db.execute(
            "SELECT * FROM strategies WHERE type = ? ORDER BY active DESC, id ASC", (type,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM strategies ORDER BY type ASC, active DESC, id ASC").fetchall()
    return {"strategies": [_row_to_dict(r) for r in rows]}


@router.get("/catalog")
async def strategy_catalog():
    return {"catalog": get_cpp_catalog()}


@router.get("/{sid}")
async def get_strategy(sid: int):
    return _row_to_dict(_get_strategy(sid))


@router.post("")
async def create_strategy(body: dict, request: Request):
    name = (body.get("name") or "").strip()
    stype = body.get("type")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if stype not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="type must be 'prompt' or 'cpp'")

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    if stype == "prompt":
        cur = db.execute(
            "INSERT INTO strategies (name, type, content, created_at, updated_at) VALUES (?, 'prompt', ?, ?, ?)",
            (name, body.get("content", ""), now, now),
        )
    else:
        engine_type = body.get("engine_type", "")
        if not validate_strategy_type(engine_type):
            raise HTTPException(status_code=400, detail=f"unknown engine_type: {engine_type}")
        params = json.dumps(normalize_cpp_params(engine_type, body.get("params")))
        cur = db.execute(
            "INSERT INTO strategies (name, type, engine_type, params, created_at, updated_at) VALUES (?, 'cpp', ?, ?, ?, ?)",
            (name, engine_type, params, now, now),
        )
    db.commit()
    return _row_to_dict(_get_strategy(cur.lastrowid))


@router.put("/{sid}")
async def update_strategy(sid: int, body: dict, request: Request):
    row = _get_strategy(sid)
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    name = (body.get("name") or "").strip() if "name" in body else row["name"]
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    if row["type"] == "prompt":
        content = body.get("content") if "content" in body else row["content"]
        db.execute(
            "UPDATE strategies SET name = ?, content = ?, updated_at = ? WHERE id = ?",
            (name, content, now, sid),
        )
    else:
        engine_type = body.get("engine_type", row["engine_type"])
        if not validate_strategy_type(engine_type):
            raise HTTPException(status_code=400, detail=f"unknown engine_type: {engine_type}")
        existing = row["params"] if isinstance(row["params"], dict) else json.loads(row["params"] or "{}")
        params = json.dumps(normalize_cpp_params(engine_type, body.get("params", existing)))
        db.execute(
            "UPDATE strategies SET name = ?, engine_type = ?, params = ?, updated_at = ? WHERE id = ?",
            (name, engine_type, params, now, sid),
        )
    db.commit()

    if row["type"] == "cpp" and row["active"]:
        _write_cpp_config(request, _get_strategy(sid))
        if await _restart_engine_if_running(request):
            logger.info("cpp_engine_restarted_after_strategy_update", sid=sid)
    return _row_to_dict(_get_strategy(sid))


@router.delete("/{sid}")
async def delete_strategy(sid: int):
    row = _get_strategy(sid)
    if row["active"]:
        raise HTTPException(status_code=400, detail="cannot delete the active strategy")
    db = get_db()
    db.execute("DELETE FROM strategies WHERE id = ?", (sid,))
    db.commit()
    return {"ok": True}


@router.post("/{sid}/activate")
async def activate_strategy(sid: int, request: Request):
    row = _get_strategy(sid)
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute("UPDATE strategies SET active = 0, updated_at = ? WHERE type = ?", (now, row["type"]))
    db.execute("UPDATE strategies SET active = 1, updated_at = ? WHERE id = ?", (now, sid))
    db.commit()

    if row["type"] == "cpp":
        _write_cpp_config(request, _get_strategy(sid))
        restarted = await _restart_engine_if_running(request)
        logger.info("cpp_strategy_activated", sid=sid, type=row["engine_type"], restarted=restarted)

    return _row_to_dict(_get_strategy(sid))


@router.post("/{sid}/duplicate")
async def duplicate_strategy(sid: int, request: Request):
    row = _get_strategy(sid)
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    new_name = f"{row['name']} (copy)"
    if row["type"] == "prompt":
        db.execute(
            "INSERT INTO strategies (name, type, content, created_at, updated_at) VALUES (?, 'prompt', ?, ?, ?)",
            (new_name, row["content"], now, now),
        )
    else:
        db.execute(
            "INSERT INTO strategies (name, type, engine_type, params, created_at, updated_at) VALUES (?, 'cpp', ?, ?, ?, ?)",
            (new_name, row["engine_type"], row["params"], now, now),
        )
    db.commit()
    return _row_to_dict(_get_strategy(db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]))
