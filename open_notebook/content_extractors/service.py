import asyncio
from typing import Any

from content_core import extract_content
from content_core.common import ProcessSourceState
from loguru import logger

from open_notebook.ai.models import Model, ModelManager
from open_notebook.content_extractors.base import ContentExtractor
from open_notebook.content_extractors.markitdown import MarkItDownExtractor
from open_notebook.content_extractors.mineru import MinerUExtractor
from open_notebook.domain.content_settings import ContentSettings


class ContentExtractionService:
    def __init__(self, extractors: list[ContentExtractor] | None = None):
        self.extractors = extractors or [MarkItDownExtractor(), MinerUExtractor()]

    async def process(self, content_state: dict[str, Any]) -> ProcessSourceState:
        await self.prepare(content_state)
        return await asyncio.to_thread(self._sync_extract, content_state)

    async def prepare(self, content_state: dict[str, Any]) -> None:
        ContentSettings.clear_instance()
        content_settings = await ContentSettings.get_instance()

        content_state["url_engine"] = (
            content_settings.default_content_processing_engine_url or "auto"
        )
        content_state["document_engine"] = (
            content_settings.default_content_processing_engine_doc or "auto"
        )
        content_state["output_format"] = "markdown"

        try:
            model_manager = ModelManager()
            defaults = await model_manager.get_defaults()
            if defaults.default_speech_to_text_model:
                stt_model = await Model.get(defaults.default_speech_to_text_model)
                if stt_model:
                    content_state["audio_provider"] = stt_model.provider
                    content_state["audio_model"] = stt_model.name
                    logger.info(
                        f"Using speech-to-text model: {stt_model.provider}/{stt_model.name}"
                    )
        except Exception as e:
            logger.warning(f"Failed to retrieve speech-to-text model configuration: {e}")

    def _sync_extract(self, state: dict[str, Any]) -> ProcessSourceState:
        for extractor in self.extractors:
            if not extractor.supports(state):
                continue

            logger.info(f"Using {extractor.name} extractor")
            extracted_state = extractor.extract(state)
            if extracted_state:
                return extracted_state

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(extract_content(state))
        finally:
            loop.close()
