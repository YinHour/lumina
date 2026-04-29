"""Utilities for enforcing a maximum runtime for background worker commands."""

import asyncio
import os
from typing import Any, Optional

from loguru import logger
from surreal_commands.core.service import command_service

DEFAULT_WORKER_TASK_TIMEOUT_SECONDS = 20 * 60
WORKER_TASK_TIMEOUT_ENV = "LUMINA_WORKER_TASK_TIMEOUT_SECONDS"


def get_worker_task_timeout_seconds() -> float:
    """Return the configured per-command worker timeout in seconds."""
    raw_value = os.environ.get(WORKER_TASK_TIMEOUT_ENV)
    if not raw_value:
        return float(DEFAULT_WORKER_TASK_TIMEOUT_SECONDS)

    try:
        timeout = float(raw_value)
    except ValueError:
        logger.warning(
            f"Invalid {WORKER_TASK_TIMEOUT_ENV}={raw_value!r}; using "
            f"{DEFAULT_WORKER_TASK_TIMEOUT_SECONDS}s"
        )
        return float(DEFAULT_WORKER_TASK_TIMEOUT_SECONDS)

    if timeout <= 0:
        logger.warning(
            f"Invalid {WORKER_TASK_TIMEOUT_ENV}={raw_value!r}; using "
            f"{DEFAULT_WORKER_TASK_TIMEOUT_SECONDS}s"
        )
        return float(DEFAULT_WORKER_TASK_TIMEOUT_SECONDS)

    return timeout


def format_worker_timeout_message(command_full_name: str, timeout_seconds: float) -> str:
    """Build the user-visible timeout error message."""
    minutes = timeout_seconds / 60
    if minutes.is_integer():
        duration = f"{int(minutes)} minutes"
    else:
        duration = f"{timeout_seconds:g} seconds"
    return f"Worker task {command_full_name} timed out after {duration}"


async def execute_command_with_timeout(
    cmd_id: Any,
    command_full_name: str,
    args: dict[str, Any],
    user_context: Optional[dict[str, Any]],
    semaphore: Any,
) -> None:
    """Execute a queued command, cancel it on timeout, and mark it failed."""
    async with semaphore:
        timeout_seconds = get_worker_task_timeout_seconds()
        try:
            await asyncio.wait_for(
                command_service.execute_command(
                    cmd_id,
                    command_full_name,
                    args,
                    user_context,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            error_message = format_worker_timeout_message(
                command_full_name, timeout_seconds
            )
            logger.error(f"{error_message}; marking command {cmd_id} as failed")
            await command_service.update_command_result(
                cmd_id,
                "failed",
                {"success": False, "error_message": error_message},
                error_message,
            )
