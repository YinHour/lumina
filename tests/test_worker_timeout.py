import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from api import worker_timeout
from api.routers import sources


class DummySemaphore:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_worker_timeout_marks_command_failed(monkeypatch):
    calls = []

    async def never_returns(*args, **kwargs):
        await asyncio.sleep(3600)

    async def record_failure(*args):
        calls.append(args)

    monkeypatch.setenv(worker_timeout.WORKER_TASK_TIMEOUT_ENV, "0.01")
    monkeypatch.setattr(
        worker_timeout.command_service, "execute_command", never_returns
    )
    monkeypatch.setattr(
        worker_timeout.command_service, "update_command_result", record_failure
    )

    await worker_timeout.execute_command_with_timeout(
        "command:abc",
        "open_notebook.process_source",
        {"source_id": "source:1"},
        None,
        DummySemaphore(),
    )

    assert calls
    cmd_id, status, result, error_message = calls[0]
    assert cmd_id == "command:abc"
    assert status == "failed"
    assert result["success"] is False
    assert "timed out" in error_message


def test_source_command_timeout_uses_20_minutes(monkeypatch):
    monkeypatch.setattr(sources, "SOURCE_PROCESSING_TIMEOUT_SECONDS", 20 * 60)
    created_at = datetime.now(timezone.utc) - timedelta(minutes=20, seconds=1)

    assert sources._is_command_timed_out(created_at)


def test_source_command_timeout_does_not_fail_before_20_minutes(monkeypatch):
    monkeypatch.setattr(sources, "SOURCE_PROCESSING_TIMEOUT_SECONDS", 20 * 60)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    created_at = now - timedelta(minutes=19, seconds=59)

    assert not sources._is_command_timed_out(created_at, now=now)


def test_command_status_value_handles_enum_like_values():
    assert sources._command_status_value(SimpleNamespace(value="running")) == "running"
    assert sources._command_status_value("failed") == "failed"
