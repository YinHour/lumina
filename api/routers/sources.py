import asyncio
import os
from pathlib import Path
from typing import Any, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, Response
from loguru import logger
from surreal_commands import execute_command_sync, submit_command

from api.command_service import CommandService
from api.models import (
    AssetModel,
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkDeleteResult,
    CreateSourceInsightRequest,
    InsightCreationResponse,
    SourceCreate,
    SourceInsightResponse,
    SourceListResponse,
    SourceResponse,
    SourceStatusResponse,
    SourceUpdate,
)
from commands.source_commands import SourceProcessingInput
from open_notebook.config import UPLOADS_FOLDER
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import Asset, Notebook, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


def _check_source_access(source_owner_id: Optional[str], source_visibility: str, user_id: Optional[str]) -> bool:
    """Check if user can access a source (read-only access).

    Public sources: anyone can access.
    Private sources: only owner can access.
    """
    if source_visibility == "public":
        return True
    if user_id and source_owner_id and str(source_owner_id) == user_id:
        return True
    return False


def _check_source_ownership(source_owner_id: Optional[str], user_id: Optional[str]) -> bool:
    """Check if user owns a source (required for write operations)."""
    if not user_id or not source_owner_id:
        return False
    return str(source_owner_id) == user_id



def generate_unique_filename(original_filename: str, upload_folder: str) -> str:
    """Generate unique filename like Streamlit app (append counter if file exists)."""
    file_path = Path(upload_folder)
    file_path.mkdir(parents=True, exist_ok=True)

    # Strip directory components to prevent path traversal
    safe_filename = os.path.basename(original_filename)
    if not safe_filename:
        raise ValueError("Invalid filename")

    # Split filename and extension
    stem = Path(safe_filename).stem
    suffix = Path(safe_filename).suffix

    # Check if file exists and generate unique name
    counter = 0
    while True:
        if counter == 0:
            new_filename = safe_filename
        else:
            new_filename = f"{stem} ({counter}){suffix}"

        full_path = file_path / new_filename
        # Verify resolved path stays within upload folder
        resolved = full_path.resolve()
        if not str(resolved).startswith(str(file_path.resolve()) + os.sep):
            raise ValueError("Invalid filename: path traversal detected")
        if not resolved.exists():
            return str(resolved)
        counter += 1


async def save_uploaded_file(upload_file: UploadFile) -> str:
    """Save uploaded file to uploads folder and return file path."""
    if not upload_file.filename:
        raise ValueError("No filename provided")

    # Generate unique filename
    file_path = generate_unique_filename(upload_file.filename, UPLOADS_FOLDER)

    try:
        # Save file
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)

        logger.info(f"Saved uploaded file to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        # Clean up partial file if it exists
        if os.path.exists(file_path):
            os.unlink(file_path)
        raise


def parse_source_form_data(
    type: str = Form(...),
    notebook_id: Optional[str] = Form(None),
    notebooks: Optional[str] = Form(None),  # JSON string of notebook IDs
    url: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    transformations: Optional[str] = Form(None),  # JSON string of transformation IDs
    embed: str = Form("false"),  # Accept as string, convert to bool
    delete_source: str = Form("false"),  # Accept as string, convert to bool
    async_processing: str = Form("false"),  # Accept as string, convert to bool
    visibility: str = Form("private"),
    file: Optional[UploadFile] = File(None),
) -> tuple[SourceCreate, Optional[UploadFile]]:
    """Parse form data into SourceCreate model and return upload file separately."""
    import json

    # Convert string booleans to actual booleans
    def str_to_bool(value: str) -> bool:
        return value.lower() in ("true", "1", "yes", "on")

    embed_bool = str_to_bool(embed)
    delete_source_bool = str_to_bool(delete_source)
    async_processing_bool = str_to_bool(async_processing)

    # Parse JSON strings
    notebooks_list = None
    if notebooks:
        try:
            notebooks_list = json.loads(notebooks)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in notebooks field: {notebooks}")
            raise ValueError("Invalid JSON in notebooks field")

    transformations_list = []
    if transformations:
        try:
            transformations_list = json.loads(transformations)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in transformations field: {transformations}")
            raise ValueError("Invalid JSON in transformations field")

    # Create SourceCreate instance
    try:
        source_data = SourceCreate(
            type=type,
            notebook_id=notebook_id,
            notebooks=notebooks_list,
            url=url,
            content=content,
            title=title,
            file_path=None,  # Will be set later if file is uploaded
            transformations=transformations_list,
            embed=embed_bool,
            delete_source=delete_source_bool,
            async_processing=async_processing_bool,
            visibility=visibility,
        )
        pass  # SourceCreate instance created successfully
    except Exception as e:
        logger.error(f"Failed to create SourceCreate instance: {e}")
        raise

    return source_data, file


@router.get("/sources", response_model=List[SourceListResponse])
async def get_sources(
    request: Request,
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
    title_contains: Optional[str] = Query(None, description="Filter sources by title substring"),
    limit: int = Query(
        50, ge=1, le=100, description="Number of sources to return (1-100)"
    ),
    offset: int = Query(0, ge=0, description="Number of sources to skip"),
    sort_by: str = Query(
        "updated", description="Field to sort by (created or updated)"
    ),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
):
    """Get sources with pagination, sorting, and filtering support.

    Returns sources owned by the user (private + public) plus all public sources.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        # Validate sort parameters
        if sort_by not in ["created", "updated"]:
            raise HTTPException(
                status_code=400, detail="sort_by must be 'created' or 'updated'"
            )
        if sort_order.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400, detail="sort_order must be 'asc' or 'desc'"
            )

        # Build ORDER BY clause
        order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
        
        # Build conditions and parameters
        conditions = []
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        # Visibility filter: see own (any visibility) + all public
        if user_id:
            conditions.append("(owner_id = $user_id) OR (visibility = 'public')")
            params["user_id"] = ensure_record_id(user_id)
        else:
            conditions.append("visibility = 'public'")

        if title_contains:
            conditions.append("string::contains(string::lowercase(title), string::lowercase($title_contains))")
            params["title_contains"] = title_contains

        if notebook_id:
            # Verify notebook exists first
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")
                
            conditions.append("id IN (SELECT VALUE in FROM reference WHERE out = $notebook_id)")
            params["notebook_id"] = ensure_record_id(notebook_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Query sources - include command field with FETCH
        query = f"""
            SELECT id, asset, created, title, updated, topics, command, owner_id, visibility,
            (SELECT VALUE count() FROM source_insight WHERE source = $parent.id GROUP ALL)[0].count OR 0 AS insights_count,
            (SELECT VALUE id FROM source_embedding WHERE source = $parent.id LIMIT 1) != [] AS embedded,
            (SELECT VALUE id FROM kg_entity WHERE source_id = type::string($parent.id) LIMIT 1) != [] AS kg_extracted
            FROM source
            {where_clause}
            {order_clause}
            LIMIT $limit START $offset
            FETCH command
        """
        result = await repo_query(query, params)

        # Convert result to response model
        # Command data is already fetched via FETCH command clause
        response_list = []
        for row in result:
            command = row.get("command")
            command_id = None
            status = None
            processing_info = None

            # Extract status from fetched command object (already resolved by FETCH)
            if command and isinstance(command, dict):
                command_id = str(command.get("id")) if command.get("id") else None
                status = command.get("status")
                # Extract execution metadata from nested result structure
                result_data = command.get("result")
                execution_metadata = (
                    result_data.get("execution_metadata", {})
                    if isinstance(result_data, dict)
                    else {}
                )
                processing_info = {
                    "started_at": execution_metadata.get("started_at"),
                    "completed_at": execution_metadata.get("completed_at"),
                    "error": command.get("error_message"),
                }
            elif command:
                # Command exists but FETCH failed to resolve it (broken reference)
                command_id = str(command)
                status = "unknown"

            response_list.append(
                SourceListResponse(
                    id=row["id"],
                    title=row.get("title"),
                    topics=row.get("topics") or [],
                    asset=AssetModel(
                        file_path=row["asset"].get("file_path")
                        if row.get("asset")
                        else None,
                        url=row["asset"].get("url") if row.get("asset") else None,
                    )
                    if row.get("asset")
                    else None,
                    embedded=row.get("embedded", False),
                    embedded_chunks=0,  # Not needed in list view
                    kg_extracted=row.get("kg_extracted", False),
                    insights_count=row.get("insights_count", 0),
                    created=str(row["created"]),
                    updated=str(row["updated"]),
                    # Status fields from fetched command
                    command_id=command_id,
                    status=status,
                    processing_info=processing_info,
                    # Ownership fields
                    owner_id=row.get("owner_id"),
                    visibility=row.get("visibility", "private"),
                )
            )

        return response_list
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching sources: {str(e)}")


@router.get("/sources/public", response_model=List[SourceListResponse])
async def get_public_sources(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
    title_contains: Optional[str] = Query(None, description="Filter sources by title substring"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("updated"),
    sort_order: str = Query("desc"),
):
    """Browse public sources without authentication."""
    try:
        if sort_by not in ["created", "updated"]:
            raise HTTPException(
                status_code=400, detail="sort_by must be 'created' or 'updated'"
            )
        if sort_order.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400, detail="sort_order must be 'asc' or 'desc'"
            )

        order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
        conditions = ["visibility = 'public'"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if title_contains:
            conditions.append("string::contains(string::lowercase(title), string::lowercase($title_contains))")
            params["title_contains"] = title_contains

        if notebook_id:
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")
            conditions.append("id IN (SELECT VALUE in FROM reference WHERE out = $notebook_id)")
            params["notebook_id"] = ensure_record_id(notebook_id)

        where_clause = f"WHERE {' AND '.join(conditions)}"

        query = f"""
            SELECT id, asset, created, title, updated, topics, command, owner_id, visibility,
            (SELECT VALUE count() FROM source_insight WHERE source = $parent.id GROUP ALL)[0].count OR 0 AS insights_count,
            (SELECT VALUE id FROM source_embedding WHERE source = $parent.id LIMIT 1) != [] AS embedded,
            (SELECT VALUE id FROM kg_entity WHERE source_id = type::string($parent.id) LIMIT 1) != [] AS kg_extracted
            FROM source
            {where_clause}
            {order_clause}
            LIMIT $limit START $offset
            FETCH command
        """
        result = await repo_query(query, params)

        response_list = []
        for row in result:
            command = row.get("command")
            command_id = status = processing_info = None
            if command and isinstance(command, dict):
                command_id = str(command.get("id")) if command.get("id") else None
                status = command.get("status")
                result_data = command.get("result")
                execution_metadata = (result_data.get("execution_metadata", {}) if isinstance(result_data, dict) else {})
                processing_info = {
                    "started_at": execution_metadata.get("started_at"),
                    "completed_at": execution_metadata.get("completed_at"),
                    "error": command.get("error_message"),
                }
            elif command:
                command_id = str(command)
                status = "unknown"

            response_list.append(
                SourceListResponse(
                    id=row["id"],
                    title=row.get("title"),
                    topics=row.get("topics") or [],
                    asset=AssetModel(
                        file_path=row["asset"].get("file_path") if row.get("asset") else None,
                        url=row["asset"].get("url") if row.get("asset") else None,
                    ) if row.get("asset") else None,
                    embedded=row.get("embedded", False),
                    embedded_chunks=0,
                    kg_extracted=row.get("kg_extracted", False),
                    insights_count=row.get("insights_count", 0),
                    created=str(row["created"]),
                    updated=str(row["updated"]),
                    command_id=command_id,
                    status=status,
                    processing_info=processing_info,
                    owner_id=row.get("owner_id"),
                    visibility=row.get("visibility", "private"),
                )
            )

        return response_list
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching public sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching public sources: {str(e)}")


@router.post("/sources", response_model=SourceResponse)
async def create_source(
    request: Request,
    form_data: tuple[SourceCreate, Optional[UploadFile]] = Depends(
        parse_source_form_data
    ),
):
    """Create a new source with support for both JSON and multipart form data."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    source_data, upload_file = form_data

    # Initialize file_path before try block so exception handlers can reference it
    file_path = None

    try:
        # Verify all specified notebooks exist (backward compatibility support)
        for notebook_id in source_data.notebooks or []:
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(
                    status_code=404, detail=f"Notebook {notebook_id} not found"
                )

        # Handle file upload if provided
        if upload_file and source_data.type == "upload":
            try:
                file_path = await save_uploaded_file(upload_file)
            except Exception as e:
                logger.error(f"File upload failed: {e}")
                raise HTTPException(
                    status_code=400, detail=f"File upload failed: {str(e)}"
                )

        # Prepare content_state for processing
        content_state: dict[str, Any] = {}

        if source_data.type == "link":
            if not source_data.url:
                raise HTTPException(
                    status_code=400, detail="URL is required for link type"
                )
            content_state["url"] = source_data.url
        elif source_data.type == "upload":
            # Use uploaded file path or provided file_path (backward compatibility)
            final_file_path = file_path or source_data.file_path
            if not final_file_path:
                raise HTTPException(
                    status_code=400,
                    detail="File upload or file_path is required for upload type",
                )
            # Validate file_path is within the uploads directory to prevent LFI
            uploads_resolved = Path(UPLOADS_FOLDER).resolve()
            file_resolved = Path(final_file_path).resolve()
            if not str(file_resolved).startswith(str(uploads_resolved) + os.sep):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path: must be within the uploads directory",
                )
            content_state["file_path"] = final_file_path
            content_state["delete_source"] = source_data.delete_source
        elif source_data.type == "text":
            if not source_data.content:
                raise HTTPException(
                    status_code=400, detail="Content is required for text type"
                )
            content_state["content"] = source_data.content
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source type. Must be link, upload, or text",
            )

        # Validate transformations exist
        transformation_ids = source_data.transformations or []
        for trans_id in transformation_ids:
            transformation = await Transformation.get(trans_id)
            if not transformation:
                raise HTTPException(
                    status_code=404, detail=f"Transformation {trans_id} not found"
                )

        # Pre-flight check: Validate required models exist before queuing
        from open_notebook.ai.models import model_manager
        defaults = await model_manager.get_defaults()

        if source_data.embed and not defaults.default_embedding_model:
            raise HTTPException(
                status_code=400,
                detail="Cannot process source: No default embedding model configured. Please configure one in Settings → Models."
            )

        if transformation_ids and not (defaults.default_transformation_model or defaults.default_chat_model):
            raise HTTPException(
                status_code=400,
                detail="Cannot process source: No default transformation or chat model configured. Please configure one in Settings → Models."
            )

        # process_source also triggers extract_knowledge_graph which needs tools or chat model
        if not (defaults.default_tools_model or defaults.default_chat_model):
            raise HTTPException(
                status_code=400,
                detail="Cannot process source: No default tools or chat model configured for Knowledge Graph extraction. Please configure one in Settings → Models."
            )

        # Branch based on processing mode
        if source_data.async_processing:
            # ASYNC PATH: Create source record first, then queue command
            logger.info("Using async processing path")

            # Create source record with asset - let SurrealDB generate the ID
            # Persist asset before save so it's available for retry if processing fails
            if source_data.type == "link":
                source_asset = Asset(url=source_data.url)
            elif source_data.type == "upload":
                source_asset = Asset(file_path=file_path or source_data.file_path)
            else:
                source_asset = None

            source = Source(
                title=source_data.title or "Processing...",
                topics=[],
                asset=source_asset,
                owner_id=user_id,
                visibility=source_data.visibility,
            )
            await source.save()

            # Add source to notebooks immediately so it appears in the UI
            # The source_graph will skip adding duplicates
            for notebook_id in source_data.notebooks or []:
                await source.add_to_notebook(notebook_id)

            try:
                # Import command modules to ensure they're registered
                import commands.source_commands  # noqa: F401

                # Submit command for background processing
                command_input = SourceProcessingInput(
                    source_id=str(source.id),
                    content_state=content_state,
                    notebook_ids=source_data.notebooks,
                    transformations=transformation_ids,
                    embed=source_data.embed,
                )

                command_id = await CommandService.submit_command_job(
                    "open_notebook",  # app name
                    "process_source",  # command name
                    command_input.model_dump(),
                )

                logger.info(f"Submitted async processing command: {command_id}")

                # Update source with command reference immediately
                # command_id already includes 'command:' prefix
                source.command = ensure_record_id(command_id)
                await source.save()

                # Return source with command info
                return SourceResponse(
                    id=source.id or "",
                    title=source.title,
                    topics=source.topics or [],
                    asset=None,  # Will be populated after processing
                    full_text=None,  # Will be populated after processing
                    embedded=False,  # Will be updated after processing
                    embedded_chunks=0,
                    kg_extracted=False,
                    created=str(source.created),
                    updated=str(source.updated),
                    command_id=command_id,
                    status="new",
                    processing_info={"async": True, "queued": True},
                    owner_id=source.owner_id,
                    visibility=source.visibility,
                )

            except Exception as e:
                logger.error(f"Failed to submit async processing command: {e}")
                # Clean up source record on command submission failure
                try:
                    await source.delete()
                except Exception:
                    pass
                # Clean up uploaded file if we created it
                if file_path and upload_file:
                    try:
                        os.unlink(file_path)
                    except Exception:
                        pass
                raise HTTPException(
                    status_code=500, detail=f"Failed to queue processing: {str(e)}"
                )

        else:
            # SYNC PATH: Execute synchronously using execute_command_sync
            logger.info("Using sync processing path")

            try:
                # Import command modules to ensure they're registered
                import commands.source_commands  # noqa: F401

                # Create source record - let SurrealDB generate the ID
                source = Source(
                    title=source_data.title or "Processing...",
                    topics=[],
                    owner_id=user_id,
                    visibility=source_data.visibility,
                )
                await source.save()

                # Add source to notebooks immediately so it appears in the UI
                # The source_graph will skip adding duplicates
                for notebook_id in source_data.notebooks or []:
                    await source.add_to_notebook(notebook_id)

                # Execute command synchronously
                command_input = SourceProcessingInput(
                    source_id=str(source.id),
                    content_state=content_state,
                    notebook_ids=source_data.notebooks,
                    transformations=transformation_ids,
                    embed=source_data.embed,
                )

                # Run in thread pool to avoid blocking the event loop
                # execute_command_sync uses asyncio.run() internally which can't
                # be called from an already-running event loop (FastAPI)
                result = await asyncio.to_thread(
                    execute_command_sync,
                    "open_notebook",  # app name
                    "process_source",  # command name
                    command_input.model_dump(),
                    timeout=300,  # 5 minute timeout for sync processing
                )

                if not result.is_success():
                    logger.error(f"Sync processing failed: {result.error_message}")
                    # Clean up source record
                    try:
                        await source.delete()
                    except Exception:
                        pass
                    # Clean up uploaded file if we created it
                    if file_path and upload_file:
                        try:
                            os.unlink(file_path)
                        except Exception:
                            pass
                    raise HTTPException(
                        status_code=500,
                        detail=f"Processing failed: {result.error_message}",
                    )

                # Get the processed source
                if not source.id:
                    raise HTTPException(status_code=500, detail="Source ID is missing")
                processed_source = await Source.get(source.id)
                if not processed_source:
                    raise HTTPException(
                        status_code=500, detail="Processed source not found"
                    )

                embedded_chunks = await processed_source.get_embedded_chunks()
                kg_extracted = await processed_source.has_knowledge_graph()
                return SourceResponse(
                    id=processed_source.id or "",
                    title=processed_source.title,
                    topics=processed_source.topics or [],
                    asset=AssetModel(
                        file_path=processed_source.asset.file_path
                        if processed_source.asset
                        else None,
                        url=processed_source.asset.url
                        if processed_source.asset
                        else None,
                    )
                    if processed_source.asset
                    else None,
                    full_text=processed_source.full_text,
                    embedded=embedded_chunks > 0,
                    embedded_chunks=embedded_chunks,
                    kg_extracted=kg_extracted,
                    created=str(processed_source.created),
                    updated=str(processed_source.updated),
                    # No command_id or status for sync processing (legacy behavior)
                    owner_id=processed_source.owner_id,
                    visibility=processed_source.visibility,
                )

            except Exception as e:
                logger.error(f"Sync processing failed: {e}")
                # Clean up uploaded file if we created it
                if file_path and upload_file:
                    try:
                        os.unlink(file_path)
                    except Exception:
                        pass
                raise

    except HTTPException:
        # Clean up uploaded file on HTTP exceptions if we created it
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise
    except InvalidInputError as e:
        # Clean up uploaded file on validation errors if we created it
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating source: {str(e)}")
        # Clean up uploaded file on unexpected errors if we created it
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Error creating source: {str(e)}")


@router.post("/sources/json", response_model=SourceResponse)
async def create_source_json(request: Request, source_data: SourceCreate):
    """Create a new source using JSON payload (legacy endpoint for backward compatibility)."""
    # Convert to form data format and call main endpoint while preserving request.user_id.
    form_data = (source_data, None)
    return await create_source(request, form_data)


async def _resolve_source_file(source_id: str) -> tuple[str, str]:
    source = await Source.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    file_path = source.asset.file_path if source.asset else None
    if not file_path:
        raise HTTPException(status_code=404, detail="Source has no file to download")

    safe_root = os.path.realpath(UPLOADS_FOLDER)
    resolved_path = os.path.realpath(file_path)

    if not resolved_path.startswith(safe_root):
        logger.warning(
            f"Blocked download outside uploads directory for source {source_id}: {resolved_path}"
        )
        raise HTTPException(status_code=403, detail="Access to file denied")

    if not os.path.exists(resolved_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    filename = os.path.basename(resolved_path)
    return resolved_path, filename


def _is_source_file_available(source: Source) -> Optional[bool]:
    if not source or not source.asset or not source.asset.file_path:
        return None

    file_path = source.asset.file_path
    safe_root = os.path.realpath(UPLOADS_FOLDER)
    resolved_path = os.path.realpath(file_path)

    if not resolved_path.startswith(safe_root):
        return False

    return os.path.exists(resolved_path)


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(request: Request, source_id: str):
    """Get a specific source by ID. Requires ownership (private) or public."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Access check
        if not _check_source_access(source.owner_id, source.visibility, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get status information if command exists
        status = None
        processing_info = None
        if source.command:
            try:
                status = await source.get_status()
                processing_info = await source.get_processing_progress()
            except Exception as e:
                logger.warning(f"Failed to get status for source {source_id}: {e}")
                status = "unknown"

        embedded_chunks = await source.get_embedded_chunks()
        kg_extracted = await source.has_knowledge_graph()

        # Get associated notebooks
        notebooks_query = await repo_query(
            "SELECT VALUE out FROM reference WHERE in = $source_id",
            {"source_id": ensure_record_id(source.id or source_id)},
        )
        notebook_ids = (
            [str(nb_id) for nb_id in notebooks_query] if notebooks_query else []
        )

        return SourceResponse(
            id=source.id or "",
            title=source.title,
            topics=source.topics or [],
            asset=AssetModel(
                file_path=source.asset.file_path if source.asset else None,
                url=source.asset.url if source.asset else None,
            )
            if source.asset
            else None,
            full_text=source.full_text,
            embedded=embedded_chunks > 0,
            embedded_chunks=embedded_chunks,
            kg_extracted=kg_extracted,
            file_available=_is_source_file_available(source),
            created=str(source.created),
            updated=str(source.updated),
            # Status fields
            command_id=str(source.command) if source.command else None,
            status=status,
            processing_info=processing_info,
            # Notebook associations
            notebooks=notebook_ids,
            owner_id=source.owner_id,
            visibility=source.visibility,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching source: {str(e)}")


@router.head("/sources/{source_id}/download")
async def check_source_file(request: Request, source_id: str):
    """Check if a source has a downloadable file. Requires access."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not _check_source_access(source.owner_id, source.visibility, user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        await _resolve_source_file(source_id)
        return Response(status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking file for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify file")


@router.patch("/sources/{source_id}/visibility")
async def update_source_visibility(request: Request, source_id: str):
    """Make a private source public. One-way only — cannot revert to private.

    Requires ownership. Returns the updated source.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        if not _check_source_ownership(source.owner_id, user_id):
            raise HTTPException(status_code=403, detail="Access denied — you do not own this source")

        if source.visibility == "public":
            raise HTTPException(
                status_code=400,
                detail="Source is already public. Making a source private is not supported."
            )

        source.visibility = "public"
        await source.save()

        # Re-fetch with full data (same query as get_sources)
        result = await repo_query("""
            SELECT id, asset, created, title, updated, topics, command, owner_id, visibility,
            (SELECT VALUE count() FROM source_insight WHERE source = $parent.id GROUP ALL)[0].count OR 0 AS insights_count,
            (SELECT VALUE id FROM source_embedding WHERE source = $parent.id LIMIT 1) != [] AS embedded,
            (SELECT VALUE id FROM kg_entity WHERE source_id = type::string($parent.id) LIMIT 1) != [] AS kg_extracted
            FROM source WHERE id = $sid
            FETCH command
        """, {"sid": ensure_record_id(source_id)})

        if not result:
            raise HTTPException(status_code=404, detail="Source not found after update")

        row = result[0]
        command = row.get("command")
        command_id = None
        status = None
        processing_info = None
        if command and isinstance(command, dict):
            command_id = str(command.get("id")) if command.get("id") else None
            status = command.get("status")
            result_data = command.get("result")
            execution_metadata = result_data.get("execution_metadata", {}) if isinstance(result_data, dict) else {}
            processing_info = {
                "started_at": execution_metadata.get("started_at"),
                "completed_at": execution_metadata.get("completed_at"),
                "error": command.get("error_message"),
            }

        return SourceListResponse(
            id=row["id"],
            title=row.get("title"),
            topics=row.get("topics") or [],
            asset=AssetModel(
                file_path=row["asset"].get("file_path") if row.get("asset") else None,
                url=row["asset"].get("url") if row.get("asset") else None,
            ) if row.get("asset") else None,
            embedded=row.get("embedded", False),
            embedded_chunks=0,
            kg_extracted=row.get("kg_extracted", False),
            insights_count=row.get("insights_count", 0),
            created=str(row["created"]),
            updated=str(row["updated"]),
            command_id=command_id,
            status=status,
            processing_info=processing_info,
            owner_id=row.get("owner_id"),
            visibility=row.get("visibility", "private"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating visibility for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating visibility: {str(e)}")


@router.get("/sources/{source_id}/download")
async def download_source_file(request: Request, source_id: str):
    """Download the original file associated with an uploaded source. Requires access."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not _check_source_access(source.owner_id, source.visibility, user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        resolved_path, filename = await _resolve_source_file(source_id)
        return FileResponse(
            path=resolved_path,
            filename=filename,
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download source file")


@router.get("/sources/{source_id}/status", response_model=SourceStatusResponse)
async def get_source_status(request: Request, source_id: str):
    """Get processing status for a source. Requires access."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        # First, verify source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Access check
        if not _check_source_access(source.owner_id, source.visibility, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if this is a legacy source (no command)
        if not source.command:
            return SourceStatusResponse(
                status=None,
                message="Legacy source (completed before async processing)",
                processing_info=None,
                command_id=None,
            )

        # Get command status and processing info
        try:
            status = await source.get_status()
            processing_info = await source.get_processing_progress()

            # Generate descriptive message based on status
            if status == "completed":
                message = "Source processing completed successfully"
            elif status == "failed":
                message = "Source processing failed"
            elif status == "running":
                message = "Source processing in progress"
            elif status == "queued":
                message = "Source processing queued"
            elif status == "unknown":
                message = "Source processing status unknown"
            else:
                message = f"Source processing status: {status}"

            return SourceStatusResponse(
                status=status,
                message=message,
                processing_info=processing_info,
                command_id=str(source.command) if source.command else None,
            )

        except Exception as e:
            logger.warning(f"Failed to get status for source {source_id}: {e}")
            return SourceStatusResponse(
                status="unknown",
                message="Failed to retrieve processing status",
                processing_info=None,
                command_id=str(source.command) if source.command else None,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching status for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching source status: {str(e)}"
        )


@router.put("/sources/{source_id}", response_model=SourceResponse)
async def update_source(request: Request, source_id: str, source_update: SourceUpdate):
    """Update a source. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Ownership check
        if not _check_source_ownership(source.owner_id, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Update only provided fields
        if source_update.title is not None:
            source.title = source_update.title
        if source_update.topics is not None:
            source.topics = source_update.topics
        if source_update.visibility is not None:
            source.visibility = source_update.visibility

        await source.save()

        embedded_chunks = await source.get_embedded_chunks()
        kg_extracted = await source.has_knowledge_graph()
        return SourceResponse(
            id=source.id or "",
            title=source.title,
            topics=source.topics or [],
            asset=AssetModel(
                file_path=source.asset.file_path if source.asset else None,
                url=source.asset.url if source.asset else None,
            )
            if source.asset
            else None,
            full_text=source.full_text,
            embedded=embedded_chunks > 0,
            embedded_chunks=embedded_chunks,
            kg_extracted=kg_extracted,
            created=str(source.created),
            updated=str(source.updated),
            owner_id=source.owner_id,
            visibility=source.visibility,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating source: {str(e)}")


@router.post("/sources/{source_id}/retry", response_model=SourceResponse)
async def retry_source_processing(request: Request, source_id: str):
    """Retry processing for a failed or stuck source. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        # First, verify source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Ownership check
        if not _check_source_ownership(source.owner_id, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if source already has a running command
        if source.command:
            try:
                status = await source.get_status()
                if status in ["running", "queued"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Source is already processing. Cannot retry while processing is active.",
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to check current status for source {source_id}: {e}"
                )
                # Continue with retry if we can't check status

        # Get notebooks that this source belongs to
        query = "SELECT notebook FROM reference WHERE source = $source_id"
        references = await repo_query(query, {"source_id": source_id})
        notebook_ids = [str(ref["notebook"]) for ref in references]

        if not notebook_ids:
            raise HTTPException(
                status_code=400, detail="Source is not associated with any notebooks"
            )

        # Prepare content_state based on source asset
        content_state = {}
        if source.asset:
            if source.asset.file_path:
                content_state = {
                    "file_path": source.asset.file_path,
                    "delete_source": False,  # Don't delete on retry
                }
            elif source.asset.url:
                content_state = {"url": source.asset.url}
            else:
                raise HTTPException(
                    status_code=400, detail="Source asset has no file_path or url"
                )
        else:
            # Check if it's a text source by trying to get full_text
            if source.full_text:
                content_state = {"content": source.full_text}
            else:
                raise HTTPException(
                    status_code=400, detail="Cannot determine source content for retry"
                )

        try:
            # Import command modules to ensure they're registered
            import commands.source_commands  # noqa: F401

            # Submit new command for background processing
            command_input = SourceProcessingInput(
                source_id=str(source.id),
                content_state=content_state,
                notebook_ids=notebook_ids,
                transformations=[],  # Use default transformations on retry
                embed=True,  # Always embed on retry
            )

            command_id = await CommandService.submit_command_job(
                "open_notebook",  # app name
                "process_source",  # command name
                command_input.model_dump(),
            )

            logger.info(
                f"Submitted retry processing command: {command_id} for source {source_id}"
            )

            # Update source with new command ID
            source.command = ensure_record_id(f"command:{command_id}")
            await source.save()

            # Get current embedded chunks count
            embedded_chunks = await source.get_embedded_chunks()
            kg_extracted = await source.has_knowledge_graph()

            # Return updated source response
            return SourceResponse(
                id=source.id or "",
                title=source.title,
                topics=source.topics or [],
                asset=AssetModel(
                    file_path=source.asset.file_path if source.asset else None,
                    url=source.asset.url if source.asset else None,
                )
                if source.asset
                else None,
                full_text=source.full_text,
                embedded=embedded_chunks > 0,
                embedded_chunks=embedded_chunks,
                kg_extracted=kg_extracted,
                created=str(source.created),
                updated=str(source.updated),
                command_id=command_id,
                status="queued",
                processing_info={"retry": True, "queued": True},
                owner_id=source.owner_id,
                visibility=source.visibility,
            )

        except Exception as e:
            logger.error(
                f"Failed to submit retry processing command for source {source_id}: {e}"
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to queue retry processing: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying source processing for {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrying source processing: {str(e)}"
        )


@router.delete("/sources/{source_id}")
async def delete_source(request: Request, source_id: str):
    """Delete a source. Requires ownership.

    Public sources that are referenced by notebooks cannot be deleted.
    Remove the source from all notebooks first.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Ownership check
        if not _check_source_ownership(source.owner_id, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        await source.delete()

        return {"message": "Source deleted successfully"}
    except InvalidInputError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting source: {str(e)}")


@router.post("/sources/{source_id}/extract-kg")
async def extract_knowledge_graph(request: Request, source_id: str):
    """Trigger knowledge graph extraction for a source. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        if not _check_source_ownership(source.owner_id, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        if not source.full_text or not source.full_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Source has no text content to extract knowledge graph from",
            )

        command_id = submit_command(
            "open_notebook",
            "extract_knowledge_graph",
            {"source_id": source_id},
        )

        logger.info(
            f"Knowledge graph extraction queued for source {source_id}: {command_id}"
        )

        return {
            "success": True,
            "source_id": source_id,
            "command_id": str(command_id),
            "message": "Knowledge graph extraction queued",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error triggering KG extraction for source {source_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error triggering KG extraction: {str(e)}"
        )


@router.post("/sources/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_sources(request: Request, body: BulkDeleteRequest):
    """Delete multiple sources at once. Only deletes sources the user owns.

    Public sources that are referenced by notebooks will be skipped
    with an error in the per-source results.

    Returns a per-source breakdown of which were deleted and which failed (with reasons).
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    results: list[BulkDeleteResult] = []
    deleted_count = 0
    failed_count = 0

    for source_id in body.source_ids:
        try:
            source = await Source.get(source_id)
            if not source:
                results.append(BulkDeleteResult(
                    source_id=source_id, title="(not found)", deleted=False,
                    error="Source not found"
                ))
                failed_count += 1
                continue

            title = source.title or "(untitled)"

            if not _check_source_ownership(source.owner_id, user_id):
                results.append(BulkDeleteResult(
                    source_id=source_id, title=title, deleted=False,
                    error="Access denied — you do not own this source"
                ))
                failed_count += 1
                continue

            await source.delete()
            results.append(BulkDeleteResult(
                source_id=source_id, title=title, deleted=True
            ))
            deleted_count += 1

        except InvalidInputError as e:
            results.append(BulkDeleteResult(
                source_id=source_id, title=title, deleted=False,
                error=str(e)
            ))
            failed_count += 1
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in bulk delete for source {source_id}: {e}")
            results.append(BulkDeleteResult(
                source_id=source_id, title="(error)", deleted=False,
                error=str(e)
            ))
            failed_count += 1

    return BulkDeleteResponse(
        total_requested=len(body.source_ids),
        deleted_count=deleted_count,
        failed_count=failed_count,
        results=results,
    )


@router.get("/sources/{source_id}/insights", response_model=List[SourceInsightResponse])
async def get_source_insights(request: Request, source_id: str):
    """Get all insights for a specific source. Requires access."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Access check
        if not _check_source_access(source.owner_id, source.visibility, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        insights = await source.get_insights()
        return [
            SourceInsightResponse(
                id=insight.id or "",
                source_id=source_id,
                insight_type=insight.insight_type,
                content=insight.content,
                created=str(insight.created),
                updated=str(insight.updated),
            )
            for insight in insights
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching insights for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching insights: {str(e)}"
        )


@router.post(
    "/sources/{source_id}/insights",
    response_model=InsightCreationResponse,
    status_code=202,
)
async def create_source_insight(http_request: Request, source_id: str, request: CreateSourceInsightRequest):
    """Start insight generation for a source by running a transformation. Requires ownership."""
    user_id: Optional[str] = getattr(http_request.state, "user_id", None)
    try:
        # Validate source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Ownership check
        if not _check_source_ownership(source.owner_id, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Validate transformation exists
        transformation = await Transformation.get(request.transformation_id)
        if not transformation:
            raise HTTPException(status_code=404, detail="Transformation not found")

        # Submit transformation as background job (fire-and-forget)
        command_id = submit_command(
            "open_notebook",
            "run_transformation",
            {
                "source_id": source_id,
                "transformation_id": request.transformation_id,
            },
        )
        logger.info(
            f"Submitted run_transformation command {command_id} for source {source_id}"
        )

        # Return immediately with command_id for status tracking
        return InsightCreationResponse(
            status="pending",
            message="Insight generation started",
            source_id=source_id,
            transformation_id=request.transformation_id,
            command_id=str(command_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting insight generation for source {source_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error starting insight generation: {str(e)}"
        )
