from typing import Any, Dict, List, Optional

from loguru import logger

from commands.lifecycle import command_status_payload, submit_command_job


class CommandService:
    """Generic service layer for command operations"""

    @staticmethod
    async def submit_command_job(
        module_name: str,  # Actually app_name for surreal-commands
        command_name: str,
        command_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit a generic command job for background processing"""
        try:
            return await submit_command_job(
                module_name,  # This is actually the app name (e.g., "open_notebook")
                command_name,  # Command name (e.g., "process_text")
                command_args,  # Input data
                context,
            )

        except Exception as e:
            logger.error(f"Failed to submit command job: {e}")
            raise

    @staticmethod
    async def get_command_status(job_id: str) -> Dict[str, Any]:
        """Get status of any command job"""
        try:
            return await command_status_payload(job_id)
        except Exception as e:
            logger.error(f"Failed to get command status: {e}")
            raise

    @staticmethod
    async def list_command_jobs(
        module_filter: Optional[str] = None,
        command_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List command jobs with optional filtering"""
        # This will be implemented with proper SurrealDB queries
        # For now, return empty list as this is foundation phase
        return []

    @staticmethod
    async def cancel_command_job(job_id: str) -> bool:
        """Cancel a running command job"""
        try:
            # Implementation depends on surreal-commands cancellation support
            # For now, just log the attempt
            logger.info(f"Attempting to cancel job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel command job: {e}")
            raise
