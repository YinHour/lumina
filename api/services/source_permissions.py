from typing import Optional


def check_source_access(
    source_owner_id: Optional[str], source_visibility: str, user_id: Optional[str]
) -> bool:
    """Return whether a user can read a source."""
    if source_visibility == "public":
        return True
    if user_id and source_owner_id and str(source_owner_id) == user_id:
        return True
    return False


def check_source_ownership(
    source_owner_id: Optional[str], user_id: Optional[str]
) -> bool:
    """Return whether a user owns a source."""
    if not user_id or not source_owner_id:
        return False
    return str(source_owner_id) == user_id

