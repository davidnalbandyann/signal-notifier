import zoneinfo
from app.database import get_db

_DEFAULT_TZ = "UTC"


def get_display_timezone() -> str:
    db = get_db()
    row = db.execute(
        "SELECT value FROM settings WHERE key = ?", ("DISPLAY_TIMEZONE",)
    ).fetchone()
    if row and row["value"]:
        tz = row["value"].strip()
        try:
            zoneinfo.ZoneInfo(tz)
            return tz
        except (zoneinfo.ZoneInfoNotFoundError, KeyError):
            pass
    return _DEFAULT_TZ


def validate_timezone(tz: str) -> bool:
    try:
        zoneinfo.ZoneInfo(tz.strip())
        return True
    except (zoneinfo.ZoneInfoNotFoundError, KeyError, AttributeError):
        return False
