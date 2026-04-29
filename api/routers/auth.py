"""
Authentication router for Lumina API.

Provides endpoints for username/password login, password change, and first-time setup.
Uses bcrypt for password hashing and JWT for session tokens.
"""

import os
import time
from typing import Any, Dict, List, Optional

import jwt
from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from api.models import (
    AuthStatusResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    SetupRequest,
    UserResponse,
)
from api.password_utils import hash_password, verify_password
from open_notebook.database.repository import (
    db_connection,
    parse_record_ids,
    repo_update,
)
from open_notebook.utils.encryption import get_secret_from_env

router = APIRouter(prefix="/auth", tags=["auth"])

# JWT configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 86400  # 24 hours


def _get_jwt_secret() -> str:
    """Derive JWT secret from encryption key for consistency."""
    secret = get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY")
    if not secret:
        # Fallback: use a default secret (only for dev without encryption)
        return "lumina-dev-jwt-secret-change-in-production"
    return secret


def _create_jwt_token(username: str, user_id: str) -> str:
    """Create a JWT token for the authenticated user."""
    payload = {
        "sub": user_id,
        "username": username,
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def _decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


async def _get_db_users() -> List[Dict[str, Any]]:
    """Query all users from the database."""
    try:
        async with db_connection() as conn:
            result = parse_record_ids(
                await conn.query("SELECT * FROM app_user ORDER BY created ASC")
            )
            if isinstance(result, list):
                # Flatten nested result structure from SurrealDB
                if result and isinstance(result[0], list):
                    return result[0]
                return result
            return []
    except Exception as e:
        logger.debug(f"Failed to query users: {e}")
        return []


async def _find_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Find a user by username."""
    try:
        async with db_connection() as conn:
            result = parse_record_ids(
                await conn.query(
                    "SELECT * FROM app_user WHERE username = $username LIMIT 1",
                    {"username": username},
                )
            )
            if isinstance(result, list):
                if result and isinstance(result[0], list):
                    users = result[0]
                else:
                    users = result
                return users[0] if users else None
            return None
    except Exception as e:
        logger.debug(f"Failed to find user: {e}")
        return None


def _get_user_id(user: Dict[str, Any]) -> str:
    """Extract user ID from user record."""
    user_id = user.get("id", "")
    # Convert RecordID to string if needed
    if hasattr(user_id, "__str__"):
        return str(user_id)
    return str(user_id)


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status():
    """
    Check authentication status.
    Returns whether auth is enabled, the auth method, and if users exist.
    """
    legacy_password = bool(get_secret_from_env("OPEN_NOTEBOOK_PASSWORD"))
    users = await _get_db_users()
    has_users = len(users) > 0

    if legacy_password:
        return AuthStatusResponse(
            auth_enabled=True,
            auth_method="legacy",
            has_users=has_users,
            message="Legacy password authentication is active",
        )
    elif has_users:
        return AuthStatusResponse(
            auth_enabled=True,
            auth_method="database",
            has_users=True,
            message="Database authentication is active",
        )
    else:
        return AuthStatusResponse(
            auth_enabled=False,
            auth_method="disabled",
            has_users=False,
            message="No authentication configured. Use /auth/setup to create an admin user.",
        )


@router.post("/setup", response_model=UserResponse)
async def setup_admin(request: SetupRequest):
    """
    Create the first admin user. Only works when no users exist in the database.
    """
    if len(await _get_db_users()) > 0:
        raise HTTPException(
            status_code=400,
            detail="Setup already completed. Users exist in the database.",
        )

    if len(request.password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 4 characters long",
        )

    hashed = hash_password(request.password)

    try:
        async with db_connection() as conn:
            result = parse_record_ids(
                await conn.query(
                    "CREATE app_user SET username = $username, hashed_password = $hashed, created = time::now(), updated = time::now()",
                    {
                        "username": request.username,
                        "hashed": hashed,
                    },
                )
            )
            # Flatten result
            if isinstance(result, list) and result:
                if isinstance(result[0], list):
                    user = result[0][0]
                else:
                    user = result[0]
            else:
                raise HTTPException(status_code=500, detail="Failed to create user")

            return UserResponse(
                username=user.get("username", request.username),
                created=str(user.get("created", "")),
                updated=str(user.get("updated", "")),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate with username and password. Returns a JWT token on success.
    """
    # Check legacy password first
    legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
    if legacy_password and request.password == legacy_password:
        # Legacy auth: accept any username with the correct legacy password
        token = _create_jwt_token(request.username, "legacy")
        return LoginResponse(
            success=True,
            token=token,
            username=request.username,
            message="Login successful",
        )

    # Database auth
    user = await _find_user_by_username(request.username)
    if not user:
        return LoginResponse(
            success=False,
            message="Invalid username or password",
        )

    if not verify_password(request.password, user.get("hashed_password", "")):
        return LoginResponse(
            success=False,
            message="Invalid username or password",
        )

    user_id = _get_user_id(user)
    token = _create_jwt_token(request.username, user_id)

    return LoginResponse(
        success=True,
        token=token,
        username=request.username,
        message="Login successful",
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(request: ChangePasswordRequest, http_request: Request):
    """
    Change the current user's password. Requires authentication.
    """
    # Get JWT token from Authorization header
    auth_header = http_request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # Try legacy password as token
        token = auth_header

    # If no auth header, try the token from the request itself
    # (the legacy middleware might have already authenticated)
    payload = None
    if token:
        payload = _decode_jwt_token(token)

    # Also check legacy password
    legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
    is_legacy = legacy_password and request.old_password == legacy_password

    if not payload and not is_legacy:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if is_legacy:
        # Legacy mode: update the env var password is not possible
        # Instead, create/update a user in the database
        users = await _get_db_users()
        if users:
            # Update first user's password
            user = users[0]
            user_id = _get_user_id(user)
            username = user.get("username", "admin")
        else:
            # Create admin user
            username = "admin"
            user_id = "app_user:admin"

        if len(request.new_password) < 4:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 4 characters long",
            )

        hashed = hash_password(request.new_password)

        try:
            await repo_update(
                "app_user",
                user_id,
                {
                    "username": username,
                    "hashed_password": hashed,
                },
            )
            return ChangePasswordResponse(
                success=True,
                message="Password changed. Future logins should use username + new password.",
            )
        except Exception as e:
            logger.error(f"Password change failed: {e}")
            raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}")

    # Database auth mode
    username = payload.get("username", "")
    user = await _find_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not verify_password(request.old_password, user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(request.new_password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 4 characters long",
        )

    hashed = hash_password(request.new_password)
    user_id = _get_user_id(user)

    try:
        await repo_update(
            "app_user",
            user_id,
            {"hashed_password": hashed},
        )
        return ChangePasswordResponse(
            success=True,
            message="Password changed successfully",
        )
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_current_user(http_request: Request):
    """
    Get current authenticated user info. Requires JWT token.
    """
    auth_header = http_request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        raise HTTPException(status_code=401, detail="Missing authorization")

    payload = _decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("username", "")
    user = await _find_user_by_username(username)
    if not user:
        return UserResponse(
            username=username,
            created="",
            updated="",
        )

    return UserResponse(
        username=user.get("username", username),
        created=str(user.get("created", "")),
        updated=str(user.get("updated", "")),
    )
