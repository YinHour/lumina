# Lumina Architecture Cleanup Plan

> **Status:** Completed
>
> **Goal:** 收紧后端边界、统一长任务模型、降低内容处理和数据库访问的耦合，并补齐前后端契约与配置一致性。该计划优先做结构整理，不以功能扩张为目标。
>
> **Current assumption:** 系统仍处于开发调试阶段，不需要维持与生产系统或旧部署形态的兼容性。后续推进可以优先选择更彻底的结构收口：删除旧路径、移除同步兼容分支、减少 legacy wrapper，而不是长期保留双轨实现。

## Progress Log

### 2026-04-29

- Started Phase 1 backend boundary cleanup.
- Added `api/services/` as the application service landing zone.
- Moved source permission helpers, upload helpers, form parsing, command status helpers, and source list response mapping out of `api/routers/sources.py`.
- Kept compatibility imports/wrappers in `api.routers.sources` for existing tests and callers.
- Moved source processing command submission, sync compatibility execution, and command failure marking into `api/services/source_processing.py`.
- Added `open_notebook/database/session.py` and repository landing zone under `open_notebook/database/repositories/`.
- Moved source list queries and notebook list/count queries into source/notebook repositories.
- Added `OPEN_NOTEBOOK_CORS_ORIGINS` and documented production CORS configuration.
- Reused the same CORS allowlist for custom error responses so they no longer echo arbitrary request origins in production mode.
- Added `OPEN_NOTEBOOK_AUTH_MODE=auto|none|password|jwt` with tests for explicit modes.
- Fixed frontend runtime API URL priority so `/config` runtime config wins over `NEXT_PUBLIC_API_URL`, with existing config tests passing.
- Aligned `eslint-config-next` to Next 16.1.7 in npm and pnpm lockfiles.
- Extracted MinerU CLI content extraction into `open_notebook/content_extractors/mineru.py`.
- Added `ContentExtractionService` and moved source graph content extraction preparation/engine dispatch into `open_notebook/content_extractors/service.py`.
- Updated architecture documentation to describe Router -> Service -> Repository/Domain flow and mark `api_client` self-calls as legacy compatibility only.
- Added OpenAPI contract tests for notebook/source list, source detail, and source status response schemas.
- Reduced `api/routers/sources.py` from 1586 lines to 1193 lines.
- Reduced `open_notebook/graphs/source.py` to 158 lines.
- Verified with `uv run ruff check api/routers/sources.py api/services`.
- Verified with `uv run pytest tests/test_visibility_access.py tests/test_worker_timeout.py tests/test_sources_api.py`.
- Verified auth mode changes with `uv run pytest tests/test_auth_modes.py tests/test_auth_legacy_and_registration.py tests/test_jwt_auth_security.py`.
- Verified frontend config with `npm run test -- src/lib/config.test.ts`.
- Verified content extraction changes with `uv run pytest tests/test_markitdown_extractor.py tests/test_graphs.py`.
- Ran full backend suite: `uv run pytest tests/` -> 192 passed, 1 skipped.
- Attempted `npm run build`; build reached Next/Turbopack production build but failed because `next/font` could not fetch Google Fonts (`fonts.googleapis.com`) in the current network environment.

### 2026-04-30

- Removed the legacy synchronous source processing branch; `POST /sources` now always creates a source record and queues `process_source`.
- Removed the legacy `/sources/json` endpoint and updated the old `api/client.py` shim to call the multipart `/api/sources` endpoint instead.
- Moved source creation, full source response assembly, status response assembly, update, visibility switch, retry, knowledge graph queueing, and insight command queueing into `api/services/source_service.py`.
- Added `file_path` support to source form parsing so dev/local callers can still queue upload sources by path through the current form endpoint.
- Removed `wait_for_command_sync` and the sync source processing helper from `api/services/source_processing.py`.
- Reduced `api/routers/sources.py` to 586 lines and removed direct `submit_command` calls from the source router.
- Verified with `uv run ruff check api/routers/sources.py api/services/source_service.py api/services/source_processing.py api/services/source_forms.py api/client.py tests/test_visibility_access.py`.
- Verified source/API boundary changes with `uv run pytest tests/test_visibility_access.py tests/test_worker_timeout.py tests/test_sources_api.py tests/test_api_contract.py` -> 17 passed.
- Ran full backend suite: `uv run pytest tests/` -> 191 passed, 1 skipped.
- Moved notebook/source relationship link and unlink queries into `NotebookRepository`.
- Removed direct `repo_query` imports from both `api/routers/notebooks.py` and `api/routers/sources.py`.
- Fixed notebook-source reference existence checks to use the actual SurrealDB relationship direction (`source -> reference -> notebook`) before creating links.
- Verified repository boundary changes with `uv run pytest tests/test_visibility_access.py tests/test_sources_api.py tests/test_api_contract.py tests/test_domain.py` -> 33 passed.
- Moved `Notebook` domain relationship queries (`get_sources`, `get_notes`, `get_chat_sessions`, delete preview, delete cleanup) into `NotebookRepository`.
- Moved `Source` domain metadata and cleanup queries (embedded chunk count, KG presence, insights, referenced notebooks, embeddings/insights/KG/reference cleanup) into `SourceRepository`.
- Added `SearchRepository` for text, vector, and graph search SurrealQL.
- Removed direct `repo_query` usage from `open_notebook/domain/notebook.py`.
- Verified domain repository migration with `uv run pytest tests/test_domain.py tests/test_embedding.py tests/test_graphs.py tests/test_visibility_access.py tests/test_sources_api.py tests/test_api_contract.py` -> 64 passed.
- Added `repo_transaction()` for SurrealQL transaction bodies.
- Consolidated source related-record cleanup (embeddings, insights, optional KG data, notebook references) into one transaction-backed `SourceRepository.delete_related_records()` call.
- Verified source cleanup transaction boundary with `uv run pytest tests/test_domain.py tests/test_sources_api.py tests/test_visibility_access.py` -> 29 passed.
- Changed notebook deletion to plan counts first, delete notebook/note/artifact/reference/exclusive-source database records in one transaction, then remove exclusive source files after the transaction succeeds.
- Added failure coverage proving notebook deletion does not remove exclusive source files when the database transaction fails.
- Added source retry failure coverage: if command submission succeeds but persisting `source.command` fails, the newly submitted command is marked failed.
- Unified API-layer command submission through `CommandService.submit_command_job`; direct `submit_command()` usage is now outside `api/` except inside `api/command_service.py`.
- Simplified `/embed` to always queue background embedding commands.
- Added `command_id` alongside `job_id` on command job response/status schemas and expanded contract tests for embedding and commands.
- Added `scripts/generate_openapi_types.py` and generated `frontend/src/lib/types/generated-api.ts`.
- Updated `frontend/src/lib/api/embedding.ts` to use generated OpenAPI types for embed request/response.
- Removed `next/font/google` usage and switched the frontend to a local system font stack so production builds no longer fetch Google Fonts.
- Documented the current compatibility-only `api_client` wrappers in `docs/7-DEVELOPMENT/architecture.md`; new backend behavior should land in `api/services/`, domain, or repository code instead.
- Verified OpenAPI type generation with `uv run python scripts/generate_openapi_types.py --check`.
- Verified frontend config tests with `npm run test -- src/lib/config.test.ts`.
- Verified frontend production build with `npm run build`.
- Ran full backend suite: `uv run pytest tests/` -> 196 passed, 1 skipped.
- Converted content extraction dispatch to an extractor registry shape using `ContentExtractor`, `MarkItDownExtractor`, and `MinerUExtractor`.
- Added MinerU extractor tests for supported extensions, successful CLI markdown output, unsupported-file fallback, and CLI-failure fallback.
- Added `ContentExtractionService` tests proving registered extractors run before the default engine and MarkItDown unsupported files fall back to content-core/simple extraction.
- Expanded API contract tests to cover source creation and auth status/login response schemas.
- Updated architecture guidance and root contributor guidance for Router -> Service -> Repository, command lifecycle, content extraction plugins, and compatibility-only `api_client` wrappers.
- Added `commands/lifecycle.py` as the shared command submission/status helper and routed both API command submission and source-graph transformation submission through it.
- Verified content extraction and command lifecycle changes with `uv run pytest tests/test_api_contract.py tests/test_graphs.py tests/test_source_service.py tests/test_sources_api.py` -> 27 passed.
- Verified full backend suite with `uv run pytest tests/` -> 205 passed, 1 skipped.
- Verified frontend config with `npm run test -- src/lib/config.test.ts` -> 4 passed.
- Verified frontend lint with `npm run lint` -> 0 errors, 25 existing warnings.
- Verified frontend production build with `npm run build`.
- Verified touched Python scope with `uv run ruff check ...` -> passed.
- Completed whole-repository import sorting with `uv run ruff check . --select I --fix`.
- Verified whole-repository lint with `uv run ruff check .`.
- Verified runtime health against the locally running stack:
  - `GET /health` -> healthy
  - `GET /api/config` -> database online
  - frontend root -> reachable
  - `GET /api/sources/public?limit=1` -> public source response shape available

**Phase 1.3 closure:** complete under the current dev/debug assumption. The active source routes are stable, while the old JSON compatibility endpoint has intentionally been removed.

**Task 1.1 closure:** complete. All current `from api.client import api_client` call sites are classified as root-level compatibility wrappers, and docs state that new backend code must not add API-internal HTTP self-calls.

**Phase 2.2 closure:** complete for API routers and `open_notebook/domain/notebook.py`; raw SurrealQL for notebook/source/search paths is now concentrated in repository modules.

**Phase 2.3 closure:** complete for the planned backend consistency pass. Source retry orphan-command cleanup is covered, source cleanup uses a transaction, and notebook delete now uses a transaction for database records with post-transaction best-effort file cleanup.

**Phase 3 closure:** complete for command submission boundaries. Source processing, embedding, transformations, KG extraction, podcast generation, and generic commands submit through the shared command lifecycle helper exposed to API callers by `CommandService`.

**Phase 5.4 closure:** complete. Frontend build no longer depends on Google Fonts and `npm run build` passes.

**Phase 4 closure:** complete. Source graph delegates extraction to `ContentExtractionService`; MarkItDown and MinerU are isolated extractor modules; fallback rules have targeted tests.

**Phase 6.1 closure:** complete for the planned contract baseline. Type generation is in place, `--check` verifies generated output, and one frontend API module uses generated OpenAPI types. Broader frontend type adoption remains incremental hardening.

**Phase 6.2 closure:** complete for the planned high-frequency surface. Contract tests cover notebooks list, sources list/detail/create/status, embedding, commands submit/status, and auth status/login.

**Phase 7.1 closure:** complete. Architecture docs and root contributor guidance now describe the current service/repository/command/content-extractor boundaries.

**Phase 7.2 closure:** automated backend and frontend verification is green, and the running local stack responds for health/config/frontend/public-source smoke checks. Authenticated create/upload/chat/search/podcast smoke remains environment-dependent because the local API has database authentication enabled and no test credentials are part of this cleanup plan.

**Phase 7.3 closure:** complete for the recommended architecture cleanup actions. This plan document is the milestone summary. Any remaining work is incremental hardening rather than a blocker for this cleanup: broader frontend generated-type adoption and an authenticated runtime smoke with a disposable test account.

## Guiding Principles

- 路由层只处理 HTTP 语义：鉴权、请求解析、响应映射、状态码。
- 应用服务层处理用例编排：权限校验、领域对象调用、命令提交、事务边界。
- 领域层表达核心业务规则，避免依赖 FastAPI、HTTP client 或前端响应结构。
- 数据访问集中到 repository，不让 raw SurrealQL 继续散落扩散。
- 长耗时工作统一走 command lifecycle，API 不阻塞等待后台任务完成。
- 开发调试阶段允许 breaking cleanup：优先删除旧兼容路径，而不是为旧调用方保留 wrapper。
- 每一步都以可测试、可回滚、可继续迁移为收口标准。

---

## Phase 1: Backend Boundary Cleanup

### Task 1.1: 标记并冻结旧式 API client service 路径

**Objective:** 明确 `api/client.py` 和 `api/*_service.py` 的角色，避免新代码继续依赖“后端内 HTTP 调后端”的旧路径。

**Files:**
- `api/client.py`
- `api/*_service.py`
- `docs/7-DEVELOPMENT/architecture.md`

**Actions:**
- 盘点所有 `from api.client import api_client` 引用。
- 将仍被运行时使用的调用方列成兼容清单。
- 在文档中声明：新后端逻辑不得通过 `api_client` 调用本 API。
- 后续新增用例必须进入 `api/services/` 或领域/repository 层。

**Closure Conditions:**
- 有一份明确清单说明哪些 `api/*_service.py` 是兼容层，哪些可以迁移或删除。
- 新增贡献指南中写明禁止在后端新增 `api_client` 内部调用。
- `rg "from api.client import api_client" api open_notebook` 的结果被全部分类，无未知用途。

### Task 1.2: 建立新的 application service 目录

**Objective:** 为后续路由瘦身提供稳定落点。

**Files:**
- Create: `api/services/__init__.py`
- Create: `api/services/source_service.py`
- Create: `api/services/notebook_service.py`
- Create: `api/services/command_lifecycle.py`

**Actions:**
- 定义 service 层输入/输出 DTO 或轻量 dataclass。
- 先不大规模迁移，只放入新代码和低风险 helper。
- 把权限判断、响应组装以外的业务逻辑逐步迁入 service。

**Closure Conditions:**
- `api/services/` 可以被路由和测试正常 import。
- 至少一个低风险 helper 从 router 移入 service，并有测试覆盖。
- service 层不 import FastAPI response classes，不返回 `HTTPException`。

### Task 1.3: 拆分 `api/routers/sources.py`

**Objective:** 降低最大路由文件复杂度，把 source 上传、处理、权限、响应映射拆开。

**Files:**
- `api/routers/sources.py`
- `api/services/source_service.py`
- `api/services/source_permissions.py`
- `api/services/source_uploads.py`
- `api/services/source_responses.py`

**Actions:**
- 先迁移纯函数：时间解析、权限判断、文件名生成、响应转换。
- 再迁移 command 提交与 retry 编排。
- 保留路由签名和响应模型，避免前端契约变化。

**Closure Conditions:**
- `api/routers/sources.py` 明显瘦身，目标低于 700 行。
- source 相关测试全部通过：`tests/test_sources_api.py`、`tests/test_visibility_access.py`、`tests/test_worker_timeout.py`。
- 当前前端使用的 source endpoint 路径、状态码、响应字段保持稳定；旧 `/sources/json` 兼容端点在开发调试阶段已删除。
- 路由文件中不再直接调用 `submit_command` 或 `wait_for_command_sync`。

---

## Phase 2: Database Access Cleanup

### Task 2.1: 引入 repository 接口和请求级数据库上下文

**Objective:** 为连接复用、事务边界和测试替换打基础。

**Files:**
- `open_notebook/database/repository.py`
- Create: `open_notebook/database/session.py`
- Create: `open_notebook/database/repositories/source_repository.py`
- Create: `open_notebook/database/repositories/notebook_repository.py`

**Actions:**
- 保留现有 `repo_query` 等函数作为兼容 API。
- 新增 `DatabaseSession` 或等价上下文，集中连接创建、signin、namespace/database selection。
- 为 `Source` 和 `Notebook` 先建立 repository 方法。

**Closure Conditions:**
- 现有测试不需要大规模改写即可通过。
- 新 repository 有单元测试或集成测试覆盖基础 CRUD/query。
- 新代码路径不直接拼接 record id 字符串，统一使用 helper。
- 兼容函数内部可以复用新 session，但外部接口保持不破。

### Task 2.2: 把高风险 raw SurrealQL 收口到 repository

**Objective:** 减少路由和领域模型中散落的查询字符串。

**Priority Targets:**
- `api/routers/notebooks.py`
- `api/routers/sources.py`
- `open_notebook/domain/notebook.py`

**Actions:**
- 先迁移 notebook/source 列表、访问过滤、关系计数、删除预览查询。
- 对每个迁移后的 query 增加命名方法。
- 对需要动态排序的查询保留 allowlist 校验。

**Closure Conditions:**
- `api/routers/notebooks.py` 不再直接 import `repo_query`。
- source/notebook 主要读取路径都走 repository。
- 动态 order/filter 的 allowlist 仍有测试覆盖。
- 删除 notebook/source 的行为测试和可见性测试保持通过。

### Task 2.3: 明确事务边界

**Objective:** 让多记录变更具备一致性，尤其是删除、解除关系、重试任务。

**Targets:**
- Notebook 删除及关联 note/source/reference 清理。
- Source 删除及 public reference constraint。
- Source retry processing command 更新。

**Actions:**
- 定义事务 helper 或 repository-level transaction 方法。
- 把跨记录更新合并到单个事务语义中。
- 对失败中断路径增加测试。

**Closure Conditions:**
- Notebook 删除过程中任一步失败不会留下半删除状态，或有明确补偿逻辑。
- Source retry command 更新失败时不会出现 source 指向不存在 command 的状态。
- 有测试模拟 repository 异常并验证状态不被部分提交。

---

## Phase 3: Command Lifecycle Unification

### Task 3.1: 统一长任务提交模型

**Objective:** API 对 source processing、embedding、transformation、podcast 等长任务统一返回 command 状态。

**Files:**
- `api/command_service.py`
- `api/services/command_lifecycle.py`
- `api/routers/commands.py`
- source/embedding/podcast/transformations 相关路由

**Actions:**
- 定义统一响应字段：`command_id`、`status`、`processing_info`。
- 抽出 submit、mark_failed、timeout classification、status normalization。
- 为同步兼容路径加 deprecation note。

**Closure Conditions:**
- 新增或重构后的长任务 endpoint 不调用同步等待 API。
- `/api/commands/{id}` 可以查询所有相关任务状态。
- command 失败、超时、重试状态使用同一套枚举或 normalization。
- 前端能用同一轮询逻辑处理至少 source processing 和 embedding。

### Task 3.2: 移除路由内同步等待

**Objective:** 防止 API worker 被长任务阻塞。

**Targets:**
- `api/routers/sources.py` 中的 `wait_for_command_sync`
- 路由附近的 `asyncio.run`

**Actions:**
- 把同步处理改成提交 command 后立即返回。
- 若必须保留兼容参数，限制为测试/开发模式，并文档化。
- 前端用 command polling 展示进度。

**Closure Conditions:**
- `rg "wait_for_command_sync|asyncio.run" api/routers api/services` 不再命中生产路由路径。
- 慢速 source 处理不会占用 HTTP 请求直到完成。
- worker timeout 测试改为验证 command 状态，而不是 HTTP 请求阻塞超时。

---

## Phase 4: Content Extraction Pluginization

### Task 4.1: 抽出 ContentExtractionService

**Objective:** 让 LangGraph 节点只编排，不承载具体提取引擎细节。

**Files:**
- `open_notebook/graphs/source.py`
- Create: `open_notebook/content_extractors/service.py`
- Create: `open_notebook/content_extractors/base.py`

**Actions:**
- 定义 extractor 接口：`supports(state)`、`extract(state)`。
- 将 content settings、STT model 注入逻辑放入 service。
- Graph node 调用 service，返回 `ProcessSourceState`。

**Closure Conditions:**
- `open_notebook/graphs/source.py` 不再直接 import `subprocess`、`tempfile`。
- graph tests 仍通过。
- service 有针对空内容、YouTube 无字幕、fallback 的测试。

### Task 4.2: 拆分 MarkItDown 和 MinerU extractor

**Objective:** 把第三方引擎集成隔离为可测试模块。

**Files:**
- `open_notebook/content_extractors/markitdown.py`
- Create: `open_notebook/content_extractors/mineru.py`
- `open_notebook/content_extractors/service.py`

**Actions:**
- MarkItDown 支持判断保留在 extractor 内。
- MinerU CLI 调用、环境变量、输出目录扫描放入 `mineru.py`。
- 为 extractor fallback 规则增加测试。

**Closure Conditions:**
- MinerU 不可用或失败时 fallback 行为与当前一致。
- MarkItDown 不支持的文件类型 fallback 行为与当前一致。
- `tests/test_markitdown_extractor.py` 通过，并新增 MinerU 轻量 mock 测试。

---

## Phase 5: Auth, Runtime Config, and Production Posture

### Task 5.1: 明确认证模式配置

**Objective:** 区分本地无认证、legacy password、JWT 用户库、生产强制认证。

**Files:**
- `api/auth.py`
- `api/jwt_auth.py`
- `docs/5-CONFIGURATION/security.md`
- `docs/5-CONFIGURATION/environment-reference.md`

**Actions:**
- 新增或文档化 `OPEN_NOTEBOOK_AUTH_MODE`：`none`、`password`、`jwt`、`auto`。
- 生产文档中不推荐 `auto` 和无用户免认证。
- 保留 backward compatibility，但在启动日志中提示风险。

**Closure Conditions:**
- auth mode 行为有测试覆盖。
- 文档明确每种模式的安全边界。
- 生产部署文档中给出推荐配置。

### Task 5.2: 收紧 CORS 配置

**Objective:** 避免生产默认 `allow_origins=["*"]`。

**Files:**
- `api/main.py`
- `docs/5-CONFIGURATION/security.md`
- `docs/5-CONFIGURATION/environment-reference.md`

**Actions:**
- 新增环境变量 `OPEN_NOTEBOOK_CORS_ORIGINS`。
- 默认开发可宽松，生产示例使用明确 origin。
- 保持本地 Docker/Next proxy 体验不破。

**Closure Conditions:**
- CORS origins 从配置读取。
- 没有配置时本地开发仍可用。
- 文档包含 reverse proxy 下的推荐设置。

### Task 5.3: 修正前端 runtime config 优先级

**Objective:** 让 `/config` endpoint、`NEXT_PUBLIC_API_URL` 和 relative proxy 的优先级与注释一致。

**Files:**
- `frontend/src/lib/config.ts`
- `frontend/src/lib/config.test.ts`

**Actions:**
- 决定是否真正使用 `/config` 返回的 `apiUrl`。
- 若使用，则优先级应为 runtime config > env > relative default。
- 若不使用，则删除无效 runtime branch 和误导注释。

**Closure Conditions:**
- config 单元测试覆盖三种来源。
- 注释和实际优先级一致。
- Docker runtime API URL 场景有明确测试或手动验证步骤。

### Task 5.4: 对齐前端 Next 相关版本

**Objective:** 避免 Next 16 与 Next 15 ESLint config 混用。

**Files:**
- `frontend/package.json`
- lockfile

**Actions:**
- 将 `eslint-config-next` 对齐到 Next 主版本。
- 运行 lint/test/build 验证。

**Closure Conditions:**
- `npm run lint` 通过。
- `npm run test` 通过。
- `npm run build` 通过，或记录已知非本次引入问题。

---

## Phase 6: API Contract and Frontend Integration

### Task 6.1: 生成或校验前后端类型契约

**Objective:** 降低 FastAPI Pydantic schema 与前端 TypeScript type 漂移风险。

**Files:**
- `api/models.py`
- `frontend/src/lib/types/*`
- Create: `scripts/generate-openapi-types.*` or equivalent

**Actions:**
- 选择 OpenAPI 到 TypeScript 的生成工具。
- 先只生成到临时目录并 diff 现有类型。
- 制定迁移策略：生成类型作为 source of truth，hooks 做 UI 适配。

**Closure Conditions:**
- 有命令可生成 TypeScript API types。
- CI 或本地测试能检测 OpenAPI schema 变化。
- 至少一个前端 API module 使用生成类型。

### Task 6.2: 增加 contract tests

**Objective:** 对高频 endpoint 的响应结构做稳定性保护。

**Targets:**
- notebooks list/detail
- sources list/detail/create/status
- commands status
- auth status/login

**Actions:**
- 使用 FastAPI TestClient 或 httpx async client 校验 OpenAPI response shape。
- 对前端依赖字段加断言。

**Closure Conditions:**
- contract tests 在 `uv run pytest tests/` 中运行。
- 修改 response 字段会触发测试失败。
- 前端类型生成和 contract tests 的职责边界清楚。

---

## Phase 7: Overall Closure

### Task 7.1: 架构文档更新

**Objective:** 让文档描述与实际代码一致。

**Files:**
- `docs/7-DEVELOPMENT/architecture.md`
- `AGENTS.md`
- Relevant nested `AGENTS.md` files if needed

**Closure Conditions:**
- 文档中的请求流与真实代码一致：Router -> Service -> Repository/Domain -> DB/Command。
- 文档明确长任务 command lifecycle。
- 文档明确新代码应放在哪一层。

### Task 7.2: 全量验证

**Objective:** 确认整理没有破坏核心功能。

**Required Checks:**
- `uv run pytest tests/`
- Frontend lint/test/build
- Manual smoke: create notebook, upload source, process source, chat, search, generate/retry command status
- Public/private visibility smoke if auth enabled

**Closure Conditions:**
- 所有自动化检查通过，或遗留失败有明确 issue 和 owner。
- 手动 smoke 结果记录在最终 PR 或 release note。
- 没有新增未分类架构例外。

### Task 7.3: Cleanup Completion Review

**Objective:** 对所有推荐动作做最终收口。

**Checklist:**
- 后端没有新的内部 HTTP self-call。
- Source router 已拆分，路由层职责轻量。
- Source/Notebook 主要 DB 访问集中在 repository。
- 长任务统一 command lifecycle，不阻塞 HTTP。
- Content extraction 已插件化，MinerU/MarkItDown 可独立测试。
- Auth/CORS/runtime config 文档和实现一致。
- 前端 Next 相关依赖版本对齐。
- OpenAPI/TypeScript 契约有生成或校验机制。
- 架构文档、开发指南、测试覆盖同步更新。

**Final Closure Conditions:**
- 开一个总收口 PR 或 milestone 总结，逐项勾掉本计划 checklist。
- 对未完成项必须有明确理由、风险说明和后续 issue。
- 维护者可以基于文档判断新功能应该放在哪一层。
- 新贡献不会被旧双轨结构误导。
