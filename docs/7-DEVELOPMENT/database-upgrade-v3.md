# SurrealDB v3 Upgrade Runbook

This runbook upgrades the single-node RocksDB database from SurrealDB v2 to
SurrealDB v3.0.5. The recommended cutover is a maintenance window: stop writes,
export from v2, import into a fresh v3.0.5 database, verify, and then restore
traffic.

References:

- [Upgrades and patching](https://surrealdb.com/docs/manage/self-hosted/upgrades-and-patching)
- [2.x to 3.x migration guide](https://surrealdb.com/docs/build/migrating/from-old-surrealdb-versions/2x-to-3x)
- [SurrealDB releases](https://surrealdb.com/releases)
- [CLI export](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export)

## Phase 1: Baseline

Collect the current state before changing anything.

```bash
surreal version
grep '^SURREAL_' .env
grep '^SURREAL_COMMANDS_MAX_TASKS' .env || true
uv run --env-file .env python - <<'PY'
import asyncio
from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.database.repository import repo_query, close_database_pool

TABLES = [
    "_sbl_migrations",
    "source",
    "notebook",
    "note",
    "reference",
    "source_embedding",
    "source_insight",
    "kg_entity",
    "kg_relation",
]

async def main():
    manager = AsyncMigrationManager()
    print("migration_version", await manager.get_current_version())
    for table in TABLES:
        result = await repo_query(f"SELECT count() AS total FROM {table} GROUP ALL;")
        print(table, result[0]["total"] if result else 0)
    await close_database_pool()

asyncio.run(main())
PY
```

Baseline closes when the migration version and table counts are recorded.

## Phase 2: Staging Rehearsal

Run migration diagnostics before exporting. Surrealist diagnostics are available
for SurrealDB 2.6.1 and newer. Resolve any flagged manual issues before cutover.

Export from the v2 database using the SurrealDB 3.0.5 CLI. The `v2 export --v3`
path is required because the v3 binary cannot directly read v2 data files, and
the v2 binary does not produce v3-compatible exports.
The first `surreal v2 ...` invocation may prompt to download a cached v2 binary;
allow it during rehearsal so the production cutover is not blocked by first-run
tool setup.

```bash
mkdir -p data/backups
DB_HTTP_ENDPOINT="${SURREAL_HTTP_ENDPOINT:-http://127.0.0.1:8000}"
surreal v2 export --v3 \
  --endpoint "$DB_HTTP_ENDPOINT" \
  --user "$SURREAL_USER" \
  --pass "$SURREAL_PASSWORD" \
  --namespace "$SURREAL_NAMESPACE" \
  --database "$SURREAL_DATABASE" \
  data/backups/surreal-v2-$(date +%Y%m%d-%H%M%S).surql
```

Use the HTTP endpoint for CLI export/import. The application WebSocket RPC URL
such as `ws://127.0.0.1:8000/rpc` is still correct for the Python driver, but
the backup/export path is validated against the HTTP service endpoint.

Start a fresh v3.0.5 staging database and import.

```bash
docker run -d --rm --name lumina-surreal-v3-stage \
  -p 18000:8000 \
  -v "$PWD/.dev-data/surreal-v3-stage:/mydata" \
  surrealdb/surrealdb:v3.0.5 start \
  --log info --user root --pass root --bind 0.0.0.0:8000 \
  rocksdb:/mydata/mydatabase.db

surreal import \
  --endpoint http://127.0.0.1:18000 \
  --user root \
  --pass root \
  --namespace "$SURREAL_NAMESPACE" \
  --database "$SURREAL_DATABASE" \
  data/backups/<export-file>.surql
```

Point a staging `.env` at `ws://127.0.0.1:18000/rpc`, start the API, and let
automatic migrations run.

```bash
SURREAL_URL=ws://127.0.0.1:18000/rpc uv run --env-file .env run_api.py
```

Rehearsal closes when import succeeds, API startup succeeds, the migration
version is latest, and core flows pass.

## Phase 3: Code And Config

Required application settings:

```env
SURREAL_POOL_SIZE=10
SURREAL_POOL_ACQUIRE_TIMEOUT=5
SURREAL_QUERY_TIMEOUT=30
SURREAL_TRANSACTION_RETRY_ATTEMPTS=3
SURREAL_COMMANDS_MAX_TASKS=5
```

If staging shows repeated transaction conflicts or queue buildup, lower
`SURREAL_COMMANDS_MAX_TASKS` to `2` before production cutover.

SurrealQL compatibility changes already handled in this codebase:

- `SEARCH ANALYZER` index definitions have been updated to `FULLTEXT ANALYZER`.
- Migration version records use `type::record()` instead of removed `type::thing()`.
- The source lookup query avoids `source.*` to stay clear of v3 `.*` idiom changes.

During staging, still verify imported production-like data for schemafull table
strictness. SurrealDB v3 errors on unknown fields that v2 could silently drop.

## Phase 4: Maintenance Cutover

1. Stop API, worker, and frontend write entry points.
2. Run the final `surreal v2 export --v3` export from the v2 database.
3. Stop the v2 database and keep the old RocksDB directory as a read-only backup.
4. Start a fresh SurrealDB v3.0.5 RocksDB database.
5. Import the final `.surql` export.
6. Start the API and let automatic migrations complete.
7. Start the worker and frontend.

Production compose should use:

```yaml
surrealdb:
  image: surrealdb/surrealdb:v3.0.5
  command: start --log info --user root --pass root --bind 0.0.0.0:8000 rocksdb:/mydata/mydatabase.db
```

Cutover closes when health checks pass and these flows work:

- Login and auth status
- Source list and source reference count
- Referenced source deletion shows the protected-source message
- Notebook create/delete
- Text search and vector search
- Background worker task submission and completion

## Phase 5: Observation And Rollback

Observe for 24 hours:

- API error rate and P95/P99 latency
- SurrealDB transaction conflict logs
- Worker queue depth and failed command count
- CPU, memory, and disk I/O

Rollback is supported only before restoring write traffic. Stop v3, restore the
old v2 image and old RocksDB directory, then restart the API. After writes resume
on v3, prefer forward fixes instead of attempting to replay v3 writes into v2.
