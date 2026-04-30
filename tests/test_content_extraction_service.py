from typing import Any

from content_core.common import ProcessSourceState

from open_notebook.content_extractors import service as extraction_service
from open_notebook.content_extractors.service import ContentExtractionService


class FakeExtractor:
    name = "fake"

    def supports(self, state: dict[str, Any]) -> bool:
        return state.get("document_engine") == self.name

    def extract(self, state: dict[str, Any]) -> ProcessSourceState | None:
        next_state = dict(state)
        next_state["content"] = "extracted by fake plugin"
        next_state["document_engine"] = "auto"
        return ProcessSourceState(**next_state)


def test_sync_extract_uses_registered_extractor_before_default_engine():
    service = ContentExtractionService(extractors=[FakeExtractor()])

    processed = service._sync_extract({"document_engine": "fake"})

    assert processed.content == "extracted by fake plugin"
    assert processed.document_engine == "auto"


def test_sync_extract_falls_back_after_markitdown_rejects_file(monkeypatch):
    async def fake_extract_content(state):
        assert state["document_engine"] == "simple"
        next_state = dict(state)
        next_state["content"] = "default extractor content"
        return ProcessSourceState(**next_state)

    monkeypatch.setattr(extraction_service, "extract_content", fake_extract_content)
    service = ContentExtractionService()
    state = {"file_path": "/tmp/image.png", "document_engine": "markitdown"}

    processed = service._sync_extract(state)

    assert processed.content == "default extractor content"
    assert processed.document_engine == "simple"
