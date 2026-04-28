# 开发计划：用户名/密码验证 + 密码修改

> 状态更新（2026-04）：本文最初是实施计划，当前仓库已完成大部分核心能力，包括用户名/密码登录、JWT 会话、密码修改、注册、验证码邮件、忘记密码与重置密码流程。保留本文主要用于记录设计背景与实现思路；具体本地开发方式请优先参考 `README.dev.md`、`docs/7-DEVELOPMENT/development-setup.md` 与 `docs/1-INSTALLATION/from-source.md`。

## 背景

最初系统使用单一密码认证（`OPEN_NOTEBOOK_PASSWORD` 环境变量），前端只有密码输入框，没有用户名概念，也不支持运行时修改密码。

## 目标

1. **登录页面**：增加用户名 + 密码双字段验证
2. **设置页面**：增加密码修改功能（无需重启服务）

## 整体方案

采用 **数据库存储用户 + 密码哈希** 方案，替代当前的环境变量纯文本密码：

- SurrealDB 新增 `app_user` 表存储用户信息（用户名 + bcrypt 哈希密码）
- 首次启动时如果设置了 `OPEN_NOTEBOOK_USERNAME`/`OPEN_NOTEBOOK_PASSWORD` 环境变量，自动创建管理员账户
- `PasswordAuthMiddleware` 改为查询数据库验证密码
- 新增 `/api/auth/login` 和 `/api/auth/change-password` 端点

---

## Phase 1：后端 — 数据库 + 密码工具

### 1.1 新增 bcrypt 依赖

**文件**: `pyproject.toml`

添加 `bcrypt>=4.0.0` 到 dependencies。

### 1.2 密码哈希工具

**新建文件**: `open_notebook/utils/password.py`

```python
import bcrypt

def hash_password(password: str) -> str:
    """返回 bcrypt 哈希字符串"""

def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配哈希"""
```

### 1.3 数据库迁移（Migration 17）

**新建文件**: `open_notebook/database/migrations/17.surrealql`

```sql
DEFINE TABLE IF NOT EXISTS app_user SCHEMAFULL;
DEFINE FIELD username ON TABLE app_user TYPE string;
DEFINE FIELD password_hash ON TABLE app_user TYPE string;
DEFINE FIELD is_admin ON TABLE app_user TYPE bool DEFAULT true;
DEFINE FIELD created_at ON TABLE app_user TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_username ON TABLE app_user FIELDS username UNIQUE;
```

**新建文件**: `open_notebook/database/migrations/17_down.surrealql`

```sql
REMOVE TABLE IF EXISTS app_user;
```

**更新文件**: `open_notebook/database/async_migrate.py`

添加 migration 17 到 up/down 列表。

### 1.4 初始化默认用户

**更新文件**: `api/main.py`（lifespan 启动流程）

在迁移完成后，检查 `OPEN_NOTEBOOK_USERNAME` / `OPEN_NOTEBOOK_PASSWORD` 环境变量：
- 如果设置了，且数据库中不存在该用户，创建默认管理员账户
- 如果没设置，保留原有行为（密码为空则跳过认证）

---

## Phase 2：后端 — API 端点

### 2.1 更新 auth 路由

**更新文件**: `api/routers/auth.py`

新增以下端点：

#### `POST /api/auth/login` — 用户名密码登录

```python
class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(req: LoginRequest):
    """验证用户名和密码，成功返回 token（即用户名）"""
```

逻辑：
1. 查询 `app_user` 表匹配 username
2. 用 `verify_password()` 验证密码
3. 成功返回 `{ "ok": true, "token": username }`
4. 失败返回 401

#### `PUT /api/auth/change-password` — 修改密码

```python
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.put("/change-password")
async def change_password(req: ChangePasswordRequest, username: str = Depends(get_current_user)):
    """修改当前用户密码"""
```

逻辑：
1. 验证 `current_password` 是否正确
2. 用 `hash_password()` 哈希新密码
3. 更新数据库记录
4. 返回 `{ "ok": true }`

#### `GET /api/auth/me` — 获取当前用户信息

```python
@router.get("/me")
async def get_me(username: str = Depends(get_current_user)):
    """返回当前登录用户信息"""
```

#### `GET /api/auth/status` — 更新

保留原有逻辑，额外返回 `has_users: bool` 表示数据库中是否有用户记录。

### 2.2 提取认证依赖

**新建/更新文件**: `api/auth.py`

新增 `get_current_user` 依赖函数，从 `Authorization: Bearer {username}` 中提取用户名并验证（用于需要认证的端点如 change-password）。

### 2.3 更新 PasswordAuthMiddleware

**更新文件**: `api/auth.py` 中的 `PasswordAuthMiddleware`

中间件改为：
1. 如果 `app_user` 表中有用户记录 → 数据库验证模式（查询数据库，用 bcrypt 验证）
2. 如果表为空但有 `OPEN_NOTEBOOK_PASSWORD` 环境变量 → 兼容旧模式（明文比对）
3. 如果两者都没有 → 跳过认证

### 2.4 更新 Pydantic models

**更新文件**: `api/models.py`

新增：
```python
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    ok: bool
    token: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
```

---

## Phase 3：前端 — 登录页面改造

### 3.1 更新 LoginForm 组件

**更新文件**: `frontend/src/components/auth/LoginForm.tsx`

- 新增 `username` state 和输入框
- `handleSubmit` 改为调用 `login(username, password)`
- 输入框顺序：username → password

### 3.2 更新 auth store

**更新文件**: `frontend/src/lib/stores/auth-store.ts`

- `login()` 改为接收 `(username, password)` 两个参数
- 登录请求改为 `POST /api/auth/login`，发送 `{ username, password }`
- 成功时将 `username` 存储为 `token`（替代原来的 password）
- `checkAuth()` 改用 `GET /api/auth/me` 验证（替代 `/api/notebooks`）

### 3.3 更新 use-auth hook

**更新文件**: `frontend/src/lib/hooks/use-auth.ts`

- `handleLogin` 改为接收 `(username, password)`

### 3.4 更新 API client 拦截器

**检查文件**: `frontend/src/lib/api/client.ts`

确保 interceptor 中的 Bearer token 发送逻辑不变（token 现在存的是 username，后端用数据库验证）。

### 3.5 更新 i18n 翻译

**更新文件**: `frontend/src/lib/locales/zh-CN/index.ts` 和 `en-US/index.ts`

auth 部分新增/更新 key：

```
auth.usernamePlaceholder = "用户名" / "Username"
auth.loginDesc = "输入用户名和密码以访问应用程序" / "Enter your username and password"
auth.loginFailed = "登录失败，请检查用户名和密码" / "Invalid username or password"
```

---

## Phase 4：前端 — 密码修改功能

### 4.1 在设置页面新增密码修改卡片

**新建文件**: `frontend/src/app/(dashboard)/settings/components/ChangePasswordForm.tsx`

组件功能：
- 三个输入框：当前密码、新密码、确认新密码
- 前端校验：新密码 ≥ 6 位，两次输入一致
- 调用 `PUT /api/auth/change-password`
- 成功后显示 toast 提示

### 4.2 集成到设置页面

**更新文件**: `frontend/src/app/(dashboard)/settings/page.tsx`

在 SettingsForm 上方或下方加入 `ChangePasswordForm` 卡片。

### 4.3 新增 i18n 翻译

settings 部分新增 key：

```
settings.changePassword = "修改密码"
settings.changePasswordDesc = "修改您的登录密码"
settings.currentPassword = "当前密码"
settings.newPassword = "新密码"
settings.confirmNewPassword = "确认新密码"
settings.passwordChanged = "密码修改成功"
settings.passwordChangeFailed = "密码修改失败"
settings.passwordsDoNotMatch = "两次密码输入不一致"
settings.passwordTooShort = "密码至少需要6个字符"
settings.currentPasswordPlaceholder = "输入当前密码"
settings.newPasswordPlaceholder = "输入新密码（至少6位）"
settings.confirmPasswordPlaceholder = "再次输入新密码"
```

---

## 文件变更清单

| 操作 | 文件路径 |
|------|----------|
| 修改 | `pyproject.toml` |
| 新建 | `open_notebook/utils/password.py` |
| 新建 | `open_notebook/database/migrations/17.surrealql` |
| 新建 | `open_notebook/database/migrations/17_down.surrealql` |
| 修改 | `open_notebook/database/async_migrate.py` |
| 修改 | `api/models.py` |
| 修改 | `api/auth.py` |
| 修改 | `api/routers/auth.py` |
| 修改 | `api/main.py` |
| 修改 | `frontend/src/components/auth/LoginForm.tsx` |
| 修改 | `frontend/src/lib/stores/auth-store.ts` |
| 修改 | `frontend/src/lib/hooks/use-auth.ts` |
| 新建 | `frontend/src/app/(dashboard)/settings/components/ChangePasswordForm.tsx` |
| 修改 | `frontend/src/app/(dashboard)/settings/page.tsx` |
| 修改 | `frontend/src/lib/locales/zh-CN/index.ts` |
| 修改 | `frontend/src/lib/locales/en-US/index.ts` |

---

## 注意事项

1. **向后兼容**：如果环境变量 `OPEN_NOTEBOOK_PASSWORD` 存在但数据库中没有用户，保留旧模式兼容
2. **密码安全**：使用 bcrypt，不存储明文
3. **token 存储**：前端 localStorage 中存储的是 username（非敏感信息），后端通过中间件每次请求验证
4. **多用户扩展**：当前设计为单用户场景（`app_user` 表理论上支持多用户，但前端只处理一个活跃用户）
5. **迁移安全**：migration 17 使用 `IF NOT EXISTS` 保证幂等
