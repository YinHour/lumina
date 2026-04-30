from types import SimpleNamespace

from api.main import _cors_response_origin


def test_cors_response_origin_uses_allowed_origin(monkeypatch):
    monkeypatch.setenv(
        "OPEN_NOTEBOOK_CORS_ORIGINS",
        "https://notebook.example.com,https://www.notebook.example.com",
    )
    request = SimpleNamespace(headers={"origin": "https://www.notebook.example.com"})

    assert _cors_response_origin(request) == "https://www.notebook.example.com"


def test_cors_response_origin_does_not_echo_untrusted_origin(monkeypatch):
    monkeypatch.setenv("OPEN_NOTEBOOK_CORS_ORIGINS", "https://notebook.example.com")
    request = SimpleNamespace(headers={"origin": "https://evil.example.com"})

    assert _cors_response_origin(request) == "https://notebook.example.com"

