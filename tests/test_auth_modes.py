from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.responses import Response

from api.auth import PasswordAuthMiddleware


async def _call_next(request):
    return Response(status_code=204)


@pytest.mark.asyncio
async def test_auth_mode_none_bypasses_auth(monkeypatch):
    monkeypatch.setenv("OPEN_NOTEBOOK_AUTH_MODE", "none")
    middleware = PasswordAuthMiddleware(app=AsyncMock())
    request = SimpleNamespace(
        url=SimpleNamespace(path="/api/notebooks"),
        method="GET",
        headers={},
        state=SimpleNamespace(),
    )

    response = await middleware.dispatch(request, _call_next)

    assert response.status_code == 204
    assert request.state.user_id is None


@pytest.mark.asyncio
async def test_auth_mode_password_requires_password_env(monkeypatch):
    monkeypatch.setenv("OPEN_NOTEBOOK_AUTH_MODE", "password")
    monkeypatch.delenv("OPEN_NOTEBOOK_PASSWORD", raising=False)
    middleware = PasswordAuthMiddleware(app=AsyncMock())
    request = SimpleNamespace(
        url=SimpleNamespace(path="/api/notebooks"),
        method="GET",
        headers={},
        state=SimpleNamespace(),
    )

    response = await middleware.dispatch(request, _call_next)

    assert response.status_code == 500

