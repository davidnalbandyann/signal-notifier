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
    "URLS_FILE",
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
async def update_settings(body: dict):
    db = get_db()
    for key, value in body.items():
        if key in EDITABLE_KEYS:
            db.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, str(value)),
            )
    db.commit()
    return {"ok": True}


SECRET_KEYS = {"TELEGRAM_TOKEN", "NVIDIA_API_KEY"}

BOOLEAN_KEYS = {"HEADLESS", "TELEGRAM_SEND_SCREENSHOT", "NOTIFY_LONG", "NOTIFY_SHORT", "NOTIFY_NEUTRAL"}


def _mask_value(key: str, val):
    if key in SECRET_KEYS and isinstance(val, str) and len(val) > 4:
        return "*" * (len(val) - 4) + val[-4:]
    return val


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
