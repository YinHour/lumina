# From Source Installation

Clone the repository and run locally. **For developers and contributors.**

## Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Git** - [Download](https://git-scm.com/)
- **SurrealDB v2 binary or Docker** (v2 is required for current migrations)
- **uv** (Python package manager) - `curl -LsSf https://astral.sh/uv/install.sh | sh`
- API key from OpenAI or similar (or use Ollama for free)

## Quick Setup (10 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/YinHour/lumina.git
cd lumina

# If you forked it:
git clone https://github.com/YOUR_USERNAME/open-notebook.git
cd open-notebook
git remote add upstream https://github.com/lfnovo/open-notebook.git
```

### 2. Install Python Dependencies

```bash
uv sync
uv pip install python-magic
```

#### 2.1 Alternative: Conda Setup (Optional)

If you prefer using **Conda** to manage your environments, follow these steps instead of the standard `uv sync`:

```bash
# Create and activate the environment
conda create -n open-notebook python=3.11 -y
conda activate open-notebook

# Install uv inside conda to maintain compatibility with the Makefile
conda install -c conda-forge uv nodejs -y

# Sync dependencies
uv sync
```

> **Note**: Installing `uv` inside your Conda environment ensures the current local workflow (`./dev-init.sh`, `make api`, and related helper commands) continues to work seamlessly.

### 3. Start the local dev stack (recommended)

```bash
cp .env.example .env
./dev-init.sh
```

This is the preferred contributor workflow. The script starts the API, worker, and frontend, and auto-starts a local SurrealDB v2 instance if needed.

### 4. Start SurrealDB manually (optional)

```bash
# Terminal 1
make database
# or: docker compose up surrealdb
```

### 5. Set Environment Variables

```bash
cp .env.example .env
# Edit .env and set:
# OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
# EMAIL_PROVIDER=debug
# ALLOW_PUBLIC_REGISTRATION=true
```

After starting the app, configure AI providers via the **Settings → API Keys** UI in the browser.

### 6. Start API

```bash
# Terminal 2
make api
# or: uv run --env-file .env run_api.py
```

### 7. Start Frontend

```bash
# Terminal 3
cd frontend && npm install && npm run dev
```

### 8. Access

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:5055/docs
- **Database**: http://localhost:8000

### 9. Verify authentication pages

- **Login**: http://localhost:3000/login
- **Register**: http://localhost:3000/register
- **Forgot password**: http://localhost:3000/forgot-password

If `EMAIL_PROVIDER=debug`, the verification code for registration/reset-password is written to the API log instead of being sent to a real email inbox.

### 10. Configure AI Provider

1. Open http://localhost:3000
2. Go to **Settings** → **API Keys**
3. Click **Add Credential** → Select your provider → Paste API key
4. Click **Save**, then **Test Connection**
5. Click **Discover Models** → **Register Models**

---

## Development Workflow

### Code Quality

```bash
# Format and lint Python
make ruff
# or: ruff check . --fix

# Type checking
make lint
# or: uv run python -m mypy .
```

### Run Tests

```bash
uv run pytest tests/
```

### Common Commands

```bash
# Start everything
./dev-init.sh

# View API docs
open http://localhost:5055/docs

# Check database migrations
# (Auto-run on API startup)

# Clean up
make clean
```

---

## Troubleshooting

### Python version too old

```bash
python --version  # Check version
uv sync --python 3.11  # Use specific version
```

### npm: command not found

Install Node.js from https://nodejs.org/

### Database connection errors

```bash
lsof -i :8000  # Check SurrealDB or local binary is listening
grep '^SURREAL_' .env
```

### Port 5055 already in use

```bash
# Use different port
uv run uvicorn api.main:app --port 5056
```

---

## Next Steps

1. Read [Development Guide](../7-DEVELOPMENT/quick-start.md)
2. See [Architecture Overview](../7-DEVELOPMENT/architecture.md)
3. Check [Contributing Guide](../7-DEVELOPMENT/contributing.md)

---

## Getting Help

- **Discord**: [Community](https://discord.gg/37XJPXfz2w)
- **Issues**: [GitHub Issues](https://github.com/YinHour/lumina/issues)
