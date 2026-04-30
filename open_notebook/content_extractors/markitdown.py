import os
from pathlib import Path
from typing import Any, Mapping

from content_core.common import ProcessSourceState
from markitdown import MarkItDown

SUPPORTED_MARKITDOWN_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".epub",
    ".html",
    ".htm",
    ".json",
    ".md",
    ".pdf",
    ".ppt",
    ".pptx",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
}


def is_markitdown_supported(file_path: str | os.PathLike[str] | None) -> bool:
    if not file_path:
        return False
    return Path(file_path).suffix.lower() in SUPPORTED_MARKITDOWN_EXTENSIONS


def extract_markitdown(state: Mapping[str, Any]) -> ProcessSourceState:
    file_path = state.get("file_path")
    if not file_path:
        raise ValueError("MarkItDown extraction requires file_path")

    path = Path(str(file_path))
    if not path.exists():
        raise FileNotFoundError(str(path))

    result = MarkItDown().convert(str(path))
    content = result.markdown or result.text_content or ""

    next_state = dict(state)
    next_state["content"] = content
    if not next_state.get("title"):
        next_state["title"] = result.title or path.name

    # content-core's ProcessSourceState currently validates document_engine against
    # auto/simple/docling only, so reset after custom MarkItDown extraction.
    next_state["document_engine"] = "auto"
    return ProcessSourceState(**next_state)


class MarkItDownExtractor:
    name = "markitdown"

    def supports(self, state: dict[str, Any]) -> bool:
        return state.get("document_engine") == self.name

    def extract(self, state: dict[str, Any]) -> ProcessSourceState | None:
        file_path = state.get("file_path")
        if file_path and is_markitdown_supported(file_path):
            return extract_markitdown(state)

        state["document_engine"] = "simple"
        return None
