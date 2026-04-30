from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.routers.notebooks import _check_notebook_access, get_notebook_delete_preview
from api.routers.sources import (
    _check_source_access,
    parse_source_form_data,
)


class TestNotebookVisibilityAccess:
    def test_public_notebook_still_requires_owner_for_write_operations(self):
        nb = {"owner_id": "user:owner", "visibility": "public"}

        assert _check_notebook_access(nb, "user:owner", require_owner=True) is True
        assert _check_notebook_access(nb, "user:other", require_owner=True) is False
        assert _check_notebook_access(nb, None, require_owner=True) is False

    def test_public_notebook_allows_read_without_owner(self):
        nb = {"owner_id": "user:owner", "visibility": "public"}

        assert _check_notebook_access(nb, None) is True
        assert _check_notebook_access(nb, "user:other") is True

    @pytest.mark.asyncio
    async def test_delete_preview_requires_notebook_owner_even_when_public(self):
        notebook = SimpleNamespace(
            id="notebook:public",
            name="Public notebook",
            owner_id="user:owner",
            visibility="public",
            get_delete_preview=AsyncMock(
                return_value={
                    "note_count": 1,
                    "exclusive_source_count": 2,
                    "shared_source_count": 3,
                }
            ),
        )
        request = SimpleNamespace(state=SimpleNamespace(user_id="user:other"))

        with patch(
            "api.routers.notebooks.Notebook.get",
            new_callable=AsyncMock,
            return_value=notebook,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_notebook_delete_preview(request, "notebook:public")

        assert exc_info.value.status_code == 403
        notebook.get_delete_preview.assert_not_awaited()


class TestSourceVisibilityAccess:
    def test_source_read_access_allows_public_or_owner_only(self):
        assert _check_source_access("user:owner", "public", None) is True
        assert _check_source_access("user:owner", "private", "user:owner") is True
        assert _check_source_access("user:owner", "private", "user:other") is False
        assert _check_source_access("user:owner", "private", None) is False

    def test_source_read_access_handles_record_id_like_owner_values(self):
        class OwnerId:
            def __str__(self):
                return "user:owner"

        assert _check_source_access(OwnerId(), "private", "user:owner") is True

    def test_parse_source_form_data_preserves_visibility(self):
        source_data, upload_file = parse_source_form_data(
            type="text",
            notebook_id=None,
            notebooks=None,
            url=None,
            content="hello",
            title=None,
            transformations=None,
            embed="false",
            delete_source="false",
            async_processing="false",
            visibility="public",
            file=None,
        )

        assert upload_file is None
        assert source_data.visibility == "public"
