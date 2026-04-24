# Local Development Setup

This guide walks you through setting up Open Notebook for local development. Follow these steps to get the full stack running on your machine.

## Prerequisites

Before you start, ensure you have the following installed:

- **Python 3.11+** - Check with: `python --version`
- **uv** (recommended) or **pip** - Install from: https://github.com/astral-sh/uv
- **SurrealDB v2** - Via local binary or Docker (v2 is required for current migrations)
- **Docker** (optional) - Only if you want a containerized database instead of the preferred local workflow
- **Node.js 18+** (optional) - For frontend development
- **Git** - For version control

## Step 1: Clone and Initial Setup

```bash
# Clone the repository
git clone https://github.com/YinHour/lumina.git
cd lumina

# Add upstream remote for keeping your fork updated
git remote add upstream https://github.com/lfnovo/open-notebook.git
```

## Step 2: Install Python Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Step 3: Environment Variables

Create a `.env` file in the project root with your configuration:

```bash
# Copy from example
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Database
SURREAL_URL=ws://127.0.0.1:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=open_notebook

# Credential encryption (required for storing API keys)
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-dev-secret-key

# Optional for auth flow testing
EMAIL_PROVIDER=debug
ALLOW_PUBLIC_REGISTRATION=true

# Application
DEBUG=true
LOG_LEVEL=DEBUG
```

### AI Provider Configuration

After starting the API and frontend, configure your AI provider via the Settings UI:

1. Open **http://localhost:3000** → **Settings** → **API Keys**
2. Click **Add Credential** → Select your provider
3. Enter your API key (get from provider dashboard)
4. Click **Save**, then **Test Connection**
5. Click **Discover Models** → **Register Models**

Popular providers:
- **OpenAI** - https://platform.openai.com/api-keys
- **Anthropic (Claude)** - https://console.anthropic.com/
- **Google** - https://ai.google.dev/
- **Groq** - https://console.groq.com/

For local development, you can also use:
- **Ollama** - Run locally without API keys (see "Local Ollama" below)

> **Note:** API key environment variables (e.g., `OPENAI_API_KEY`) are deprecated. Use the Settings UI to manage credentials instead.

## Step 4: Start the local development stack (recommended)

For daily Lumina development, use the one-command local workflow:

```bash
./dev-init.sh
```

This script:

1. Loads `.env`
2. Reuses an existing SurrealDB instance or auto-starts a local SurrealDB v2 binary
3. Starts the API on port 5055
4. Waits for `GET /api/auth/status` to become healthy
5. Starts the worker and frontend
6. Cleans up processes it started when you press `Ctrl+C`

Optional overrides:

```bash
FRONTEND_PORT=3001 ./dev-init.sh
START_LOCAL_SURREAL=false ./dev-init.sh
LOCAL_SURREAL_BINARY=$HOME/Library/Caches/surrealdb/surreal_v2 ./dev-init.sh
```

## Step 5: Start SurrealDB manually (optional advanced workflow)

### Option A: Using local SurrealDB v2 binary

```bash
$HOME/Library/Caches/surrealdb/surreal_v2 start \
  --log info \
  --bind 127.0.0.1:8000 \
  --user root \
  --pass root \
  rocksdb:./.dev-data/surreal
```

### Option B: Using Docker

```bash
# Start SurrealDB in memory
docker run -d --name surrealdb -p 8000:8000 \
  surrealdb/surrealdb:v2 start \
  --user root --pass password \
  --bind 0.0.0.0:8000 memory

# Or with persistent storage
docker run -d --name surrealdb -p 8000:8000 \
  -v surrealdb_data:/data \
  surrealdb/surrealdb:v2 start \
  --user root --pass password \
  --bind 0.0.0.0:8000 file:/data/surreal.db
```

### Option C: Using Make

```bash
make database
```

### Option D: Using Docker Compose

```bash
docker compose up -d surrealdb
```

### Verify SurrealDB is Running

```bash
# Should show server information
curl http://localhost:8000/
```

## Step 6: Run Database Migrations

Database migrations run automatically when you start the API. The first startup will apply any pending migrations.

To verify migrations manually:

```bash
# API will run migrations on startup
uv run python -m api.main
```

Check the logs - you should see messages like:
```
Running migration 001_initial_schema
Running migration 002_add_vectors
...
Migrations completed successfully
```

## Step 7: Start the API Server

In a new terminal window:

```bash
# Terminal 2: Start API (port 5055)
uv run --env-file .env run_api.py

# Or using the shortcut
make api
```

You should see:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:5055
```

### Verify API is Running

```bash
# Check health endpoint
curl http://localhost:5055/health

# View API documentation
open http://localhost:5055/docs
```

## Step 8: Start the Frontend (Optional)

If you want to work on the frontend, start Next.js in another terminal:

```bash
# Terminal 3: Start Next.js frontend (port 3000)
cd frontend
npm install  # First time only
npm run dev
```

You should see:
```
> next dev
  ▲ Next.js 16.x
  - Local:        http://localhost:3000
```

### Access the Frontend

Open your browser to: http://localhost:3000

## Verification Checklist

After setup, verify everything is working:

- [ ] **SurrealDB**: `curl http://localhost:8000/` returns content
- [ ] **API health**: `curl http://localhost:5055/health` returns `{"status": "healthy"}`
- [ ] **Auth status**: `curl http://localhost:5055/api/auth/status` returns JSON
- [ ] **API Docs**: `open http://localhost:5055/docs` works
- [ ] **Database**: API logs show migrations completing
- [ ] **Frontend** (optional): `http://localhost:3000` loads

## Authentication flows available during development

The current auth system is no longer a single password page only.

- `/login` → username + password login
- `/register` → public registration when `ALLOW_PUBLIC_REGISTRATION=true`
- `/forgot-password` → email verification code + password reset
- `/api/auth/status` → reports whether auth is disabled, legacy, or database-backed

For local verification without real email delivery, set `EMAIL_PROVIDER=debug` and read the generated verification code from the API log.

## Starting Services Together

### Quick Start All Services

```bash
./dev-init.sh
```

This is the preferred all-in-one local startup command for Lumina.

### Individual Terminals (Recommended for Development)

**Terminal 1 - Database:**
```bash
make database
```

**Terminal 2 - API:**
```bash
make api
```

**Terminal 3 - Frontend:**
```bash
cd frontend && npm run dev
```

## Development Tools Setup

### Pre-commit Hooks (Optional but Recommended)

Install git hooks to automatically check code quality:

```bash
uv run pre-commit install
```

Now your commits will be checked before they're made.

### Code Quality Commands

```bash
# Lint Python code (auto-fix)
make ruff
# or: ruff check . --fix

# Type check Python code
make lint
# or: uv run python -m mypy .

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=open_notebook
```

## Common Development Tasks

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_notebooks.py

# Run with coverage report
uv run pytest --cov=open_notebook --cov-report=html
```

### Creating a Feature Branch

```bash
# Create and switch to new branch
git checkout -b feature/my-feature

# Make changes, then commit
git add .
git commit -m "feat: add my feature"

# Push to your fork
git push origin feature/my-feature
```

### Updating from Upstream

```bash
# Fetch latest changes
git fetch upstream

# Rebase your branch
git rebase upstream/main

# Push updated branch
git push origin feature/my-feature -f
```

## Troubleshooting

### "Connection refused" on SurrealDB

**Problem**: API can't connect to SurrealDB

**Solutions**:
1. Check if SurrealDB is running: `lsof -i :8000`
2. Verify URL in `.env`: Should be `ws://127.0.0.1:8000/rpc`
3. Confirm you are using SurrealDB v2, not v3
4. Restart with `./dev-init.sh` or start the local v2 binary manually

### "Address already in use"

**Problem**: Port 5055 or 3000 is already in use

**Solutions**:
```bash
# Find process using port
lsof -i :5055  # Check port 5055

# Kill process (macOS/Linux)
kill -9 <PID>

# Or use different port
uvicorn api.main:app --port 5056
```

### Module not found errors

**Problem**: Import errors when running API

**Solutions**:
```bash
# Reinstall dependencies
uv sync

# Or with pip
pip install -e .
```

### Database migration failures

**Problem**: API fails to start with migration errors

**Solutions**:
1. Check SurrealDB is running: `curl http://localhost:8000/`
2. Check credentials in `.env` match your SurrealDB setup
3. Check logs for specific migration error: `make api 2>&1 | grep -i migration`
4. Verify database exists: Check SurrealDB console at http://localhost:8000/

### Migrations not applying

**Problem**: Database schema seems outdated

**Solutions**:
1. Restart API - migrations run on startup: `make api`
2. Check logs show "Migrations completed successfully"
3. Verify `/migrations/` folder exists and has files
4. Check SurrealDB is writable and not in read-only mode

## Optional: Local Ollama Setup

For testing with local AI models:

```bash
# Install Ollama from https://ollama.ai

# Pull a model (e.g., Mistral 7B)
ollama pull mistral
```

Then configure via the Settings UI:
1. Go to **Settings** → **API Keys** → **Add Credential** → **Ollama**
2. Enter base URL: `http://localhost:11434`
3. Click **Save**, then **Test Connection**
4. Click **Discover Models** → **Register Models**

## Optional: Docker Development Environment

Run entire stack in Docker:

```bash
# Start all services
docker compose --profile multi up

# Logs
docker compose logs -f

# Stop services
docker compose down
```

## Next Steps

After setup is complete:

1. **Read the Contributing Guide** - [contributing.md](contributing.md)
2. **Explore the Architecture** - Check the documentation
3. **Find an Issue** - Look for "good first issue" on GitHub
4. **Set Up Pre-commit** - Install git hooks for code quality
5. **Join Discord** - https://discord.gg/37XJPXfz2w

## Getting Help

If you get stuck:

- **Discord**: [Join our server](https://discord.gg/37XJPXfz2w) for real-time help
- **GitHub Issues**: Check existing issues for similar problems
- **GitHub Discussions**: Ask questions in discussions
- **Documentation**: See [code-standards.md](code-standards.md) and [testing.md](testing.md)

---

**Ready to contribute?** Go to [contributing.md](contributing.md) for the contribution workflow.
