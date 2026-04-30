# Developer Guide

This guide is for developers working on Open Notebook. For end-user documentation, see [README.md](README.md) and [docs/](docs/).

## Quick Start for Development

```bash
# 1. Clone and setup
git clone https://github.com/YinHour/lumina.git
cd lumina

# 2. Copy environment file
cp .env.example .env

# 3. Install dependencies
uv sync

# 4. Start the local dev stack (recommended)
./dev-init.sh
```

`./dev-init.sh` is the recommended day-to-day workflow on macOS/Linux for this repository. It prefers local non-Docker development, checks port conflicts, starts the API + worker + frontend, and auto-starts a local SurrealDB 3.0.x binary if the database is not already reachable.

## Development Workflows

### When to Use What?

| Workflow | Use Case | Speed | Production Parity |
|----------|----------|-------|-------------------|
| **Local Services** (`./dev-init.sh`) | Day-to-day development, fastest iteration | ⚡⚡⚡ Fast | Medium |
| **Docker Compose** (`make dev`) | Testing containerized setup | ⚡⚡ Medium | High |
| **Local Docker Build** (`make docker-build-local`) | Testing Dockerfile changes | ⚡ Slow | Very High |
| **Multi-platform Build** (`make docker-push`) | Publishing releases | 🐌 Very Slow | Exact |

---

## 1. Local Development (Recommended)

**Best for:** Daily development, hot reload, debugging

### Setup

```bash
# Start everything in one command
./dev-init.sh
```

Optional overrides:

```bash
# Use a different frontend port
FRONTEND_PORT=3001 ./dev-init.sh

# Disable auto-starting a local SurrealDB binary
START_LOCAL_SURREAL=false ./dev-init.sh
```

### What This Does

1. Loads `.env` from the project root
2. Reuses an existing SurrealDB instance or auto-starts a local SurrealDB 3.0.x binary on port 8000
3. Starts the FastAPI backend on port 5055 and waits for `/api/auth/status`
4. Starts the background worker (`surreal-commands-worker`)
5. Starts the Next.js frontend on port 3000

Important local dev note: this codebase now targets SurrealDB v3.0.5. If you run the database manually, make sure it is a SurrealDB 3.0.x binary.

### Individual Services

```bash
# Just the database
make database

# Just the API
make api

# Just the frontend
make frontend

# Just the worker
make worker
```

### Checking Status

```bash
# See what's running
make status

# Stop everything
make stop-all
```

### Advantages
- ✅ Fastest iteration (hot reload)
- ✅ Easy debugging (direct process access)
- ✅ Low resource usage
- ✅ Direct log access

### Disadvantages
- ❌ Doesn't test Docker build
- ❌ Environment may differ from production
- ❌ Requires local Python/Node setup
- ❌ Requires a local SurrealDB 3.0.x binary if you don't want to reuse an existing DB

### Authentication in local development

The app now supports database-backed username/password authentication with JWT sessions.

- Login page: `/login`
- Self-registration page: `/register`
- Forgot password page: `/forgot-password`
- Auth status endpoint: `GET /api/auth/status`

Useful local testing flags:

```bash
# Log verification codes to the API log instead of sending real email
EMAIL_PROVIDER=debug

# Allow public self-registration for /register
ALLOW_PUBLIC_REGISTRATION=true
```

If you start the API manually, these are handy for end-to-end testing of registration and reset-password flows.

---

## 2. Docker Compose Development

**Best for:** Testing containerized setup, CI/CD verification

```bash
# Start with dev profile
make dev

# Or full stack
make full
```

### Configuration Files

- `docker-compose.dev.yml` - Development setup
- `docker-compose.full.yml` - Full stack setup
- `docker-compose.yml` - Base configuration

### Advantages
- ✅ Closer to production environment
- ✅ Isolated dependencies
- ✅ Easy to share exact environment

### Disadvantages
- ❌ Slower rebuilds
- ❌ More complex debugging
- ❌ Higher resource usage

---

## 3. Testing Production Docker Images

**Best for:** Verifying Dockerfile changes before publishing

### Build Locally

```bash
# Build production image for your platform only
make docker-build-local
```

This creates two tags:
- `lfnovo/open_notebook:<version>` (from pyproject.toml)
- `lfnovo/open_notebook:local`

### Run Locally

```bash
docker run -p 5055:5055 -p 3000:3000 lfnovo/open_notebook:local
```

### When to Use
- ✅ Before pushing to registry
- ✅ Testing Dockerfile changes
- ✅ Debugging production-specific issues
- ✅ Verifying build process

---

## 4. Publishing Docker Images

### Workflow

```bash
# 1. Test locally first
make docker-build-local

# 2. If successful, push version tag (no latest update)
make docker-push

# 3. Test the pushed version in staging/production

# 4. When ready, promote to latest
make docker-push-latest
```

### Available Commands

| Command | What It Does | Updates Latest? |
|---------|--------------|-----------------|
| `make docker-build-local` | Build for current platform only | No registry push |
| `make docker-push` | Push version tags to registries | ❌ No |
| `make docker-push-latest` | Push version + update v1-latest | ✅ Yes |
| `make docker-release` | Full release (same as docker-push-latest) | ✅ Yes |

### Publishing Details

- **Platforms:** `linux/amd64`, `linux/arm64`
- **Registries:** Docker Hub + GitHub Container Registry
- **Image Variants:** Regular + Single-container (`-single`)
- **Version Source:** `pyproject.toml`

### Creating Git Tags

```bash
# Create and push git tag matching pyproject.toml version
make tag
```

---

## Code Quality

```bash
# Run linter with auto-fix
make ruff

# Run type checking
make lint

# Run tests
uv run pytest tests/

# Clean cache directories
make clean-cache
```

---

## Common Development Tasks

### Adding a New Feature

1. Create feature branch
2. Develop using `./dev-init.sh`
3. Write tests
4. Run `make ruff` and `make lint`
5. Test with `make docker-build-local`
6. Create PR

### Fixing a Bug

1. Reproduce locally with `./dev-init.sh`
2. Add test case demonstrating bug
3. Fix the bug
4. Verify test passes
5. Check with `make docker-build-local`

### Updating Dependencies

```bash
# Add Python dependency
uv add package-name

# Update dependencies
uv sync

# Frontend dependencies
cd frontend && npm install package-name
```

### Adding a New Language (i18n)

Open Notebook supports internationalization. To add a new language:

1. **Create locale file**: Copy an existing locale as template
   ```bash
   cp frontend/src/lib/locales/en-US/index.ts frontend/src/lib/locales/pt-BR/index.ts
   ```

2. **Translate all strings** in the new file. The structure includes:
   - `common`: Shared UI elements (buttons, labels)
   - `notebooks`, `sources`, `notes`: Feature-specific strings
   - `chat`, `search`, `podcasts`: Module-specific strings
   - `apiErrors`: Error message translations

3. **Register the locale** in `frontend/src/lib/locales/index.ts`:
   ```typescript
   import { ptBR } from './pt-BR'

   export const locales = {
     'en-US': enUS,
     'zh-CN': zhCN,
     'zh-TW': zhTW,
     'pt-BR': ptBR,  // Add your locale
   }
   ```

4. **Add date-fns locale** in `frontend/src/lib/utils/date-locale.ts`:
   ```typescript
   import { zhCN, enUS, zhTW, ptBR } from 'date-fns/locale'

   const LOCALE_MAP: Record<string, Locale> = {
     'zh-CN': zhCN,
     'zh-TW': zhTW,
     'en-US': enUS,
     'pt-BR': ptBR,  // Add your locale
   }
   ```

5. **Test**: Switch languages using the language toggle in the UI header.

### Database Migrations

Database migrations run **automatically** when the API starts.

1. Create migration file: `migrations/XXX_description.surql`
2. Write SurrealQL schema changes
3. (Optional) Create rollback: `migrations/XXX_description_down.surql`
4. Restart API - migration runs on startup

---

## Troubleshooting

### Services Won't Start

```bash
# Check status
make status

# Check listening ports
lsof -i :8000
lsof -i :5055
lsof -i :3000

# Restart everything
make stop-all
./dev-init.sh
```

### Port Already in Use

```bash
# Find process using port
lsof -i :5055
lsof -i :3000
lsof -i :8000

# Kill stuck processes
make stop-all
```

### Database Connection Issues

```bash
# Check connection settings in .env
grep '^SURREAL_' .env

# Verify something is listening on port 8000
lsof -i :8000

# If using a local binary, confirm it is v2
$HOME/Library/Caches/surrealdb/surreal_v3 version
```

### Docker Build Fails

```bash
# Clean Docker cache
docker builder prune

# Reset buildx
make docker-buildx-reset

# Try local build first
make docker-build-local
```

---

## Project Structure

```
lumina/
├── api/                    # FastAPI backend
├── frontend/               # Next.js React frontend
├── open_notebook/          # Python core library
│   ├── domain/            # Domain models
│   ├── graphs/            # LangGraph workflows
│   ├── ai/                # AI provider integration
│   └── database/          # SurrealDB operations + migrations
├── tests/                  # Test suite
├── docs/                   # User documentation
├── dev-init.sh             # Preferred local non-Docker startup script
└── Makefile                # Development commands
```

See component-specific CLAUDE.md files for detailed architecture:
- [frontend/CLAUDE.md](frontend/CLAUDE.md)
- [api/CLAUDE.md](api/CLAUDE.md)
- [open_notebook/CLAUDE.md](open_notebook/CLAUDE.md)

---

## Environment Variables

### Required for Local Development

```bash
# .env file
SURREAL_URL=ws://127.0.0.1:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=open_notebook
OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string

# Optional for local auth flow testing
EMAIL_PROVIDER=debug
ALLOW_PUBLIC_REGISTRATION=true
```

See [docs/5-CONFIGURATION/](docs/5-CONFIGURATION/) for complete configuration guide.

---

## Performance Tips

### Speed Up Local Development

1. **Use `./dev-init.sh`** instead of Docker for daily work
2. **Keep a SurrealDB 3.0.x instance available** between sessions for faster restarts
3. **Use `make docker-build-local`** only when testing Dockerfile changes
4. **Skip multi-platform builds** until ready to publish

### Reduce Resource Usage

```bash
# Stop unused services
make stop-all

# Clean up Docker
docker system prune -a

# Clean Python cache
make clean-cache
```

---

## TODO: Sections to Add

- [ ] Frontend development guide (hot reload, component structure)
- [ ] API development guide (adding endpoints, services)
- [ ] LangGraph workflow development
- [ ] Testing strategy and coverage
- [ ] Debugging tips (VSCode/PyCharm setup)
- [ ] CI/CD pipeline overview
- [ ] Release process checklist
- [ ] Common error messages and solutions

---

## Resources

- **Documentation:** https://open-notebook.ai
- **Discord:** https://discord.gg/37XJPXfz2w
- **Issues:** https://github.com/YinHour/lumina/issues
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Maintainer Guide:** [MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md)

---

**Last Updated:** April 2026
