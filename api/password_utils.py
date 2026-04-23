"""
Password hashing utilities using bcrypt.

Used for Lumina's app-level authentication: store a username + bcrypt-hashed
password in SurrealDB, verify at login time, and support password changes.
"""

import bcrypt


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt.

    Returns the bcrypt hash as a UTF-8 string (suitable for DB storage).
    """
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Returns True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
