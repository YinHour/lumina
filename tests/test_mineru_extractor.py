import subprocess
from pathlib import Path

from open_notebook.content_extractors import mineru
from open_notebook.content_extractors.mineru import extract_mineru, is_mineru_supported


def test_is_mineru_supported_for_document_extensions():
    assert is_mineru_supported("/tmp/example.pdf") is True
    assert is_mineru_supported("/tmp/example.docx") is True
    assert is_mineru_supported("/tmp/example.pptx") is True
    assert is_mineru_supported("/tmp/example.txt") is False
    assert is_mineru_supported("/tmp/example.png") is False


def test_extract_mineru_reads_cli_markdown_output(tmp_path: Path, monkeypatch):
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-1.4")
    captured_env = {}

    def fake_run(args, check, env, stdout, stderr):
        captured_env.update(env)
        output_dir = Path(args[args.index("-o") + 1])
        markdown_dir = output_dir / "paper" / "auto"
        markdown_dir.mkdir(parents=True)
        (markdown_dir / "paper.md").write_text("# MinerU\n\nExtracted.", encoding="utf-8")

    monkeypatch.setattr(mineru.subprocess, "run", fake_run)

    processed = extract_mineru(
        {"file_path": str(source), "title": "", "document_engine": "mineru"}
    )

    assert processed is not None
    assert processed.content == "# MinerU\n\nExtracted."
    assert processed.title == "paper.pdf"
    assert processed.document_engine == "auto"
    assert captured_env["MINERU_TABLE_ENABLE"] == "true"
    assert captured_env["HF_HUB_ENABLE_HF_TRANSFER"] == "1"
    assert captured_env["MINERU_MODEL_SOURCE"] == "modelscope"
    assert captured_env["HF_ENDPOINT"]


def test_extract_mineru_falls_back_for_unsupported_file_type():
    state = {"file_path": "/tmp/example.png", "document_engine": "mineru"}

    processed = extract_mineru(state)

    assert processed is None
    assert state["document_engine"] == "simple"


def test_extract_mineru_falls_back_when_cli_fails(tmp_path: Path, monkeypatch):
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-1.4")

    def fake_run(args, check, env, stdout, stderr):
        raise subprocess.CalledProcessError(returncode=2, cmd=args)

    monkeypatch.setattr(mineru.subprocess, "run", fake_run)
    state = {"file_path": str(source), "document_engine": "mineru"}

    processed = extract_mineru(state)

    assert processed is None
    assert state["document_engine"] == "simple"
