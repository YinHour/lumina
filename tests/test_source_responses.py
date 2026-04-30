from api.services.source_responses import source_list_response_from_row


def test_source_list_response_includes_reference_count():
    response = source_list_response_from_row(
        {
            "id": "source:example",
            "title": "Example source",
            "topics": [],
            "asset": None,
            "embedded": False,
            "kg_extracted": False,
            "insights_count": 2,
            "reference_count": 3,
            "created": "2026-04-30T00:00:00Z",
            "updated": "2026-04-30T00:00:00Z",
            "owner_id": "app_user:owner",
            "visibility": "public",
        }
    )

    assert response.reference_count == 3
