import asyncio
import structlog

logger = structlog.get_logger(__name__)

_paused = False
_last_scan_ts = 0.0


def get_paused() -> bool:
    return _paused


def set_paused(value: bool) -> None:
    global _paused
    _paused = value


def set_last_scan() -> None:
    global _last_scan_ts
    _last_scan_ts = asyncio.get_event_loop().time()


def get_last_scan_ts() -> float:
    return _last_scan_ts
