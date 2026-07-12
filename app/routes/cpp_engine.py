import asyncio
import structlog
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.config.settings import Settings
from app.database import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/cpp-engine", tags=["cpp_engine"])


async def _pipe_stdout(proc: asyncio.subprocess.Process) -> None:
    """Read and log the C++ engine's stdout until the process exits."""
    if not proc.stdout:
        return
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        logger.info("cpp_engine", line=line.decode("utf-8", errors="replace").rstrip())


async def _stop_engine(app_state) -> None:
    """Terminate the C++ engine subprocess with SIGTERM, force kill after 5s."""
    engine = getattr(app_state, "cpp_engine", None)
    if not engine or not engine.get("process"):
        return
    proc = engine["process"]
    if proc.returncode is not None:
        app_state.cpp_engine = None
        return
    logger.info("stopping_cpp_engine", pid=proc.pid)
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        logger.warning("cpp_engine_kill", pid=proc.pid)
        proc.kill()
        await proc.wait()
    app_state.cpp_engine = None
    logger.info("cpp_engine_stopped")


@router.post("/start")
async def start_engine(request: Request):
    """Launch the C++ signal engine as a subprocess."""
    engine = getattr(request.app.state, "cpp_engine", None)
    if engine and engine.get("process") and engine["process"].returncode is None:
        raise HTTPException(status_code=409, detail="Engine already running")

    settings: Settings = request.app.state._settings
    binary = settings.CPP_ENGINE_BINARY
    config = settings.CPP_ENGINE_CONFIG

    if not Path(binary).is_file():
        raise HTTPException(
            status_code=500,
            detail=f"C++ engine binary not found: {binary}. Build it first with cmake.",
        )

    proc = await asyncio.create_subprocess_exec(
        binary, config,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    request.app.state.cpp_engine = {
        "process": proc,
        "started_at": time.monotonic(),
    }

    asyncio.create_task(_pipe_stdout(proc))

    logger.info("cpp_engine_started", pid=proc.pid, binary=binary)
    return {"ok": True, "pid": proc.pid}


@router.post("/stop")
async def stop_engine(request: Request):
    """Stop the C++ engine subprocess (SIGTERM, kill after 5s)."""
    await _stop_engine(request.app.state)
    return {"ok": True}


@router.get("/status")
async def engine_status(request: Request):
    """Return whether the C++ engine is running, its PID, uptime, and last signal from DB."""
    engine = getattr(request.app.state, "cpp_engine", None)
    proc = engine.get("process") if engine else None
    running = proc is not None and proc.returncode is None
    pid = proc.pid if running else None
    uptime = None
    if running and engine and engine.get("started_at"):
        uptime = int(time.monotonic() - engine["started_at"])

    # Last signal stored in DB (from /trigger)
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
