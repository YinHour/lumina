import os
import subprocess
import sys
import tempfile
from typing import Any, Optional

from content_core.common import ProcessSourceState
from loguru import logger

MINERU_SUPPORTED_EXTENSIONS = (".pdf", ".ppt", ".pptx", ".doc", ".docx")


def is_mineru_supported(file_path: str) -> bool:
    return file_path.lower().endswith(MINERU_SUPPORTED_EXTENSIONS)


def extract_mineru(state: dict[str, Any]) -> Optional[ProcessSourceState]:
    """Extract document content with MinerU, returning None to trigger fallback."""
    file_path = state.get("file_path")
    if not file_path or not is_mineru_supported(file_path):
        logger.warning(
            "MinerU does not support this file type. Falling back to simple engine."
        )
        state["document_engine"] = "simple"
        return None

    logger.info(f"Using MinerU to extract content from {file_path}")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            if "HF_ENDPOINT" not in env:
                env["HF_ENDPOINT"] = "https://hf-mirror.com"
            env["MINERU_TABLE_ENABLE"] = "true"
            env["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
            env["MINERU_MODEL_SOURCE"] = "modelscope"

            try:
                logger.info(
                    "MinerU may need to download models on first run. Streaming output to console..."
                )
                subprocess.run(
                    [
                        "mineru",
                        "-p",
                        file_path,
                        "-o",
                        temp_dir,
                        "-m",
                        "auto",
                        "--backend",
                        "pipeline",
                    ],
                    check=True,
                    env=env,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"MinerU extraction process failed with exit code {e.returncode}"
                )
                raise

            md_content = _find_mineru_markdown(temp_dir, file_path)
            if not md_content:
                logger.warning(
                    "MinerU failed to produce markdown output. Falling back to simple engine."
                )
                state["document_engine"] = "simple"
                return None

            logger.info(f"Successfully extracted {len(md_content)} chars using MinerU.")
            state["content"] = md_content
            if not state.get("title") and state.get("file_path"):
                state["title"] = os.path.basename(state["file_path"])
            state["document_engine"] = "auto"
            return ProcessSourceState(**state)
    except Exception as e:
        logger.error(f"MinerU extraction failed: {e}. Falling back to simple engine.")
        state["document_engine"] = "simple"
        return None


def _find_mineru_markdown(temp_dir: str, file_path: str) -> str:
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    out_dir = os.path.join(temp_dir, base_name, "auto")

    if os.path.exists(out_dir):
        return _first_markdown_file(out_dir)

    fallback_dir = os.path.join(temp_dir, base_name)
    if os.path.exists(fallback_dir):
        return _first_markdown_file(fallback_dir)

    return ""


def _first_markdown_file(directory: str) -> str:
    for filename in os.listdir(directory):
        if filename.endswith(".md"):
            with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
                return f.read()
    return ""


class MinerUExtractor:
    name = "mineru"

    def supports(self, state: dict[str, Any]) -> bool:
        return state.get("document_engine") == self.name

    def extract(self, state: dict[str, Any]) -> Optional[ProcessSourceState]:
        return extract_mineru(state)
