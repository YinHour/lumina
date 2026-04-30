from typing import Any

from loguru import logger

from api.command_service import CommandService
from open_notebook.database.repository import repo_query

SOURCE_PROCESSING_TIMEOUT_MESSAGE = "Processing failed: worker timed out"


async def submit_process_source_command(args: dict[str, Any]) -> str:
    """Submit a source processing command and return its command id."""
    import commands.source_commands  # noqa: F401

    command_id = await CommandService.submit_command_job(
        "open_notebook",
        "process_source",
        args,
    )
    logger.info(f"Submitted async processing command: {command_id}")
    return command_id


async def mark_command_failed(command_id: str, error_message: str) -> None:
    await repo_query(
        "UPDATE $command_id SET status = 'failed', result = $result, error_message = $error_message, updated = time::now()",
        {
            "command_id": command_id,
            "result": {"success": False, "error_message": error_message},
            "error_message": error_message,
        },
    )
