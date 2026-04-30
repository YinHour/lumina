from datetime import datetime, timezone
from typing import Any, Optional

ACTIVE_COMMAND_STATUSES = {"new", "queued", "running"}


def command_status_value(status: Any) -> str:
    return getattr(status, "value", status)


def coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_command_timed_out(
    created_at: Any,
    *,
    timeout_seconds: int,
    now: Optional[datetime] = None,
) -> bool:
    created_dt = coerce_datetime(created_at)
    if created_dt is None:
        return False
    now_dt = now or datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    return (
        now_dt.astimezone(timezone.utc) - created_dt
    ).total_seconds() >= timeout_seconds

