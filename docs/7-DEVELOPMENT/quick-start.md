# Quick Start - Development

Get Lumina running locally in 5 minutes.

## Prerequisites

- **Python 3.11+**
- **Git**
- **uv** (package manager) - install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **SurrealDB v2 binary or Docker** (optional if you let `./dev-init.sh` auto-start the local binary)

## 1. Clone the Repository (2 min)

```bash
# Fork the repository on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/lumina.git
cd lumina

# Add upstream remote for updates
git remote add upstream https://github.com/lfnovo/open-notebook.git
```

## 2. Install Dependencies (2 min)

```bash
# Install Python dependencies
uv sync

# Verify uv is working
uv --version
```

## 3. Start Services (1 min)

```bash
cp .env.example .env
./dev-init.sh
```

Recommended local test flags in `.env`:

```bash
EMAIL_PROVIDER=debug
ALLOW_PUBLIC_REGISTRATION=true
```

For real SMTP or Resend delivery, see
[Email Verification](../5-CONFIGURATION/environment-reference.md#email-verification).

## 4. Verify Everything Works (instant)

- **API Health**: http://localhost:5055/health → should return `{"status": "healthy"}`
- **Auth Status**: http://localhost:5055/api/auth/status → should return JSON
- **API Docs**: http://localhost:5055/docs → interactive API documentation
- **Frontend**: http://localhost:3000 → Open Notebook UI

You can also verify the auth UI routes:

- http://localhost:3000/login
- http://localhost:3000/register
- http://localhost:3000/forgot-password

**All three show up?** ✅ You're ready to develop!

---

## Next Steps

- **First Issue?** Pick a [good first issue](https://github.com/YinHour/lumina/issues?q=label%3A%22good+first+issue%22)
- **Understand the code?** Read [Architecture Overview](architecture.md)
- **Make changes?** Follow [Contributing Guide](contributing.md)
- **Setup details?** See [Development Setup](development-setup.md)

---

## Troubleshooting

### "Port 5055 already in use"
```bash
# Find what's using the port
lsof -i :5055

# Use a different port
uv run uvicorn api.main:app --port 5056
```

### "Can't connect to SurrealDB"
```bash
# Check if SurrealDB is running
docker ps | grep surrealdb

# Restart it
make database
```

### "Python version is too old"
```bash
# Check your Python version
python --version  # Should be 3.11+

# Use Python 3.11 specifically
uv sync --python 3.11
```

### "npm: command not found"
```bash
# Install Node.js from https://nodejs.org/
# Then install frontend dependencies
cd frontend && npm install
```

---

## Common Development Commands

```bash
# Run tests
uv run pytest

# Format code
make ruff

# Type checking
make lint

# Run the full stack
./dev-init.sh

# View API documentation
open http://localhost:5055/docs
```

---

Need more help? See [Development Setup](development-setup.md) for details or join our [Discord](https://discord.gg/37XJPXfz2w).
