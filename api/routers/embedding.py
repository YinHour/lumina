from fastapi import APIRouter, HTTPException
from loguru import logger

from api.command_service import CommandService
from api.models import EmbedRequest, EmbedResponse
from open_notebook.ai.models import model_manager

router = APIRouter()


@router.post("/embed", response_model=EmbedResponse)
async def embed_content(embed_request: EmbedRequest):
    """Embed content for vector search."""
    try:
        # Check if embedding model is available
        if not await model_manager.get_embedding_model():
            raise HTTPException(
                status_code=400,
                detail="No embedding model configured. Please configure one in the Models section.",
            )

        item_id = embed_request.item_id
        item_type = embed_request.item_type.lower()

        # Validate item type
        if item_type not in ["source", "note"]:
            raise HTTPException(
                status_code=400, detail="Item type must be either 'source' or 'note'"
            )

        if item_type == "source":
            command_name = "embed_source"
            command_input = {"source_id": item_id}
        else:
            command_name = "embed_note"
            command_input = {"note_id": item_id}

        command_id = await CommandService.submit_command_job(
            "open_notebook",
            command_name,
            command_input,
        )

        logger.info(f"Submitted {command_name} command: {command_id}")

        return EmbedResponse(
            success=True,
            message="Embedding queued for background processing",
            item_id=item_id,
            item_type=item_type,
            command_id=command_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error embedding {embed_request.item_type} {embed_request.item_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error embedding content: {str(e)}"
        )
