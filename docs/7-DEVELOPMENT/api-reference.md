# API Reference

Complete REST API for Open Notebook. All endpoints are served from the API backend (default: `http://localhost:5055`).

**Base URL**: `http://localhost:5055` (development) or environment-specific production URL

**Interactive Docs**: Use FastAPI's built-in Swagger UI at `http://localhost:5055/docs` for live testing and exploration. This is the primary reference for all endpoints, request/response schemas, and real-time testing.

---

## Quick Start

### 1. Authentication

Preferred current flow: database-backed username/password login that returns a JWT.

```bash
# Login first
curl -X POST http://localhost:5055/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Then use the returned token
curl http://localhost:5055/api/notebooks \
  -H "Authorization: Bearer <jwt-token>"
```

Legacy compatibility still exists: if `OPEN_NOTEBOOK_PASSWORD` is set, the middleware accepts `Authorization: Bearer <password>` instead of a JWT.

### 2. Base API Flow

Most operations follow this pattern:
1. Create a **Notebook** (container for research)
2. Add **Sources** (PDFs, URLs, text)
3. Query via **Chat** or **Search**
4. View results and **Notes**

### 3. Testing Endpoints

Instead of memorizing endpoints, use the interactive API docs:
- Navigate to `http://localhost:5055/docs`
- Try requests directly in the browser
- See request/response schemas in real-time
- Test with your own data

---

## API Endpoints Overview

### Main Resource Types

**Notebooks** - Research projects containing sources and notes
- `GET/POST /notebooks` - List and create
- `GET/PUT/DELETE /notebooks/{id}` - Read, update, delete
- `PATCH /notebooks/{id}/visibility` - Make notebook public (one-way)

**Sources** - Content items (PDFs, URLs, text)
- `GET/POST /sources` - List and add content
- `GET /sources/{id}` - Fetch source details
- `DELETE /sources/{id}` - Delete source (public + referenced → 409)
- `POST /sources/bulk-delete` - Delete multiple sources at once
- `PATCH /sources/{id}/visibility` - Make source public (one-way)
- `POST /sources/{id}/retry` - Retry failed processing
- `GET /sources/{id}/download` - Download original file

**Notes** - User-created or AI-generated research notes
- `GET/POST /notes` - List and create
- `GET/PUT/DELETE /notes/{id}` - Read, update, delete

**Chat** - Conversational AI interface
- `GET/POST /chat/sessions` - Manage chat sessions
- `POST /chat/execute` - Send message and get response
- `POST /chat/context/build` - Prepare context for chat

**Search** - Find content by text or semantic similarity
- `POST /search` - Full-text or vector search
- `POST /ask` - Ask a question (search + synthesize)

**Transformations** - Custom prompts for extracting insights
- `GET/POST /transformations` - Create custom extraction rules
- `POST /sources/{id}/insights` - Apply transformation to source

**Models** - Configure AI providers
- `GET /models` - Available models
- `GET /models/defaults` - Current defaults
- `POST /models/config` - Set defaults

**Credentials** - Manage AI provider credentials
- `GET/POST /credentials` - List and create credentials
- `GET/PUT/DELETE /credentials/{id}` - CRUD operations
- `POST /credentials/{id}/test` - Test connection
- `POST /credentials/{id}/discover` - Discover models from provider
- `POST /credentials/{id}/register-models` - Register discovered models
- `GET /credentials/status` - Provider status overview
- `GET /credentials/env-status` - Environment variable status
- `POST /credentials/migrate-from-env` - Migrate env vars to credentials

**Health & Status**
- `GET /health` - Health check
- `GET /commands/{id}` - Track async operations

**Public Browsing** (no auth required)
- `GET /api/public/notebooks` - List all public notebooks
- `GET /api/public/sources` - List all public sources

---

## Authentication

### Current (Development)

The API supports two auth modes:

1. Preferred: database users + JWT tokens
2. Legacy compatibility: `OPEN_NOTEBOOK_PASSWORD` env var

Recommended flow:

```bash
# Check auth mode
curl http://localhost:5055/api/auth/status

# Login and get JWT
curl -X POST http://localhost:5055/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Use JWT for protected endpoints
curl -H "Authorization: Bearer <jwt-token>" \
  http://localhost:5055/api/notebooks
```

If your deployment still uses legacy mode, send the password itself as the Bearer credential.

> **📖 See [Security Configuration](../5-CONFIGURATION/security.md)** for complete authentication setup, API examples, and production hardening.

### Production

Current production-friendly baseline is the built-in username/password + JWT flow, optionally placed behind a reverse proxy.

For stronger enterprise setups, consider adding:
- OAuth 2.0 / OIDC at the proxy layer
- SSO in front of the application
- Network restrictions and HTTPS termination

See [Security Configuration](../5-CONFIGURATION/security.md) for deployment guidance.

---

## Common Patterns

### Pagination

```bash
# List sources with limit/offset
curl 'http://localhost:5055/sources?limit=20&offset=10'
```

### Filtering & Sorting

```bash
# Filter by notebook, sort by date
curl 'http://localhost:5055/sources?notebook_id=notebook:abc&sort_by=created&sort_order=asc'
```

### Async Operations

Some operations (source processing, podcast generation) return immediately with a command ID:

```bash
# Submit async operation
curl -X POST http://localhost:5055/sources -F async_processing=true
# Response: {"id": "source:src001", "command_id": "command:cmd123"}

# Poll status
curl http://localhost:5055/commands/command:cmd123
```

### Streaming Responses

The `/ask` endpoint streams responses as Server-Sent Events:

```bash
curl -N 'http://localhost:5055/ask' \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?"}'

# Outputs: data: {"type":"strategy",...}
#          data: {"type":"answer",...}
#          data: {"type":"final_answer",...}
```

### Multipart File Upload

```bash
curl -X POST http://localhost:5055/sources \
  -F "type=upload" \
  -F "notebook_id=notebook:abc" \
  -F "file=@document.pdf"
```

---

## Error Handling

All errors return JSON with status code:

```json
{"detail": "Notebook not found"}
```

### Common Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Operation completed |
| 400 | Bad Request | Invalid input / already public |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Cannot delete public source with active references |
| 500 | Server Error | Database/processing error |

---

## Visibility API

Control whether notebooks and sources are private (default) or publicly accessible.

### Make a Notebook Public

Visibility can only change from `private` → `public`. This is irreversible.

```bash
curl -X PATCH http://localhost:5055/api/notebooks/notebook:abc/visibility \
  -H "Authorization: Bearer $TOKEN"
```

Response: `200 OK` — returns the updated notebook.

Errors:
- `400 Bad Request` — Notebook is already public
- `403 Forbidden` — You don't own this notebook
- `404 Not Found` — Notebook doesn't exist

### Make a Source Public

Same one-way toggle as notebooks.

```bash
curl -X PATCH http://localhost:5055/api/sources/source:xyz/visibility \
  -H "Authorization: Bearer $TOKEN"
```

Errors:
- `400 Bad Request` — Source is already public
- `403 Forbidden` — You don't own this source
- `404 Not Found` — Source doesn't exist

### Source Deletion Constraint

A public source that is referenced by notebooks **cannot** be deleted:

```bash
curl -X DELETE http://localhost:5055/api/sources/source:xyz \
  -H "Authorization: Bearer $TOKEN"
```

| Scenario | Response |
|----------|----------|
| Private source | `200 OK` — Deleted |
| Public source, 0 references | `200 OK` — Deleted |
| Public source, N references | `409 Conflict` — "Cannot delete public source: it is referenced by N notebook(s)" |

To delete a referenced public source, first remove it from all referencing notebooks using `DELETE /api/notebooks/{notebook_id}/sources/{source_id}`.

### Bulk Delete Sources

```bash
curl -X POST http://localhost:5055/api/sources/bulk-delete \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_ids": ["source:abc", "source:xyz"]}'
```

Returns per-source results. Public sources with references are skipped with an error message in the results array.

---

## Public Browsing API

No authentication required. Public endpoints let anyone browse publicly shared content.

### List Public Notebooks

```bash
curl http://localhost:5055/api/public/notebooks?limit=20&offset=0
```

Returns notebooks with `visibility = 'public'`, including owner username, source count, and note count.

### List Public Sources

```bash
curl http://localhost:5055/api/public/sources?limit=20&offset=0
```

Returns sources with `visibility = 'public'`, including owner info and processing status.

### Accessing Public Content

Public notebooks/sources can also be fetched directly by ID without authentication if they're public:

```bash
# Works without auth for public content
curl http://localhost:5055/api/notebooks/notebook:abc
curl http://localhost:5055/api/sources/source:xyz

# Returns 404 for private content (same as "not found" to avoid leaking existence)
```

---

## Tips for Developers

1. **Start with interactive docs** (`http://localhost:5055/docs`) - this is the definitive reference
2. **Enable logging** for debugging (check API logs: `docker logs`)
3. **Streaming endpoints** require special handling (Server-Sent Events, not standard JSON)
4. **Async operations** return immediately; always poll status before assuming completion
5. **Vector search** requires embedding model configured (check `/models`)
6. **Model overrides** are per-request; set in body, not config
7. **CORS enabled** in development; configure for production

---

## Learning Path

1. **Authentication**: Call `/api/auth/status` then `/api/auth/login` to obtain a JWT
2. **Create a notebook**: `POST /notebooks` with name and description
3. **Add a source**: `POST /sources` with file, URL, or text
4. **Query your content**: `POST /chat/execute` to ask questions
5. **Explore advanced features**: Search, transformations, streaming

---

## Production Considerations

- Decide whether to use built-in JWT auth only or layer OAuth/OIDC in front via reverse proxy
- Add rate limiting via reverse proxy (Nginx, CloudFlare, Kong)
- Enable CORS restrictions (currently allows all origins)
- Use HTTPS via reverse proxy (see [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md))
- Set up API versioning strategy (currently implicit)

See [Security Configuration](../5-CONFIGURATION/security.md) and [Reverse Proxy Setup](../5-CONFIGURATION/reverse-proxy.md) for complete production setup.
