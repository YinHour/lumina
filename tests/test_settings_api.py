import pytest
from pydantic import ValidationError

from api.models import SettingsUpdate


class TestSettingsApiModels:
    def test_settings_update_accepts_markitdown_document_engine(self):
        settings = SettingsUpdate(default_content_processing_engine_doc="markitdown")

        assert settings.default_content_processing_engine_doc == "markitdown"

    def test_settings_update_rejects_unknown_document_engine(self):
        with pytest.raises(ValidationError):
            SettingsUpdate(default_content_processing_engine_doc="unknown-engine")
