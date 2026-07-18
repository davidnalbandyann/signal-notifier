from fastapi import APIRouter, Request
from app.database import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])

EDITABLE_KEYS = {
    "CHECK_INTERVAL_SECONDS",
    "NOTIFICATION_THRESHOLD",
    "PLAYWRIGHT_WAIT_TIME",
    "HEADLESS",
    "BROWSER_VIEWPORT_WIDTH",
    "BROWSER_VIEWPORT_HEIGHT",
    "NVIDIA_API_KEY",
    "NVIDIA_MODEL",
    "AI_CALL_DELAY",
    "BROWSER_USER_DATA_DIR",
    "BROWSER_RETRY_COUNT",
    "BROWSER_RETRY_DELAY",
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_SEND_SCREENSHOT",
    "TELEGRAM_QUIET_START",
    "TELEGRAM_QUIET_END",
    "NOTIFY_LONG",
    "NOTIFY_SHORT",
    "NOTIFY_NEUTRAL",
    "CPP_BYPASS_AI",
    "URLS_FILE",
    "DISPLAY_TIMEZONE",
}


@router.get("")
async def get_settings(request: Request):
    db = get_db()
    settings_obj = getattr(request.app.state, "_settings", None)
    result = {}

    for key in EDITABLE_KEYS:
        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row:
            result[key] = _mask_value(key, _cast_value(key, row["value"]))
        elif settings_obj and hasattr(settings_obj, key):
            val = getattr(settings_obj, key)
            result[key] = _mask_value(key, _cast_value(key, str(val)))

    return result


@router.put("")
async def update_settings(body: dict, request: Request):
    from app.utils import validate_timezone

    db = get_db()
    for key, value in body.items():
        if key not in EDITABLE_KEYS:
            continue
        str_val = str(value)
        if key in SECRET_KEYS and _is_masked(str_val):
            continue
        if key == "DISPLAY_TIMEZONE" and str_val and not validate_timezone(str_val):
            continue
        db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, str_val),
        )
    db.commit()

    if "DISPLAY_TIMEZONE" in body:
        _sync_config_timezone(request)

    return {"ok": True}


def _sync_config_timezone(request: Request) -> None:
    import json
    from pathlib import Path
    from app.utils import get_display_timezone

    settings = getattr(request.app.state, "_settings", None)
    if not settings:
        return
    config_path = Path(settings.CPP_ENGINE_CONFIG)
    if not config_path.exists():
        return
    tz = get_display_timezone()
    try:
        cfg = json.loads(config_path.read_text())
        cfg.setdefault("logging", {})["timezone"] = tz
        config_path.write_text(json.dumps(cfg, indent=2) + "\n")
    except Exception:
        pass


SECRET_KEYS = {"TELEGRAM_TOKEN", "NVIDIA_API_KEY"}

BOOLEAN_KEYS = {"HEADLESS", "TELEGRAM_SEND_SCREENSHOT", "NOTIFY_LONG", "NOTIFY_SHORT", "NOTIFY_NEUTRAL", "CPP_BYPASS_AI"}


def _mask_value(key: str, val):
    if key in SECRET_KEYS and isinstance(val, str) and len(val) > 4:
        return "*" * (len(val) - 4) + val[-4:]
    return val


def _is_masked(val: str) -> bool:
    return val.startswith("*") and val.count("*") >= len(val) - 4


def _cast_value(key: str, val: str):
    float_keys = {"NOTIFICATION_THRESHOLD", "AI_CALL_DELAY"}
    if key in BOOLEAN_KEYS:
        return val.lower() in ("true", "1", "yes")
    if key in float_keys:
        try:
            return float(val)
        except ValueError:
            return val
    try:
        return int(val)
    except ValueError:
        return val
