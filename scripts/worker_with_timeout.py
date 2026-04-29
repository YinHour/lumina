#!/usr/bin/env python3
# ruff: noqa: E402, I001
"""Start the Surreal Commands worker with Lumina's per-task timeout enabled."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.worker_timeout import execute_command_with_timeout
from surreal_commands.core import worker as worker_module


def parse_import_modules(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    modules = [item.strip() for item in value.split(",") if item.strip()]
    return modules or None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run surreal-commands-worker with Lumina task timeout support"
    )
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--max-tasks",
        "-m",
        type=int,
        default=worker_module.DEFAULT_MAX_TASKS,
        help="Maximum number of concurrent tasks",
    )
    parser.add_argument(
        "--import-modules",
        "-i",
        default=None,
        help="Comma-separated list of modules to import for command registration",
    )
    args = parser.parse_args()

    # The worker's listener looks up this module global when it schedules tasks.
    # Replacing it here keeps the upstream worker behavior but adds timeout/cancel.
    worker_module.execute_command_with_semaphore = execute_command_with_timeout

    worker_module.run_worker(
        debug=args.debug,
        max_tasks=args.max_tasks,
        import_modules=parse_import_modules(args.import_modules),
    )


if __name__ == "__main__":
    main()
