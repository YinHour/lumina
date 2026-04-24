"""
Verification code management: generate, send, and verify codes for
email-based registration and password reset.
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger

from api.email_service import send_verification_email, generate_code
from open_notebook.database.repository import repo_query
from open_notebook.utils.encryption import get_secret_from_env

# Code validity period in seconds
CODE_TTL_SECONDS = int(os.getenv("VERIFICATION_CODE_TTL_SECONDS", "600"))  # 10 minutes

# Rate limit: minimum seconds between send attempts for same email+purpose
SEND_COOLDOWN_SECONDS = int(os.getenv("VERIFICATION_CODE_COOLDOWN_SECONDS", "300"))  # 5 minutes

# Whether public registration is allowed
ALLOW_PUBLIC_REGISTRATION = os.getenv("ALLOW_PUBLIC_REGISTRATION", "false").lower() == "true"

# Maximum invalid verification attempts before the code is treated as expired
MAX_VERIFICATION_ATTEMPTS = int(os.getenv("VERIFICATION_CODE_MAX_ATTEMPTS", "5"))


def hash_verification_code(code: str) -> str:
    """Hash a verification code before storing/comparing it."""
    secret = (
        get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY")
        or get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
    )
    if not secret:
        raise RuntimeError(
            "Verification code secret is not configured. Set OPEN_NOTEBOOK_ENCRYPTION_KEY "
            "(preferred) or OPEN_NOTEBOOK_PASSWORD (legacy fallback)."
        )
    return hmac.new(secret.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


async def _get_active_code(email: str, purpose: str) -> Optional[dict]:
    """Return the most recent unexpired, unused code for this email+purpose, or None."""
    now_value = datetime.now(timezone.utc)
    result = await repo_query(
        """
        SELECT * FROM verification_code
        WHERE email = $email
          AND purpose = $purpose
          AND used = false
          AND expires_at > $now
          AND (attempts = NONE OR attempts < $max_attempts)
        ORDER BY created DESC
        LIMIT 1
        """,
        {
            "email": email,
            "purpose": purpose,
            "now": now_value,
            "max_attempts": MAX_VERIFICATION_ATTEMPTS,
        },
    )
    if result and len(result) > 0:
        return result[0]
    return None


async def _mark_code_used(code_record_id: str) -> None:
    """Mark a verification code record as used."""
    await repo_query(
        f"UPDATE {code_record_id} SET used = true"
    )


async def _increment_code_attempts(code_record_id: str) -> None:
    """Increment failed verification attempts for a code record."""
    await repo_query(
        f"UPDATE {code_record_id} SET attempts = math::min((attempts ?? 0) + 1, {MAX_VERIFICATION_ATTEMPTS})"
    )


async def _delete_expired_codes(email: str, purpose: str) -> None:
    """Delete expired codes for this email+purpose to keep table clean."""
    now_value = datetime.now(timezone.utc)
    await repo_query(
        """
        DELETE FROM verification_code
        WHERE email = $email
          AND purpose = $purpose
          AND (used = true OR expires_at <= $now)
        """,
        {
            "email": email,
            "purpose": purpose,
            "now": now_value,
        },
    )


async def send_code(email: str, purpose: str, language: str = "en") -> tuple[bool, str]:
    """Send a verification code to the given email.

    Returns:
        (success, message)
    """
    if purpose == "register" and not ALLOW_PUBLIC_REGISTRATION:
        return False, "Public registration is disabled"

    # Enforce cooldown
    active = await _get_active_code(email, purpose)
    if active:
        created_at = active["created"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
        remaining = int(SEND_COOLDOWN_SECONDS - elapsed)
        if remaining > 0:
            return False, f"Too many requests. Please wait {remaining} seconds"

    # Clean up old codes first
    await _delete_expired_codes(email, purpose)

    # Generate and store new code
    code = generate_code(6)
    code_hash = hash_verification_code(code)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=CODE_TTL_SECONDS)

    try:
        result = await repo_query(
            """
            CREATE verification_code
            SET email = $email,
                code = $code,
                purpose = $purpose,
                expires_at = <datetime>$expires_at,
                used = false,
                created = time::now()
            RETURN AFTER
            """,
            {
                "email": email,
                "code": code_hash,
                "purpose": purpose,
                "expires_at": expires_at.isoformat(),
            },
        )
        record = result[0] if result else {}
        record_id = record.get("id", "") if isinstance(record, dict) else ""
    except Exception as e:
        logger.error(f"Failed to create verification code record: {e}")
        return False, "Failed to generate code. Please try again"

    # Send the email
    ok = send_verification_email(email, code, purpose, language)
    if not ok:
        # Rollback: delete the record if email failed
        if record_id:
            await repo_query(f"DELETE FROM verification_code WHERE id = '{record_id}'")
        return False, "Failed to send email. Please check the address and try again"

    logger.info(f"Verification code sent to {email} for purpose={purpose}")
    return True, f"Code sent to {email}"


async def verify_code(email: str, code: str, purpose: str) -> tuple[bool, str]:
    """Verify a code for the given email and purpose.

    Returns:
        (success, message)
        On success, the code is marked as used.
    """
    record = await _get_active_code(email, purpose)

    if not record:
        return False, "Invalid or expired code"

    if record["code"] != hash_verification_code(code):
        await _increment_code_attempts(record["id"])
        return False, "Invalid code"

    # Mark used
    await _mark_code_used(record["id"])
    logger.info(f"Verification code verified for {email}, purpose={purpose}")
    return True, "Code verified"


async def check_user_exists(email: str) -> bool:
    """Check if a user with this email already exists in app_user table."""
    result = await repo_query(
        "SELECT * FROM app_user WHERE username = $username LIMIT 1",
        {"username": email},
    )
    return result and len(result) > 0
