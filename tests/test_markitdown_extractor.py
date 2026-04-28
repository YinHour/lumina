from pathlib import Path

from open_notebook.content_extractors.markitdown import extract_markitdown, is_markitdown_supported


def test_is_markitdown_supported_for_document_extensions():
    assert is_markitdown_supported("/tmp/example.pdf") is True
    assert is_markitdown_supported("/tmp/example.docx") is True
    assert is_markitdown_supported("/tmp/example.pptx") is True
    assert is_markitdown_supported("/tmp/example.xlsx") is True
    assert is_markitdown_supported("/tmp/example.txt") is True
    assert is_markitdown_supported("/tmp/example.png") is False


def test_extract_markitdown_returns_process_source_state(tmp_path: Path):
    source = tmp_path / "sample.txt"
    source.write_text("# Hello\n\nThis is MarkItDown content.", encoding="utf-8")

    processed = extract_markitdown({"file_path": str(source), "title": ""})

    assert "Hello" in (processed.content or "")
    assert "MarkItDown content" in (processed.content or "")
    assert processed.title == "sample.txt"
    assert processed.document_engine == "auto"


def test_extract_markitdown_raises_for_missing_file():
    missing = "/tmp/lumina-markitdown-missing-file.txt"

    try:
        extract_markitdown({"file_path": missing})
    except FileNotFoundError as exc:
        assert str(exc) == missing
    else:
        raise AssertionError("Expected FileNotFoundError")
