# Security Configuration

Protect your Open Notebook deployment with the built-in authentication system and production hardening.

---

## API Key Encryption

Open Notebook encrypts API keys stored in the database using Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).

### Configuration Methods

| Method | Documentation |
|--------|---------------|
| **Settings UI** | [API Configuration Guide](../3-USER-GUIDE/api-configuration.md) |
| **Environment Variables** | This page (below) |

### Setup

Set the encryption key to any secret string:

```bash
# .env or docker.env
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-passphrase
```

Any string works — it will be securely derived via SHA-256 internally. Use a strong passphrase for production deployments.

### Default Credentials

| Setting | Default | Security Level |
|---------|---------|----------------|
| Username/password login | No default database user is guaranteed | Configure during setup |
| Legacy password mode | Disabled unless `OPEN_NOTEBOOK_PASSWORD` is set | Backward compatibility only |
| Encryption Key | **None** (must be configured) | Required for API key storage |

**The encryption key has no default.** You must set `OPEN_NOTEBOOK_ENCRYPTION_KEY` before using the API key configuration feature. Without it, encrypting/decrypting API keys will fail.

### Docker Secrets Support

Both settings support Docker secrets via `_FILE` suffix:

```yaml
environment:
  - OPEN_NOTEBOOK_PASSWORD_FILE=/run/secrets/app_password
  - OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
```

### Security Notes

| Scenario | Behavior |
|----------|----------|
| Key configured | API keys encrypted with your key |
| No key configured | Encryption/decryption will fail (key is required) |
| Key changed | Old encrypted keys become unreadable |
| Legacy data | Unencrypted keys still work (graceful fallback) |

### Key Management

- **Keep secret**: Never commit the encryption key to version control
- **Backup securely**: Store the key separately from database backups
- **No rotation yet**: Changing the key requires re-saving all API keys
- **Per-deployment**: Each instance should have its own encryption key

---

## When to Use Built-in Authentication

### Use it for:
- Public cloud deployments (PikaPods, Railway, DigitalOcean)
- Shared network environments
- Any deployment accessible beyond localhost

### You can skip it for:
- Local development on your machine
- Private, isolated networks
- Single-user local setups

---

## Quick Setup

### Docker Deployment

```yaml
# Add to your docker-compose.yml (requires surrealdb service, see installation guide)
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    pull_policy: always
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-encryption-key
    # ... rest of config
```

Or using environment file:

```bash
# docker.env
OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-encryption-key
```

> **Important**: The encryption key is **required** for credential storage. Without it, you cannot save AI provider credentials via the Settings UI. If you change or lose the encryption key, all stored credentials become unreadable.

### Legacy Password Mode (optional)

```bash
# .env
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

If this variable is set, the middleware accepts `Authorization: Bearer <password>` and gives legacy mode priority over database JWT auth.

---

## Legacy Password Requirements

### Good Passwords

```bash
# Strong: 20+ characters, mixed case, numbers, symbols
OPEN_NOTEBOOK_PASSWORD=MySecure2024!Research#Tool
OPEN_NOTEBOOK_PASSWORD=Notebook$Dev$2024$Strong!

# Generated (recommended)
OPEN_NOTEBOOK_PASSWORD=$(openssl rand -base64 24)
```

### Bad Passwords

```bash
# DON'T use these
OPEN_NOTEBOOK_PASSWORD=password123
OPEN_NOTEBOOK_PASSWORD=opennotebook
OPEN_NOTEBOOK_PASSWORD=admin
```

---

## How It Works

### Frontend Protection

1. Users sign in with username + password
2. `/api/auth/login` returns a JWT token
3. The frontend stores the token and sends `Authorization: Bearer <jwt>` to protected endpoints
4. Additional flows may include `/register`, `/forgot-password`, and password change
5. Legacy deployments may still use one shared password if `OPEN_NOTEBOOK_PASSWORD` is set

### API Protection

Protected API endpoints require either a JWT or, in legacy mode, the shared password:

```bash
# Login first
curl -X POST http://localhost:5055/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Authenticated request with JWT
curl -H "Authorization: Bearer <jwt-token>" \
  http://localhost:5055/api/notebooks

# Unauthenticated (will fail)
curl http://localhost:5055/api/notebooks
# Returns: {"detail": "Missing authorization header"}
```

### Unprotected Endpoints

These work without authentication:

- `/health` - System health check
- `/docs` - API documentation
- `/openapi.json` - OpenAPI spec

---

## API Authentication Examples

### curl

```bash
# Check auth mode
curl http://localhost:5055/api/auth/status

# Login
curl -X POST http://localhost:5055/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# List notebooks
curl -H "Authorization: Bearer <jwt-token>" \
  http://localhost:5055/api/notebooks

# Create notebook
curl -X POST \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Notebook", "description": "Research notes"}' \
  http://localhost:5055/api/notebooks

# Upload file
curl -X POST \
  -H "Authorization: Bearer <jwt-token>" \
  -F "file=@document.pdf" \
  http://localhost:5055/api/sources/upload
```

### Python

```python
import requests

class OpenNotebookClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_notebooks(self):
        response = requests.get(
            f"{self.base_url}/api/notebooks",
            headers=self.headers
        )
        return response.json()

    def create_notebook(self, name: str, description: str = None):
        response = requests.post(
            f"{self.base_url}/api/notebooks",
            headers=self.headers,
            json={"name": name, "description": description}
        )
        return response.json()

# Usage
client = OpenNotebookClient("http://localhost:5055", "your_jwt_token")
notebooks = client.get_notebooks()
```

### JavaScript/TypeScript

```javascript
const API_URL = 'http://localhost:5055';
const TOKEN = 'your-jwt-token';

async function getNotebooks() {
  const response = await fetch(`${API_URL}/api/notebooks`, {
    headers: {
      'Authorization': `Bearer ${TOKEN}`
    }
  });
  return response.json();
}
```

---

## Production Hardening

### Docker Security

```yaml
# Add to your docker-compose.yml (requires surrealdb service, see installation guide)
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    pull_policy: always
    ports:
      - "127.0.0.1:8502:8502"  # Bind to localhost only
    environment:
      - OPEN_NOTEBOOK_PASSWORD=your_secure_password
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    restart: always
```

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8502/tcp   # Block direct access
sudo ufw deny 5055/tcp   # Block direct API access
sudo ufw enable

# iptables
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 8502 -j DROP
iptables -A INPUT -p tcp --dport 5055 -j DROP
```

### Reverse Proxy with SSL

See [Reverse Proxy Configuration](reverse-proxy.md) for complete nginx/Caddy/Traefik setup with HTTPS.

---

## Security Limitations

Open Notebook's built-in authentication provides a practical self-hosted baseline, not enterprise-grade IAM:

| Feature | Status |
|---------|--------|
| Password transmission | Protected by JWT bearer auth or legacy Bearer password (use HTTPS!) |
| Password storage | Database-backed bcrypt hashes in current auth flow |
| User management | Database users supported; advanced RBAC not built in |
| Session timeout | JWT expiry applies |
| Rate limiting | None |
| Audit logging | None |

### Risk Mitigation

1. **Always use HTTPS** - Encrypt traffic with TLS
2. **Strong passwords** - 20+ characters, complex
3. **Network security** - Firewall, VPN for sensitive deployments
4. **Regular updates** - Keep containers and dependencies updated
5. **Monitoring** - Check logs for suspicious activity
6. **Backups** - Regular backups of data

---

## Enterprise Considerations

For deployments requiring advanced security:

| Need | Solution |
|------|----------|
| SSO/OAuth | Implement OAuth2/SAML proxy |
| Role-based access | Custom middleware |
| Audit logging | Log aggregation service |
| Rate limiting | API gateway or nginx |
| Data encryption | Encrypt volumes at rest |
| Network segmentation | Docker networks, VPC |

---

## Troubleshooting

### Password / Login Issues

```bash
# Check env var is set if using legacy shared-password mode
docker exec open-notebook env | grep OPEN_NOTEBOOK_PASSWORD

# Check logs
docker logs open-notebook | grep -i auth

# Check auth mode and login flow
curl http://localhost:5055/api/auth/status
curl -X POST http://localhost:5055/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### 401 Unauthorized Errors

```bash
# Check header format
curl -v -H "Authorization: Bearer <jwt-token>" \
  http://localhost:5055/api/notebooks

# Verify legacy shared password if that mode is enabled
echo "Password length: $(echo -n $OPEN_NOTEBOOK_PASSWORD | wc -c)"
```

### Cannot Access After Setting Password

1. Clear browser cache and cookies
2. Try incognito/private mode
3. Check browser console for errors
4. Verify whether your deployment expects JWT login or legacy `OPEN_NOTEBOOK_PASSWORD`
5. Check `GET /api/auth/status` for the active mode

### Security Testing

```bash
# Without authentication (should fail when auth is enabled)
curl http://localhost:5055/api/notebooks
# Expected: {"detail": "Missing authorization header"}

# With correct JWT (should succeed)
curl -H "Authorization: Bearer <jwt-token>" \
  http://localhost:5055/api/notebooks

# Legacy mode alternative
curl -H "Authorization: Bearer your_shared_password" \
  http://localhost:5055/api/notebooks

# Health check (should work without authentication)
curl http://localhost:5055/health
```

---

## Reporting Security Issues

If you discover security vulnerabilities:

1. **Do NOT open public issues**
2. Contact maintainers directly
3. Provide detailed information
4. Allow time for fixes before disclosure

---

## Related

- **[Reverse Proxy](reverse-proxy.md)** - HTTPS and SSL setup
- **[Advanced Configuration](advanced.md)** - Ports, timeouts, and SSL settings
- **[Environment Reference](environment-reference.md)** - All configuration options
