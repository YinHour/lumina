# MarkItDown 文档引擎集成推进计划

> For Hermes: 如需执行本计划，优先使用 subagent-driven-development skill，按任务逐项实现和复查。

Goal: 在 Lumina 中新增 MarkItDown 作为可选文档内容处理引擎，用于轻量 Markdown 提取，并在失败时安全 fallback 到现有 simple/content-core 流程。

Architecture: 沿用当前 `open_notebook/graphs/source.py` 中 MinerU 的拦截模式，在进入 `content_core.extract_content()` 前识别 `document_engine == "markitdown"` 并用 MarkItDown 提取本地上传文件内容。设置项、API schema、前端 Settings 表单和 locale 同步扩展，避免后端能保存但前端不能选择，或前端能提交但后端 Pydantic/Literal 不接受。

Tech Stack: Python 3.11/3.12, FastAPI, Pydantic v2, content-core, MarkItDown, Next.js/React, react-hook-form, zod, uv, pytest, pnpm.

---

## 当前上下文

已确认：

- 项目路径：`/Users/wangz/project/lumina`
- 当前分支工作区已有大量前端改动，执行时必须避免覆盖无关改动。
- 当前 `reason_content` 搜索为 0 命中；本计划只覆盖 MarkItDown 文档引擎集成，不处理 reason_content 补丁。
- 当前 `pyproject.toml` 已有：
  - `content-core[docling]>=1.14.1,<2`
  - `mineru>=3.0.0`
- 当前没有安装 MarkItDown：`ModuleNotFoundError: No module named 'markitdown'`
- 依赖解析预检查通过：临时加入 `markitdown[pdf,docx,pptx,xlsx,xls]>=0.1.3` 后 `uv pip compile` 成功。
- 当前文档引擎枚举为：`auto | docling | mineru | simple`
- 当前 `content_core.common.ProcessSourceState` 很可能不接受 `mineru/markitdown`，现有 MinerU 分支已通过在返回前把 `document_engine` 改回 `auto` 来规避校验。

工作区当前已有未提交改动，包括但不限于：

- `frontend/next.config.ts`
- `frontend/src/app/(auth)/login/page.tsx`
- `frontend/src/app/(auth)/register/page.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/lib/config.ts`
- `frontend/src/lib/locales/en-US/index.ts`
- `frontend/src/lib/locales/zh-CN/index.ts`
- 多个新增 frontend assets/components

执行计划时必须先 `git diff -- <file>` 查看目标文件当前状态，所有 patch 只改与 MarkItDown 相关的最小片段。

---

## 非目标 / 暂不做

- 不把 MarkItDown 设为默认引擎；默认仍保持 `auto`。
- 不替换 MinerU；MinerU 仍适合 OCR、扫描 PDF、复杂版面。
- 不处理旧 `.doc` 的 LibreOffice/textutil 预转换，除非后续单独加任务。
- 不开放 MarkItDown 处理任意 URL；只处理 Lumina 已保存的本地上传文件路径，降低安全风险。
- 不引入 `markitdown[all]`，避免不必要的音频、Azure、YouTube 等依赖。

---

## 支持范围

第一版支持 MarkItDown 处理这些本地文件后缀：

- `.pdf`
- `.docx`
- `.pptx`
- `.xlsx`
- `.xls`
- `.html`
- `.htm`
- `.csv`
- `.json`
- `.xml`
- `.epub`
- `.zip`
- `.txt`
- `.md`

不支持：

- `.doc`，先 fallback 到 simple，并记录 warning。
- 无 file_path 的 URL source，继续走 content-core URL 流程。

---

## Task 1: 加入 MarkItDown 后端依赖

Objective: 让后端环境可以 import 并调用 MarkItDown。

Files:
- Modify: `/Users/wangz/project/lumina/pyproject.toml`
- Generated/updated by uv: `/Users/wangz/project/lumina/uv.lock`，如果项目使用 lockfile。

Steps:

1. 查看当前依赖区域：

   Run:

   `sed -n '15,55p' pyproject.toml`

2. 在 dependencies 中追加一行，建议放在 content-core 或 mineru 附近：

   `"markitdown[pdf,docx,pptx,xlsx,xls]>=0.1.3",`

   推荐位置：`content-core[docling]` 后面，便于理解它也是内容提取依赖。

3. 同步依赖：

   Run:

   `uv sync --extra dev`

   Expected:

   - 命令成功退出。
   - `uv run python -c "from markitdown import MarkItDown; print(MarkItDown)"` 成功。

4. 验证依赖解析：

   Run:

   `uv pip compile pyproject.toml --extra dev --quiet >/tmp/lumina-markitdown-lock-check.txt`

   Expected:

   - exit code 0。

Commit:

`git add pyproject.toml uv.lock && git commit -m "feat: add markitdown dependency"`

如果当前用户工作区不适合提交，则不要 commit，只记录待提交文件。

---

## Task 2: 扩展 ContentSettings 文档引擎枚举

Objective: 后端配置模型接受 `markitdown`，并允许通过 `CCORE_DOCUMENT_ENGINE=markitdown` 设置默认值。

Files:
- Modify: `/Users/wangz/project/lumina/open_notebook/domain/content_settings.py`
- Test: `/Users/wangz/project/lumina/tests/test_domain.py`

Implementation:

在 `ContentSettings.default_content_processing_engine_doc` 的 Literal 中加入 `"markitdown"`：

```python
default_content_processing_engine_doc: Optional[
    Literal["auto", "docling", "mineru", "markitdown", "simple"]
] = Field(None, description="Default Content Processing Engine for Documents")
```

在 env 校验列表中加入 `"markitdown"`：

```python
if env_val in ["auto", "docling", "mineru", "markitdown", "simple"]:
    self.default_content_processing_engine_doc = env_val
```

Test plan:

1. 在 `tests/test_domain.py` 新增或扩展 ContentSettings 测试。
2. 覆盖：
   - `CCORE_DOCUMENT_ENGINE=markitdown` 时默认值为 `markitdown`。
   - 非法值仍 fallback 到 `auto`。

Suggested test shape:

```python
def test_content_settings_accepts_markitdown_env(monkeypatch):
    ContentSettings.clear_instance()
    monkeypatch.setenv("CCORE_DOCUMENT_ENGINE", "markitdown")

    settings = ContentSettings()

    assert settings.default_content_processing_engine_doc == "markitdown"


def test_content_settings_invalid_doc_engine_falls_back_to_auto(monkeypatch):
    ContentSettings.clear_instance()
    monkeypatch.setenv("CCORE_DOCUMENT_ENGINE", "invalid")

    settings = ContentSettings()

    assert settings.default_content_processing_engine_doc == "auto"
```

Verification:

Run:

`uv run pytest tests/test_domain.py -q`

Expected:

- 新增测试通过。
- 既有 ContentSettings 测试不回归。

Commit:

`git add open_notebook/domain/content_settings.py tests/test_domain.py && git commit -m "feat: allow markitdown document engine setting"`

---

## Task 3: 扩展 settings API schema 和 router cast

Objective: API GET/PUT `/settings` 接受并返回 `markitdown`。

Files:
- Modify: `/Users/wangz/project/lumina/api/models.py`
- Modify: `/Users/wangz/project/lumina/api/settings_service.py`
- Modify: `/Users/wangz/project/lumina/api/routers/settings.py`
- Test: 可优先加到已有 settings/API 测试；若没有合适文件，新建 `/Users/wangz/project/lumina/tests/test_settings_api.py`

Known current files:

- `api/models.py` 当前 SettingsResponse/SettingsUpdate 中 doc engine 类型是 `Optional[str]`，可能不需要改；如果有 Literal 或 validator，要同步加 `markitdown`。
- `api/routers/settings.py` 当前 cast Literal 需要改。
- `api/settings_service.py` 当前只是透传，通常无需改逻辑，但需要检查是否有白名单。

Implementation:

在 `api/routers/settings.py` 中把：

```python
Literal["auto", "docling", "mineru", "simple"]
```

改为：

```python
Literal["auto", "docling", "mineru", "markitdown", "simple"]
```

Test plan:

- 如果 router 测试已有 app fixture，写 PUT `/api/settings` 或对应 mounted path，提交：

```json
{"default_content_processing_engine_doc": "markitdown"}
```

断言 response 中返回：

```json
{"default_content_processing_engine_doc": "markitdown"}
```

- 如果没有轻量 API fixture，至少用单元测试构造 `SettingsUpdate(default_content_processing_engine_doc="markitdown")` 并验证 router update 逻辑可保存。保存 DB 的部分应 mock `ContentSettings.get_instance()` 和 `settings.update()`。

Verification:

Run:

`uv run pytest tests/test_settings_api.py -q`

或：

`uv run pytest tests/test_domain.py tests/test_settings_api.py -q`

Commit:

`git add api/models.py api/settings_service.py api/routers/settings.py tests/test_settings_api.py && git commit -m "feat: accept markitdown in settings api"`

---

## Task 4: 抽出 MarkItDown 提取 helper

Objective: 避免把全部逻辑塞进 `content_process()` 内部，降低 `source.py` 复杂度，并方便单测。

Files:
- Create: `/Users/wangz/project/lumina/open_notebook/content/markitdown_extractor.py`
- Create if needed: `/Users/wangz/project/lumina/open_notebook/content/__init__.py`
- Test: `/Users/wangz/project/lumina/tests/test_markitdown_extractor.py`

Implementation:

新增 helper，职责：

- 判断文件后缀是否支持。
- 对 unsupported 文件返回 structured fallback 信息，而不是抛出。
- 调用 `MarkItDown(enable_plugins=False).convert_local(file_path)`。
- 返回 markdown 字符串。
- 空内容视为失败。

Suggested code:

```python
from __future__ import annotations

import os
from dataclasses import dataclass

from loguru import logger

SUPPORTED_MARKITDOWN_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".csv",
    ".json",
    ".xml",
    ".epub",
    ".zip",
    ".txt",
    ".md",
}


@dataclass(frozen=True)
class MarkItDownExtractionResult:
    content: str | None
    supported: bool
    error: str | None = None


def is_markitdown_supported_file(file_path: str) -> bool:
    return os.path.splitext(file_path.lower())[1] in SUPPORTED_MARKITDOWN_EXTENSIONS


def extract_markitdown_content(file_path: str) -> MarkItDownExtractionResult:
    if not is_markitdown_supported_file(file_path):
        return MarkItDownExtractionResult(
            content=None,
            supported=False,
            error="unsupported_file_type",
        )

    try:
        from markitdown import MarkItDown

        converter = MarkItDown(enable_plugins=False)
        result = converter.convert_local(file_path)
        content = (result.text_content or "").strip()
        if not content:
            return MarkItDownExtractionResult(
                content=None,
                supported=True,
                error="empty_content",
            )
        return MarkItDownExtractionResult(content=content, supported=True)
    except Exception as exc:
        logger.error(f"MarkItDown extraction failed for {file_path}: {exc}")
        return MarkItDownExtractionResult(
            content=None,
            supported=True,
            error=str(exc),
        )
```

Tests:

1. `is_markitdown_supported_file("a.docx") is True`
2. `is_markitdown_supported_file("a.doc") is False`
3. Mock `markitdown.MarkItDown.convert_local` 返回 `text_content="# Hello"`，验证 helper 返回 content。
4. Mock 返回空字符串，验证 error 为 `empty_content`。
5. Mock 抛异常，验证不抛出而返回 error。

Verification:

Run:

`uv run pytest tests/test_markitdown_extractor.py -q`

Commit:

`git add open_notebook/content tests/test_markitdown_extractor.py && git commit -m "feat: add markitdown extraction helper"`

---

## Task 5: 在 source content_process 中接入 MarkItDown 分支

Objective: 当用户选择 MarkItDown 文档引擎时，上传文件由 MarkItDown 提取，成功后直接返回 ProcessSourceState；失败时 fallback 到 simple。

Files:
- Modify: `/Users/wangz/project/lumina/open_notebook/graphs/source.py`
- Test: `/Users/wangz/project/lumina/tests/test_source_content_process_markitdown.py`

Implementation approach:

在 `_sync_extract(state)` 内，MinerU 分支后、调用 `extract_content(state)` 前加入：

```python
if engine == "markitdown" and file_path:
    from open_notebook.content.markitdown_extractor import extract_markitdown_content

    logger.info(f"Using MarkItDown to extract content from {file_path}")
    result = extract_markitdown_content(file_path)
    if result.content:
        logger.info(f"Successfully extracted {len(result.content)} chars using MarkItDown.")
        state["content"] = result.content
        if not state.get("title") and state.get("file_path"):
            state["title"] = os.path.basename(state["file_path"])
        state["document_engine"] = "auto"
        return ProcessSourceState(**state)

    if result.supported:
        logger.warning(
            f"MarkItDown failed to produce markdown output ({result.error}). Falling back to simple engine."
        )
    else:
        logger.warning("MarkItDown does not support this file type. Falling back to simple engine.")
    state["document_engine"] = "simple"
elif engine == "markitdown":
    logger.warning("MarkItDown requires a local file path. Falling back to simple engine.")
    state["document_engine"] = "simple"
```

Important:

- 成功返回前必须把 `state["document_engine"] = "auto"`，与 MinerU 当前规避 ProcessSourceState 校验的方式一致。
- 失败时不要吞掉后续处理，而是把 document_engine 改为 `simple` 后继续调用 `extract_content(state)`。
- 不处理 URL source。
- 不改变 MinerU 原有逻辑。

Test strategy:

优先测 `_sync_extract` 不易直接访问的问题。如果内部函数不好测，建议做一个小重构：把“根据 engine 做预提取”的逻辑抽成模块级函数，例如：

`_maybe_extract_with_custom_document_engine(state: dict[str, Any]) -> ProcessSourceState | None`

然后测试这个 helper。

Suggested helper behavior:

- 输入 `document_engine=markitdown, file_path=/tmp/a.docx`
- Mock `extract_markitdown_content` 返回 content。
- 断言返回 `ProcessSourceState`，content 正确，title fallback 为 basename，document_engine 为 auto。
- Mock 返回 empty_content。
- 断言返回 None 且 state document_engine 被改为 simple。
- 输入 `document_engine=markitdown, file_path=/tmp/a.doc`
- 断言返回 None 且 state document_engine=simple。

Verification:

Run:

`uv run pytest tests/test_source_content_process_markitdown.py -q`

Then run a broader backend subset:

`uv run pytest tests/test_domain.py tests/test_markitdown_extractor.py tests/test_source_content_process_markitdown.py -q`

Commit:

`git add open_notebook/graphs/source.py tests/test_source_content_process_markitdown.py && git commit -m "feat: process documents with markitdown engine"`

---

## Task 6: 前端 Settings 表单加入 MarkItDown 选项

Objective: 用户可以在 Settings 页面选择 MarkItDown。

Files:
- Modify: `/Users/wangz/project/lumina/frontend/src/app/(dashboard)/settings/components/SettingsForm.tsx`
- Modify: `/Users/wangz/project/lumina/frontend/src/lib/types/api.ts`，如有更严格 union 类型则同步。

Current location:

`SettingsForm.tsx` 当前有：

```ts
z.enum(['auto', 'docling', 'mineru', 'simple']).optional()
```

和 SelectItem：

```tsx
<SelectItem value="auto">{t.settings.autoRecommended}</SelectItem>
<SelectItem value="docling">{t.settings.docling}</SelectItem>
<SelectItem value="mineru">{t.settings.mineru}</SelectItem>
<SelectItem value="simple">{t.settings.simple}</SelectItem>
```

Implementation:

- zod enum 加 `markitdown`。
- TypeScript cast union 加 `markitdown`。
- SelectItem 在 MinerU 和 Simple 之间加入：

```tsx
<SelectItem value="markitdown">{t.settings.markitdown}</SelectItem>
```

Suggested order:

1. Auto
2. Docling
3. MinerU
4. MarkItDown
5. Simple

Verification:

Run:

`cd frontend && pnpm lint`

如果项目无 lint script，则运行：

`cd frontend && pnpm build`

Commit:

`git add frontend/src/app/'(dashboard)'/settings/components/SettingsForm.tsx frontend/src/lib/types/api.ts && git commit -m "feat: expose markitdown in settings form"`

注意：当前前端已有大量未提交改动，执行前必须查看 `git diff -- frontend/src/app/'(dashboard)'/settings/components/SettingsForm.tsx`，只改与 Settings 表单有关的最小片段。

---

## Task 7: 更新 locale 文案

Objective: Settings 页面显示 MarkItDown 名称，并在帮助文案中解释适用场景。

Files:
- Modify: `/Users/wangz/project/lumina/frontend/src/lib/locales/en-US/index.ts`
- Modify: `/Users/wangz/project/lumina/frontend/src/lib/locales/zh-CN/index.ts`
- Optional: 其它 locale 文件也可同步加 `markitdown: "MarkItDown"`，避免语言切换时报缺字段。

Implementation:

在 settings locale 对象中加入：

English:

```ts
markitdown: "MarkItDown",
```

Chinese:

```ts
markitdown: "MarkItDown",
```

更新 docHelp，建议中文：

```ts
docHelp: "· Docling 较慢但更准确，适合包含表格和图片的文档。· MinerU 更适合复杂 PDF、扫描件、OCR 和版面还原。· MarkItDown 适合 Office 文档、普通 PDF、HTML/CSV/JSON/XML 等轻量 Markdown 提取。· Simple 会快速提取纯文本但保留格式较少。· Auto（推荐）会自动选择并在失败时回退。",
```

英文：

```ts
docHelp: "· Docling is slower but more accurate, especially for documents with tables and images. · MinerU is better for complex PDFs, scanned files, OCR, and layout recovery. · MarkItDown is good for Office documents, regular PDFs, HTML/CSV/JSON/XML, and lightweight Markdown extraction. · Simple quickly extracts plain text with minimal formatting. · Auto (recommended) chooses automatically and falls back when needed.",
```

Verification:

Run:

`cd frontend && pnpm build`

Commit:

`git add frontend/src/lib/locales && git commit -m "feat: document markitdown processing option"`

注意：`en-US` 和 `zh-CN` 当前已有未提交改动，必须最小 patch，不要格式化整个文件。

---

## Task 8: 端到端手动验证

Objective: 验证真实开发环境中 Settings 保存、文档上传和提取链路可用。

Prerequisites:

- 使用本机非 Docker local dev。
- 如需 LAN 访问，保持已知约束：backend bind `0.0.0.0`，Next.js allowedDevOrigins 包含 `192.168.10.237`/`0.0.0.0`，前端 API baseUrl 使用相对路径。

Steps:

1. 启动/刷新依赖和数据库：

   Run:

   `./dev-init.sh`

   Expected:

   - SurrealDB 可用。
   - API 可用。
   - frontend dev server 可用。

2. 后端快速 import 验证：

   Run:

   `uv run python -c "from markitdown import MarkItDown; print('markitdown ok')"`

   Expected:

   `markitdown ok`

3. 打开 Settings 页面，选择 Document Engine = MarkItDown，保存。

4. 调用 API 验证设置已保存：

   Run:

   `curl -s http://localhost:5050/api/settings | python -m json.tool`

   或按当前项目实际 API prefix 调整。

   Expected:

   `default_content_processing_engine_doc` 为 `markitdown`。

5. 上传一个小型 `.docx` 或 `.pdf`。

6. 观察 worker/backend log：

   Expected log includes:

   - `Using MarkItDown to extract content from ...`
   - `Successfully extracted ... chars using MarkItDown.`

7. 在 UI 中打开 source。

   Expected:

   - source 不再停留 Processing。
   - full text/summary 能看到提取出的 Markdown 内容。
   - 如果开启 embedding，vectorization 正常提交。

8. 上传一个 `.doc` 或不支持格式。

   Expected:

   - log 显示 MarkItDown 不支持并 fallback simple。
   - 不因 `markitdown` 枚举导致 ProcessSourceState validation error。

---

## Task 9: 回归测试和质量检查

Objective: 确保后端、前端、依赖和已有 MinerU 流程没有明显回归。

Commands:

Backend:

`uv run pytest tests/test_domain.py tests/test_markitdown_extractor.py tests/test_source_content_process_markitdown.py -q`

如果新增了 settings API 测试：

`uv run pytest tests/test_settings_api.py -q`

Lint:

`uv run ruff check open_notebook/domain/content_settings.py open_notebook/content/markitdown_extractor.py open_notebook/graphs/source.py tests/test_markitdown_extractor.py tests/test_source_content_process_markitdown.py`

Frontend:

`cd frontend && pnpm build`

Dependency sanity:

`uv run python -c "from markitdown import MarkItDown; print('ok')"`

Git review:

`git diff --stat`

`git diff -- pyproject.toml open_notebook/domain/content_settings.py api/routers/settings.py open_notebook/graphs/source.py frontend/src/app/'(dashboard)'/settings/components/SettingsForm.tsx frontend/src/lib/locales/en-US/index.ts frontend/src/lib/locales/zh-CN/index.ts`

Expected:

- 只包含 MarkItDown 相关改动。
- 没有误改已有登录页、首页、公有页设计文件。

---

## Risks and Mitigations

1. MarkItDown 依赖可能拉入较多 transitive deps

Mitigation:

- 不使用 `[all]`。
- 第一版只加 `[pdf,docx,pptx,xlsx,xls]`。
- 用 `uv pip compile` 验证。

2. `ProcessSourceState` 不接受 `markitdown`

Mitigation:

- 与 MinerU 一样，成功返回前设置 `document_engine="auto"`。
- 失败 fallback 前设置 `document_engine="simple"`。

3. MarkItDown 对扫描 PDF/OCR 效果不如 MinerU

Mitigation:

- UI 帮助文案明确区分适用场景。
- 不改变默认引擎。
- 保留 MinerU。

4. 当前工作区已有大量未提交前端改动，容易冲突或误覆盖

Mitigation:

- 每个目标文件 patch 前先 `git diff -- <file>`。
- 不运行格式化整个目录的命令。
- 只做小范围 patch。

5. 安全风险：MarkItDown README 提醒 convert 可能访问进程可访问资源

Mitigation:

- 只用 `convert_local(file_path)`。
- 只处理 Lumina 上传路径中的本地文件。
- 不把任意用户 URL 交给 MarkItDown。

---

## Acceptance Criteria

- `ContentSettings(default_content_processing_engine_doc="markitdown")` 合法。
- `CCORE_DOCUMENT_ENGINE=markitdown` 生效。
- Settings API 能保存并返回 `markitdown`。
- Settings UI 下拉框显示 MarkItDown。
- 选择 MarkItDown 后上传支持文件，source content 能成功填充 Markdown。
- 支持文件提取失败时 fallback 到 simple，不产生 validation error。
- 不支持文件如 `.doc` fallback 到 simple。
- 后端新增/相关测试通过。
- 前端 build 或 lint 通过。
- 不影响现有 MinerU 分支。

---

## 推荐执行顺序

1. Task 1 dependency
2. Task 2 backend settings model
3. Task 3 API
4. Task 4 extractor helper
5. Task 5 source graph integration
6. Task 6 frontend form
7. Task 7 locale
8. Task 9 automated verification
9. Task 8 manual end-to-end verification

如果希望降低风险，可以先只做 Task 1-5，后端链路验证通过后再做前端 UI。