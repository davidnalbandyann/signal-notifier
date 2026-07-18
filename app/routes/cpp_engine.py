import asyncio
import structlog

from fastapi import APIRouter, Request

from app.database import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/cpp-engine", tags=["cpp_engine"])

SYSTEMD_SERVICE = "trading-notifier-engine.service"


async def _run_cmd(*args: str) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(), stderr.decode()


async def _systemctl_active() -> bool:
    rc, out, _ = await _run_cmd("systemctl", "is-active", SYSTEMD_SERVICE)
    return rc == 0 and out.strip() == "active"


async def _systemctl_pid() -> int | None:
    rc, out, _ = await _run_cmd(
        "systemctl", "show", SYSTEMD_SERVICE, "--property=MainPID", "--value"
    )
    if rc == 0:
        pid = int(out.strip())
        return pid if pid > 0 else None
    return None


@router.post("/start")
async def start_engine(request: Request):
    if await _systemctl_active():
        pid = await _systemctl_pid()
        return {"ok": True, "pid": pid, "message": "Already running"}

    rc, out, err = await _run_cmd("sudo", "systemctl", "start", SYSTEMD_SERVICE)
    if rc != 0:
        raise Exception(f"systemctl start failed: {err.strip() or out.strip()}")

    await asyncio.sleep(0.5)
    pid = await _systemctl_pid()
    logger.info("cpp_engine_started_via_systemd", pid=pid)
    return {"ok": True, "pid": pid}


@router.post("/stop")
async def stop_engine(request: Request):
    if not await _systemctl_active():
        return {"ok": True, "message": "Already stopped"}

    rc, out, err = await _run_cmd("sudo", "systemctl", "stop", SYSTEMD_SERVICE)
    if rc != 0:
        raise Exception(f"systemctl stop failed: {err.strip() or out.strip()}")

    logger.info("cpp_engine_stopped_via_systemd")
    return {"ok": True}


@router.get("/logs")
async def engine_logs():
    rc, out, _ = await _run_cmd("journalctl", "-u", SYSTEMD_SERVICE, "-n", "100", "--no-pager", "-o", "cat")
    if rc != 0:
        return {"lines": []}
    lines = [l for l in out.split("\n") if l.strip()]
    return {"lines": lines}


@router.get("/signals")
async def engine_signals():
    db = get_db()
    rows = db.execute(
        "SELECT id, chart_name, timestamp, score, direction, entry, signal_json, sent "
        "FROM analyses WHERE signal_json IS NOT NULL ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    signals_list = []
    for r in rows:
        signals_list.append({
            "id": r["id"],
            "chart_name": r["chart_name"],
            "timestamp": r["timestamp"],
            "score": r["score"],
            "direction": r["direction"],
            "entry": r["entry"],
            "sent": bool(r["sent"]),
            "signal_json": r["signal_json"],
        })
    return {"signals": signals_list}


@router.get("/status")
async def engine_status(request: Request):
    running = await _systemctl_active()
    pid = await _systemctl_pid() if running else None
    uptime = None

    if running and pid:
        rc, out, _ = await _run_cmd("systemctl", "show", SYSTEMD_SERVICE, "--property=ActiveEnterTimestamp", "--value")
        if rc == 0 and out.strip():
            try:
                from datetime import datetime
                started = datetime.fromisoformat(out.strip())
                uptime = int((datetime.now() - started).total_seconds())
            except Exception:
                pass

    db = get_db()
    row = db.execute(
        "SELECT chart_name, timestamp, score, direction, entry, signal_json "
        "FROM analyses WHERE signal_json IS NOT NULL ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    last_signal = None
    if row:
        last_signal = {
            "chart_name": row["chart_name"],
            "timestamp": row["timestamp"],
            "score": row["score"],
            "direction": row["direction"],
            "entry": row["entry"],
        }

    return {
        "running": running,
        "pid": pid,
        "uptime_seconds": uptime,
        "last_signal": last_signal,
    }
