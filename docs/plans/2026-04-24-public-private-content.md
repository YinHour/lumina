# Lumina 公开/私密 Sources & Notebooks 实现计划

> **Status: ✅ Implemented** — 2026-04-27, branch `feature/public-private-content`
>
> All phases completed. Additional work beyond this plan:
> - Source deletion constraint: public sources with active references cannot be deleted (409 Conflict)
> - Notebook.delete() reorder: unlink references before deleting exclusive sources
> - `PATCH /sources/{id}/visibility` endpoint (one-way toggle)
> - `POST /sources/bulk-delete` endpoint with per-source constraint checking
> - Frontend public browse page, visibility selector component, i18n keys
> - `init-admin.py` admin user creation script
>
> **Relevant docs:**
> - [Core Concepts: Visibility](../2-CORE-CONCEPTS/notebooks-sources-notes.md#2-public--private-visibility)
> - [API Reference: Visibility API](../7-DEVELOPMENT/api-reference.md#visibility-api)
> - [API Reference: Public Browsing](../7-DEVELOPMENT/api-reference.md#public-browsing-api)

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 为 Source 和 Notebook 添加 owner_id + visibility 字段，实现公开/私密内容隔离，新增 Public 浏览页面。

**Architecture:** 在 SurrealDB 层添加 owner 字段和 visibility 枚举，在 API 中间件层提取用户身份，在路由层按 owner + visibility 过滤数据，在前端新增 Public 浏览页和可见性选择器。

**Tech Stack:** SurrealDB v2 (migrations)、FastAPI (routes/middleware)、Python 3.12+、Next.js 16 (React 19)、TypeScript、Zustand / TanStack Query、Tailwind CSS + Shadcn/ui

---

## Phase 1: 数据库迁移 (Backend)

### Task 1.1: 创建 source 表 migration 扩展文件

**Objective:** 为 source 表添加 owner_id 和 visibility 字段，以及对应的索引

**Files:**
- Create: `open_notebook/database/migrations/20.surrealql`
- Create: `open_notebook/database/migrations/20_down.surrealql`

**Step 1: 创建 20.surrealql**

```sql
-- Migration 20: Add owner_id and visibility to source and notebook tables

-- === Source table ===

-- Add owner field (references app_user)
DEFINE FIELD IF NOT EXISTS owner_id ON TABLE source TYPE option<record<app_user>>;

-- Add visibility field with default 'private'
DEFINE FIELD IF NOT EXISTS visibility ON TABLE source TYPE string DEFAULT 'private';
DEFINE FIELD IF NOT EXISTS visibility ON TABLE source ASSERT $value IN ['private', 'public'];

-- Index for efficient owner-based queries
DEFINE INDEX IF NOT EXISTS idx_source_owner ON TABLE source COLUMNS owner_id;

-- Index for public sources browsing
DEFINE INDEX IF NOT EXISTS idx_source_public ON TABLE source COLUMNS visibility;

-- === Notebook table ===

DEFINE FIELD IF NOT EXISTS owner_id ON TABLE notebook TYPE option<record<app_user>>;

DEFINE FIELD IF NOT EXISTS visibility ON TABLE notebook TYPE string DEFAULT 'private';
DEFINE FIELD IF NOT EXISTS visibility ON TABLE notebook ASSERT $value IN ['private', 'public'];

DEFINE INDEX IF NOT EXISTS idx_notebook_owner ON TABLE notebook COLUMNS owner_id;

DEFINE INDEX IF NOT EXISTS idx_notebook_public ON TABLE notebook COLUMNS visibility;
```

**Step 2: 创建 20_down.surrealql**

```sql
-- Rollback Migration 20

REMOVE INDEX IF EXISTS idx_source_owner ON TABLE source;
REMOVE INDEX IF EXISTS idx_source_public ON TABLE source;
REMOVE FIELD IF EXISTS owner_id ON TABLE source;
REMOVE FIELD IF EXISTS visibility ON TABLE source;

REMOVE INDEX IF EXISTS idx_notebook_owner ON TABLE notebook;
REMOVE INDEX IF EXISTS idx_notebook_public ON TABLE notebook;
REMOVE FIELD IF EXISTS owner_id ON TABLE notebook;
REMOVE FIELD IF EXISTS visibility ON TABLE notebook;
```

---

### Task 1.2: 注册新迁移到 AsyncMigrationManager

**Objective:** 将 migration 20 加入迁移管理器

**File:** `open_notebook/database/async_migrate.py`

**Step 1: 在 up_migrations 列表末尾添加**

找到类似以下代码段（在 `__init__` 方法中）：

```python
self.up_migrations = [
    # ... 现有 migrations 1-19 ...
    AsyncMigration.from_file("open_notebook/database/migrations/19.surrealql"),
]
```

在末尾的 `]` 之前添加：

```python
    AsyncMigration.from_file("open_notebook/database/migrations/20.surrealql"),
```

**Step 2: 在 down_migrations 列表开头添加**

```python
self.down_migrations = [
    AsyncMigration.from_file("open_notebook/database/migrations/20_down.surrealql"),
    # ... 现有 down migrations ...
]
```

**Verification:** 运行 `python -c "from open_notebook.database.async_migrate import AsyncMigrationManager; m = AsyncMigrationManager(); assert len(m.up_migrations) >= 20"`

---

## Phase 2: Backend 域模型扩展

### Task 2.1: 更新 Notebook 域模型

**Objective:** 为 Notebook 添加 owner_id 和 visibility 字段

**File:** `open_notebook/domain/notebook.py` (Notebook 类, 约第16-22行)

**Step 1: 添加字段**

在 `Notebook` 类的 `creator_name` 之后添加：

```python
class Notebook(ObjectModel):
    table_name: ClassVar[str] = "notebook"
    name: str
    description: str
    archived: Optional[bool] = False
    password: Optional[str] = None
    creator_name: Optional[str] = None
    owner_id: Optional[str] = None      # record ID of the owning app_user
    visibility: Optional[str] = "private"  # "private" or "public"
```

**Step 2: 确认 nullable_fields 不需要特殊处理**

owner_id 是 Optional[str]，visibility 有默认值，Pydantic 可正常处理。

---

### Task 2.2: 更新 Source 域模型

**Objective:** 为 Source 添加 owner_id 和 visibility 字段

**File:** `open_notebook/domain/notebook.py` (Source 类, 约第290-298行)

**Step 1: 在 Source 类的 `command` 字段之后添加：**

```python
class Source(ObjectModel):
    # ... existing fields ...
    command: Optional[Union[str, RecordID]] = Field(
        default=None, description="Link to surreal-commands processing job"
    )
    owner_id: Optional[str] = None
    visibility: Optional[str] = "private"
```

---

## Phase 3: 认证中间件增强

### Task 3.1: 提取用户身份并注入 request.state

**Objective:** 在中间件中从 JWT 提取 user_id，通过 request.state 传递给下游路由

**File:** `api/auth.py`

**Step 1: 修改 PasswordAuthMiddleware.dispatch**

在认证成功后、调用 `call_next` 之前，将 user 信息注入 `request.state`：

```python
async def dispatch(self, request: Request, call_next):
    # ... existing path exclusion logic ...

    auth_header = request.headers.get("Authorization")

    # --- Legacy mode: env var password ---
    if self.legacy_password:
        # ... existing legacy check ...
        if credentials == self.legacy_password:
            request.state.user_id = None  # legacy: no user context
            request.state.username = None
            return await call_next(request)
        payload = await validate_jwt_token(credentials)
        if payload:
            request.state.user_id = payload.get("sub")
            request.state.username = payload.get("username")
            return await call_next(request)
        # ... error ...

    # --- Database mode: JWT validation ---
    has_users = await _check_has_users()
    if not has_users:
        request.state.user_id = None
        request.state.username = None
        return await call_next(request)

    # ... existing JWT validation ...
    payload = await validate_jwt_token(token)
    if not payload:
        # ... error ...
    
    request.state.user_id = payload.get("sub")
    request.state.username = payload.get("username")
    return await call_next(request)
```

**Step 2: 创建一个 FastAPI 依赖函数**

新建或在 `api/auth.py` 末尾添加：

```python
from fastapi import Request

async def get_current_user_id(request: Request) -> Optional[str]:
    """Dependency that extracts current user_id from request.state (set by middleware)."""
    return getattr(request.state, "user_id", None)
```

---

## Phase 4: API 路由更新

### Task 4.1: 更新 GET /notebooks — 添加用户过滤

**Objective:** 只返回当前用户的 notebooks + 公开的 notebooks

**File:** `api/routers/notebooks.py`

**Step 1: 添加导入**

```python
from api.auth import get_current_user_id
```

**Step 2: 修改 get_notebooks 函数签名**

```python
@router.get("/notebooks", response_model=List[NotebookResponse])
async def get_notebooks(
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    order_by: str = Query("updated desc", description="Order by field and direction"),
    user_id: Optional[str] = Depends(get_current_user_id),
):
```

**Step 3: 修改查询添加 WHERE 条件**

在 ORDER BY 之前插入过滤逻辑：

```python
# Build the query with counts
conditions = []
params = {}

if user_id:
    # Show user's own notebooks + public notebooks from others
    conditions.append("(owner_id = $user_id OR visibility = 'public')")
    params["user_id"] = user_id
else:
    # Legacy mode: show all
    pass

where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

query = f"""
    SELECT *,
    count(<-reference.in) as source_count,
    count(<-artifact.in) as note_count
    FROM notebook
    {where_clause}
    ORDER BY {validated_order_by}
"""
```

---

### Task 4.2: 更新 POST /notebooks — 自动设置 owner

**Objective:** 创建 notebook 时自动设置 owner_id 为当前用户

**File:** `api/routers/notebooks.py`

**Step 1: 修改 create_notebook 函数**

```python
@router.post("/notebooks", response_model=NotebookResponse)
async def create_notebook(
    notebook: NotebookCreate,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    try:
        new_notebook = Notebook(
            name=notebook.name,
            description=notebook.description,
            password=notebook.password,
            creator_name=notebook.creator_name,
            owner_id=user_id,
            visibility=notebook.visibility or "private",
        )
        await new_notebook.save()
```

---

### Task 4.3: 更新 PUT/DELETE /notebooks — 所有权检查

**Objective:** 只允许 owner 编辑/删除自己的 notebook

**File:** `api/routers/notebooks.py`

**Step 1: 创建辅助函数**

```python
async def _check_notebook_ownership(notebook_id: str, user_id: Optional[str]) -> Notebook:
    """Fetch notebook and verify ownership. Raises 403 if not owner."""
    notebook = await Notebook.get(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    if user_id and notebook.owner_id and notebook.owner_id != user_id:
        raise HTTPException(status_code=403, detail="You can only modify your own notebooks")
    return notebook
```

**Step 2: 在 update_notebook 和 delete_notebook 中添加所有权检查**

```python
@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    notebook_update: NotebookUpdate,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    try:
        notebook = await _check_notebook_ownership(notebook_id, user_id)
        # ... rest of update logic ...
```

```python
@router.delete("/notebooks/{notebook_id}", response_model=NotebookDeleteResponse)
async def delete_notebook(
    notebook_id: str,
    delete_exclusive_sources: bool = Query(False),
    user_id: Optional[str] = Depends(get_current_user_id),
):
    try:
        notebook = await _check_notebook_ownership(notebook_id, user_id)
        # ... rest of delete logic ...
```

**Step 4: update_notebook 支持 visibility 更新**

在字段更新部分添加：

```python
if notebook_update.visibility is not None:
    notebook.visibility = notebook_update.visibility
```

---

### Task 4.4: 更新 GET /notebooks/{id} — 可见性检查

**Objective:** 检查用户是否有权访问特定 notebook

```python
@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(
    notebook_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    try:
        nb_result = await repo_query(query, {"notebook_id": ensure_record_id(notebook_id)})
        if not nb_result:
            raise HTTPException(status_code=404, detail="Notebook not found")
        
        nb = nb_result[0]
        owner = nb.get("owner_id")
        visibility = nb.get("visibility", "private")
        
        # Check access: own or public
        if owner and visibility == "private":
            if not user_id or owner != user_id:
                raise HTTPException(status_code=404, detail="Notebook not found")
        
        # ... return response ...
```

---

### Task 4.5: 更新 Sources 路由 (同样模式)

**Objective:** 对 Sources 路由应用相同的 owner + visibility 逻辑

**File:** `api/routers/sources.py`

对以下端点应用类似修改：

1. **GET /sources**: 添加 `user_id: Optional[str] = Depends(get_current_user_id)`，过滤 `(owner_id = $user_id OR visibility = 'public')`
2. **POST /sources**: 在创建 Source 时设置 `owner_id=user_id`，并支持 `visibility` 参数
3. **PUT /sources/{id}**: 添加 `_check_source_ownership()` 辅助函数
4. **DELETE /sources/{id}**: 添加所有权检查
5. **GET /sources/{id}**: 添加可见性检查

---

### Task 4.6: 更新 Pydantic 模型

**Objective:** 在 API schemas 中添加 owner_id, visibility, owner_username 字段

**File:** `api/models.py`

**Step 1: NotebookCreate 添加 visibility**

```python
class NotebookCreate(BaseModel):
    name: str
    description: str = Field(default="")
    password: Optional[str] = None
    creator_name: Optional[str] = None
    visibility: Optional[str] = Field(default="private", description="'private' or 'public'")
```

**Step 2: NotebookUpdate 添加 visibility**

```python
class NotebookUpdate(BaseModel):
    # ... existing fields ...
    visibility: Optional[str] = Field(None, description="'private' or 'public'")
```

**Step 3: NotebookResponse 添加 owner 信息**

```python
class NotebookResponse(BaseModel):
    # ... existing fields ...
    owner_id: Optional[str] = None
    visibility: Optional[str] = "private"
    owner_username: Optional[str] = None  # populated by query JOIN
```

**Step 4: SourceCreate, SourceUpdate, SourceResponse 同样添加**

---

### Task 4.7: 新增 GET /public/notebooks 和 GET /public/sources 端点

**Objective:** 提供专门的公开内容浏览 API

**File:** `api/routers/notebooks.py` 和 `api/routers/sources.py`

```python
@router.get("/public/notebooks", response_model=List[NotebookResponse])
async def get_public_notebooks(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get all public notebooks."""
    try:
        query = """
            SELECT *, owner_id.owner_id.username AS owner_username,
            count(<-reference.in) as source_count,
            count(<-artifact.in) as note_count
            FROM notebook
            WHERE visibility = 'public'
            ORDER BY updated DESC
            LIMIT $limit START $offset
            FETCH owner_id
        """
        result = await repo_query(query, {"limit": limit, "offset": offset})
        # ... map to NotebookResponse with owner_username ...
    except Exception as e:
        # ... error handling ...
```

---

### Task 4.8: 搜索函数添加用户范围

**Objective:** 更新 `text_search` 和 `vector_search` 支持用户范围过滤

**File:** `open_notebook/domain/notebook.py`

**Step 1: 在搜索路由添加用户过滤**

`api/routers/search.py` 中的 `search_knowledge_base`：

添加 `user_id` 依赖，将 owner 过滤传递给 search 请求。

**注意:** 搜索函数定义在 SurrealQL 的 `fn::text_search` 和 `fn::vector_search` 中（migration 1）。由于修改函数需要新 migration，初期可以通过在 API 层后过滤搜索结果来实现（检查每个结果的 owner_id），后续再优化 SurrealQL 函数。

---

## Phase 5: Frontend 更新

### Task 5.1: 更新 TypeScript 类型

**Objective:** 在 frontend types 中添加 owner_id, visibility, owner_username

**File:** `frontend/src/lib/types/api.ts`

**Step 1: 更新 NotebookResponse**

```typescript
export interface NotebookResponse {
  // ... existing fields ...
  owner_id?: string | null
  visibility?: string
  owner_username?: string | null
}
```

**Step 2: 更新 CreateNotebookRequest / UpdateNotebookRequest**

```typescript
export interface CreateNotebookRequest {
  // ... existing fields ...
  visibility?: string  // 'private' | 'public'
}

export interface UpdateNotebookRequest {
  // ... existing fields ...
  visibility?: string
}
```

**Step 3: 更新 SourceListResponse / SourceDetailResponse**

```typescript
export interface SourceListResponse {
  // ... existing fields ...
  owner_id?: string | null
  visibility?: string
  owner_username?: string | null
}
```

---

### Task 5.2: 更新 API 客户端

**Objective:** 前端 API 调用同步后端变化

**Files:**
- `frontend/src/lib/api/notebooks.ts`
- `frontend/src/lib/api/sources.ts`

**Step 1: 添加 public API 方法**

```typescript
// notebooks.ts
export const notebooksApi = {
  // ... existing methods ...
  listPublic: async (params?: { limit?: number; offset?: number }) => {
    const response = await apiClient.get<NotebookResponse[]>('/public/notebooks', { params })
    return response.data
  },
}
```

```typescript
// sources.ts
export const sourcesApi = {
  // ... existing methods ...
  listPublic: async (params?: { limit?: number; offset?: number }) => {
    const response = await apiClient.get<SourceListResponse[]>('/public/sources', { params })
    return response.data
  },
}
```

---

### Task 5.3: 更新 Sidebar 导航

**Objective:** 在侧边栏添加 "Public / 探索" 导航项

**File:** `frontend/src/components/layout/AppSidebar.tsx`

**Step 1: 添加图标导入**

```typescript
import { Globe } from 'lucide-react'  // 或 Compass
```

**Step 2: 在 navigation 中添加 Public 项**

在 `getNavigation` 函数的 sections 中，在 "Process" section 添加：

```typescript
const getNavigation = (t: TranslationKeys) => [
  {
    title: t.navigation.collect,
    items: [
      { name: t.navigation.sources, href: '/sources', icon: FileText },
    ],
  },
  {
    title: t.navigation.process,
    items: [
      { name: t.navigation.notebooks, href: '/notebooks', icon: Book },
      { name: t.navigation.askAndSearch, href: '/search', icon: Search },
      { name: t.navigation.public, href: '/public', icon: Globe },  // NEW
    ],
  },
  // ... rest
]
```

---

### Task 5.4: 创建 /public 页面

**Objective:** 新建公开内容浏览页面

**Files to create:**
- `frontend/src/app/(dashboard)/public/page.tsx`
- `frontend/src/components/public/PublicNotebooks.tsx`
- `frontend/src/components/public/PublicSources.tsx`

**Step 1: 创建页面框架**

```tsx
// frontend/src/app/(dashboard)/public/page.tsx
'use client'

import { useTranslation } from '@/lib/hooks/use-translation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import PublicNotebooks from '@/components/public/PublicNotebooks'
import PublicSources from '@/components/public/PublicSources'

export default function PublicPage() {
  const { t } = useTranslation()
  
  return (
    <div className="flex flex-col max-w-[1400px] mx-auto w-full h-full px-6 py-6">
      <h1 className="text-2xl font-bold mb-6">{t.public.title}</h1>
      <Tabs defaultValue="notebooks">
        <TabsList>
          <TabsTrigger value="notebooks">{t.navigation.notebooks}</TabsTrigger>
          <TabsTrigger value="sources">{t.navigation.sources}</TabsTrigger>
        </TabsList>
        <TabsContent value="notebooks">
          <PublicNotebooks />
        </TabsContent>
        <TabsContent value="sources">
          <PublicSources />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

**Step 2: 创建 PublicNotebooks 和 PublicSources 组件**

使用 TanStack Query 调用 `notebooksApi.listPublic()` 和 `sourcesApi.listPublic()`，以卡片/列表形式展示，显示 owner_username。

---

### Task 5.5: 添加 Visibility 选择器

**Objective:** 在创建/编辑 Notebook 和 Source 时允许选择 visibility

**Files to modify:**
- SourceDialog 组件
- NotebookDialog 组件

**Step 1: 创建 VisibilitySelector 组件**

```tsx
// frontend/src/components/common/VisibilitySelector.tsx
'use client'

import { Lock, Globe } from 'lucide-react'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { useTranslation } from '@/lib/hooks/use-translation'

interface VisibilitySelectorProps {
  value: string
  onChange: (value: string) => void
}

export function VisibilitySelector({ value, onChange }: VisibilitySelectorProps) {
  const { t } = useTranslation()
  
  return (
    <RadioGroup value={value} onValueChange={onChange} className="flex gap-4">
      <div className="flex items-center space-x-2">
        <RadioGroupItem value="private" id="private" />
        <Label htmlFor="private" className="flex items-center gap-1">
          <Lock className="h-3.5 w-3.5" />
          {t.common.private}
        </Label>
      </div>
      <div className="flex items-center space-x-2">
        <RadioGroupItem value="public" id="public" />
        <Label htmlFor="public" className="flex items-center gap-1">
          <Globe className="h-3.5 w-3.5" />
          {t.common.public}
        </Label>
      </div>
    </RadioGroup>
  )
}
```

**Step 2: 在创建/编辑对话框中嵌入**

在 Notebook 和 Source 的创建表单中，在适当位置（如 name 字段下方）添加 `<VisibilitySelector>`。

---

### Task 5.6: 在列表页显示 owner 标签

**Objective:** 在 Notebook 卡片和 Source 列表项上，如果是他人公开的内容，显示创建者名称

**Files to modify:**
- Notebook 列表组件
- Source 列表组件

在现有组件中，当 `item.owner_id !== currentUserId` 时，显示一个小的 owner badge。

---

### Task 5.7: 添加 i18n 翻译键

**Objective:** 为中英文添加新的翻译键

**Files:**
- `frontend/src/lib/locales/en-US/common.json`
- `frontend/src/lib/locales/zh-CN/common.json`
- `frontend/src/lib/locales/en-US/navigation.json` (if exists)
- `frontend/src/lib/locales/zh-CN/navigation.json` (if exists)

**New keys needed:**

```json
// en-US
{
  "common": {
    "public": "Public",
    "private": "Private",
    "byCreator": "by {name}"
  },
  "navigation": {
    "public": "Explore"
  },
  "public": {
    "title": "Public Content",
    "noNotebooks": "No public notebooks yet",
    "noSources": "No public sources yet",
    "description": "Discover notebooks and sources shared by the community"
  }
}
```

```json
// zh-CN
{
  "common": {
    "public": "公开",
    "private": "私密",
    "byCreator": "来自 {name}"
  },
  "navigation": {
    "public": "发现"
  },
  "public": {
    "title": "公开内容",
    "noNotebooks": "还没有公开的笔记本",
    "noSources": "还没有公开的来源",
    "description": "发现社区分享的笔记本和来源"
  }
}
```

---

## Phase 6: 测试与验证

### Task 6.1: 后端单元测试

添加测试覆盖：

1. Migration 20 正确添加字段和索引
2. 无 owner 的 Notebook 在无过滤的 legacy 模式下仍然可访问
3. 有 owner 的 private notebook 只对 owner 可见
4. 有 owner 的 public notebook 对所有登录用户可见
5. 非 owner 不能编辑/删除他人的 notebook/source
6. 公开浏览 API 只返回 visibility=public 的内容

### Task 6.2: 前端构建验证

```bash
cd frontend && pnpm run build
```

确保 TypeScript 编译无错误。

### Task 6.3: 端到端验证流程

1. 启动 API + SurrealDB
2. 注册两个用户 userA 和 userB
3. userA 创建 private notebook → userB 不可见 ✓
4. userA 创建 public notebook → userB 可在 /public 看到 ✓
5. userB 尝试编辑 userA 的 public notebook → 403 ✓
6. userB 创建自己的 notebook → 正常 ✓
7. 搜索只返回自己的 + 公开的结果 ✓

---

## 向后兼容

- **Legacy 模式（无 user 系统）**: 当 `OPEN_NOTEBOOK_PASSWORD` 设置时，所有内容继续全量可见，owner_id 字段为 None，现有行为不变。
- **Migration 安全**: 所有新字段使用 `DEFINE FIELD IF NOT EXISTS`，对已有数据设为可选 (option<...>)，不破坏现有数据。

---

## 不变的部分

以下系统在此次改动中**不需要修改**：

- Chat / Source Chat 系统
- Podcast 生成
- Notes 系统（Notes 属于 Notebook，继承 Notebook 的可见性）
- Credential / Model 管理
- Transformation
- LangGraph workflows
- 前端 Message/Chat 组件
