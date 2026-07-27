# Multi-Instance Dokploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring up a second Telegram MCP Dokploy server from the same GitHub repo while making future tool updates easy to distribute to every account instance.

**Architecture:** Keep the Python MCP server single-account per process. Add non-secret account identity to the shared server, document the multi-instance Dokploy model, and deploy a second Dokploy app using the same Dockerfile with account-specific environment variables.

**Tech Stack:** Python 3.10+, Telethon, MCP Python SDK FastMCP, Starlette, Uvicorn, Docker, Dokploy, Cloudflare Access, GitHub, pytest.

## Global Constraints

- Keep one shared repository and one Dockerfile for all Telegram account servers.
- Run one Dokploy application per Telegram account.
- Do not add runtime account switching inside one process.
- Do not add `account` parameters to all Telegram tools.
- Do not commit Telegram session strings, MCP bearer tokens, Cloudflare Access secrets, Dokploy API keys, or Infisical values.
- The existing live public domain remains `tg-mcp.351hub.space`.
- The second instance name is `telegram-mcp-main`.
- The second public domain is `tg-mcp-main.351hub.space`.
- The second MCP endpoint path is `/mcp`.
- The app port remains `8000`.
- The HTTP transport remains `streamable-http`.

---

## File Structure

- Modify `main.py`: read `TELEGRAM_ACCOUNT_NAME`, include it in health/server diagnostics, and expose a small read-only MCP diagnostic tool.
- Modify `test_auth_middleware.py`: add coverage for health account identity and auth bypass behavior.
- Modify `docs/dokploy.env.example`: include `TELEGRAM_ACCOUNT_NAME` and show the second-instance host convention.
- Modify `docs/dokploy-runbook.md`: document the one-repo/many-Dokploy-apps model, second-app setup, and redeploy flow for distributing tool changes.
- Create `docs/docker-compose.multi-instance.example.yml`: provide a non-secret local reference for running two instances from the same image.

## Task 1: Add Account Identity Diagnostics

**Files:**
- Modify: `main.py`
- Modify: `test_auth_middleware.py`

**Interfaces:**
- Consumes: environment variable `TELEGRAM_ACCOUNT_NAME`.
- Produces: constant `TELEGRAM_ACCOUNT_NAME: str`.
- Produces: function `_server_info_payload() -> dict[str, str]`.
- Produces: MCP tool `get_server_info() -> str`.
- Produces: `/health` response shape `{"status": "ok", "account_name": "<name>", "transport": "<transport>"}`.

- [ ] **Step 1: Write failing tests for account identity payload and health**

Add these imports to `test_auth_middleware.py`:

```python
from main import _healthcheck, _server_info_payload
```

Add these tests to `test_auth_middleware.py`:

```python
def test_server_info_payload_includes_account_name(monkeypatch):
    monkeypatch.setattr("main.TELEGRAM_ACCOUNT_NAME", "main")
    monkeypatch.setattr("main.MCP_TRANSPORT", "streamable-http")

    assert _server_info_payload() == {
        "account_name": "main",
        "transport": "streamable-http",
    }


def test_server_info_payload_defaults_blank_account_to_telegram(monkeypatch):
    monkeypatch.setattr("main.TELEGRAM_ACCOUNT_NAME", "")
    monkeypatch.setattr("main.MCP_TRANSPORT", "streamable-http")

    assert _server_info_payload()["account_name"] == "telegram"


def test_healthcheck_includes_account_identity():
    client = TestClient(Starlette(routes=[Route("/health", _healthcheck, methods=["GET"])]))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "account_name" in body
    assert body["transport"] == "streamable-http"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest test_auth_middleware.py -v
```

Expected: FAIL because `_server_info_payload` does not exist and `/health` only returns `{"status": "ok"}`.

- [ ] **Step 3: Implement account identity in `main.py`**

Add this after `MCP_ALLOWED_HOSTS_RAW` is defined:

```python
TELEGRAM_ACCOUNT_NAME = os.getenv("TELEGRAM_ACCOUNT_NAME", "telegram").strip()
```

Add this helper near `_healthcheck`:

```python
def _server_info_payload() -> dict[str, str]:
    return {
        "account_name": TELEGRAM_ACCOUNT_NAME or "telegram",
        "transport": MCP_TRANSPORT,
    }
```

Change `_healthcheck` to:

```python
async def _healthcheck(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", **_server_info_payload()})
```

Add this MCP tool near `get_me` or near the health/server startup helpers:

```python
@mcp.tool(annotations=ToolAnnotations(title="Get Server Info", openWorldHint=True, readOnlyHint=True))
async def get_server_info() -> str:
    """Return non-secret diagnostics for this Telegram MCP server instance."""
    return json.dumps(_server_info_payload(), indent=2)
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest test_auth_middleware.py -v
```

Expected: PASS.

- [ ] **Step 5: Run the broader existing test set**

Run:

```bash
uv run pytest test_auth_middleware.py test_validation.py test_file_path_security.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit account identity diagnostics**

Run:

```bash
git add main.py test_auth_middleware.py
git commit -m "feat: add Telegram MCP instance identity"
```

## Task 2: Document Multi-Instance Dokploy Configuration

**Files:**
- Modify: `docs/dokploy.env.example`
- Modify: `docs/dokploy-runbook.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `TELEGRAM_ACCOUNT_NAME` from Task 1.
- Produces: documented second-instance environment convention.
- Produces: documented redeploy procedure for distributing new tools to all apps.

- [ ] **Step 1: Update env example**

Replace `docs/dokploy.env.example` with this non-secret example:

```dotenv
TELEGRAM_ACCOUNT_NAME=main
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
TELEGRAM_SESSION_STRING=your_generated_session_string_here
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_PATH=/mcp
MCP_BEARER_TOKEN=replace_with_strong_random_token
MCP_ALLOWED_HOSTS=localhost,localhost:8000,tg-mcp-main.351hub.space,tg-mcp-main.351hub.space:443
```

- [ ] **Step 2: Update Dokploy runbook required variables**

In `docs/dokploy-runbook.md`, add `TELEGRAM_ACCOUNT_NAME` to the required environment variable list above `TELEGRAM_API_ID`.

Add this text after the required variable list:

```markdown
For multiple Telegram accounts, create one Dokploy application per account. Each application uses the same GitHub repository, branch, Dockerfile, and port. Only the environment variables, domain, and bearer token differ.

Recommended app/domain pairs:

| Account | Dokploy app | Domain |
| --- | --- | --- |
| Existing account | existing Dokploy app | `tg-mcp.351hub.space` |
| New main account | `telegram-mcp-main` | `tg-mcp-main.351hub.space` |
```

- [ ] **Step 3: Add second app setup section to runbook**

Add this section after "Create application in Dokploy":

```markdown
## 3. Create the second account application

Use the same source settings as the first app:

- Source: the same GitHub fork and branch as the first app
- Build type: `dockerfile`
- Dockerfile path: `Dockerfile`
- Context path: `.`
- Port: `8000`
- Application name: `telegram-mcp-main`
- Domain: `tg-mcp-main.351hub.space`

Set account-specific environment variables:

```text
TELEGRAM_ACCOUNT_NAME=main
TELEGRAM_SESSION_STRING=<second account session string>
MCP_BEARER_TOKEN=<second account bearer token>
MCP_ALLOWED_HOSTS=localhost,localhost:8000,tg-mcp-main.351hub.space,tg-mcp-main.351hub.space:443
```

Use the same `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` if both accounts use the same Telegram API application. Keep all secret values in Dokploy and/or Infisical, not in GitHub.
```

Renumber following sections so the runbook order stays sequential.

- [ ] **Step 4: Add tool distribution section to runbook**

Add this section before the current update-from-upstream section:

```markdown
## Distribute tool updates to all account servers

All account servers run the same code. To publish a new MCP tool or tool fix:

1. Implement the tool change once in this repository.
2. Run the test suite locally.
3. Push the branch to GitHub.
4. Redeploy the existing app for `tg-mcp.351hub.space`.
5. Redeploy `telegram-mcp-main`.
6. Check `https://tg-mcp.351hub.space/health` and `https://tg-mcp-main.351hub.space/health` with Cloudflare Access headers.
7. Call `get_server_info` and `get_me` through each MCP connection to confirm the connected account.

If Dokploy provides a bulk redeploy action for apps from the same repo revision, use it. Otherwise, redeploy each app manually.
```

- [ ] **Step 5: Add README deployment note**

Add this short note near the Docker/Dokploy setup area in `README.md`:

```markdown
### Multiple Telegram Accounts

Run one server instance per Telegram account. Each instance uses the same repository and Docker image, but has its own `TELEGRAM_SESSION_STRING`, `MCP_BEARER_TOKEN`, `TELEGRAM_ACCOUNT_NAME`, and domain. This keeps tool code shared while preventing runtime account mix-ups. See `docs/dokploy-runbook.md` for the Dokploy multi-instance setup.
```

- [ ] **Step 6: Verify docs contain no real secrets**

Run:

```bash
rg -n "TELEGRAM_SESSION_STRING=([^y]|$)|MCP_BEARER_TOKEN=([^r]|$)|CF-Access-Client-Secret: [^<]|x-api-key: [^<]" README.md docs/dokploy-runbook.md docs/dokploy.env.example
```

Expected: no output.

- [ ] **Step 7: Commit Dokploy docs**

Run:

```bash
git add README.md docs/dokploy-runbook.md docs/dokploy.env.example
git commit -m "docs: describe multi-instance Dokploy setup"
```

## Task 3: Add Local Multi-Instance Compose Reference

**Files:**
- Create: `docs/docker-compose.multi-instance.example.yml`

**Interfaces:**
- Consumes: Docker image built from the shared `Dockerfile`.
- Produces: a non-secret local example showing two services using the same image and different env files.

- [ ] **Step 1: Create compose example**

Create `docs/docker-compose.multi-instance.example.yml`:

```yaml
version: "3.8"

services:
  telegram-mcp-existing:
    build:
      context: ..
      dockerfile: Dockerfile
    container_name: telegram-mcp-existing
    env_file:
      - ../.env.existing
    environment:
      TELEGRAM_ACCOUNT_NAME: existing
      MCP_PORT: "8000"
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 20s
    restart: unless-stopped

  telegram-mcp-main:
    build:
      context: ..
      dockerfile: Dockerfile
    container_name: telegram-mcp-main
    env_file:
      - ../.env.main
    environment:
      TELEGRAM_ACCOUNT_NAME: main
      MCP_PORT: "8000"
    ports:
      - "127.0.0.1:8001:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 20s
    restart: unless-stopped
```

- [ ] **Step 2: Add runbook link to compose example**

Add this sentence to the local/Docker section of `docs/dokploy-runbook.md`:

```markdown
For a local two-account reference, see `docs/docker-compose.multi-instance.example.yml`. It intentionally points to `.env.existing` and `.env.main`, which must stay local and uncommitted.
```

- [ ] **Step 3: Verify compose syntax**

Run:

```bash
docker compose -f docs/docker-compose.multi-instance.example.yml config
```

Expected: command exits 0 and prints normalized compose config. It may warn that `version` is obsolete depending on the installed Docker Compose version; that warning is acceptable.

- [ ] **Step 4: Verify docs contain no real secrets**

Run:

```bash
rg -n "TELEGRAM_SESSION_STRING=([^y<]|$)|MCP_BEARER_TOKEN=([^r<]|$)|CF-Access-Client-Secret: [^<]|x-api-key: [^<]" docs/docker-compose.multi-instance.example.yml docs/dokploy-runbook.md
```

Expected: no output.

- [ ] **Step 5: Commit compose reference**

Run:

```bash
git add docs/docker-compose.multi-instance.example.yml docs/dokploy-runbook.md
git commit -m "docs: add local multi-instance compose example"
```

## Task 4: Push Shared Configuration to GitHub

**Files:**
- No file changes expected.

**Interfaces:**
- Consumes: commits from Tasks 1-3.
- Produces: GitHub branch containing account identity diagnostics and non-secret deployment docs.

- [ ] **Step 1: Run full focused verification**

Run:

```bash
uv run pytest test_auth_middleware.py test_validation.py test_file_path_security.py -v
docker compose -f docs/docker-compose.multi-instance.example.yml config
```

Expected: pytest passes, compose config exits 0.

- [ ] **Step 2: Check working tree before push**

Run:

```bash
git status --short
```

Expected: no uncommitted changes from Tasks 1-3. Existing unrelated worktree changes from before this plan may still appear; do not stage them unless they were intentionally modified by the tasks.

- [ ] **Step 3: Push the current branch**

Run:

```bash
git push
```

Expected: push succeeds to the configured GitHub remote for the current branch.

## Task 5: Generate Second Account Runtime Values

**Files:**
- No committed file changes.

**Interfaces:**
- Consumes: local Telegram API credentials in `.env` or shell environment.
- Produces: second account Telegram session string for Dokploy.
- Produces: second app MCP bearer token for Dokploy.

- [ ] **Step 1: Generate a strong bearer token without printing secrets**

Run:

```bash
SECOND_MCP_BEARER_TOKEN=$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)
test -n "$SECOND_MCP_BEARER_TOKEN"
```

Expected: exit 0. Do not echo the token.

- [ ] **Step 2: Generate the second Telegram session string**

Run:

```bash
uv run session_string_generator.py
```

Expected: the script prompts for the second Telegram account phone number and login code. Store the resulting session string directly in the second Dokploy app environment. Do not commit it and do not paste it into docs.

- [ ] **Step 3: Prepare second app environment values**

Use these values in Dokploy:

```text
TELEGRAM_ACCOUNT_NAME=main
TELEGRAM_API_ID=<same value used by the existing app>
TELEGRAM_API_HASH=<same value used by the existing app>
TELEGRAM_SESSION_STRING=<second account session string>
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_PATH=/mcp
MCP_BEARER_TOKEN=<value from SECOND_MCP_BEARER_TOKEN>
MCP_ALLOWED_HOSTS=localhost,localhost:8000,tg-mcp-main.351hub.space,tg-mcp-main.351hub.space:443
```

Expected: values are entered into Dokploy or Infisical without being committed to the repository.

## Task 6: Create and Verify the Second Dokploy App

**Files:**
- No committed file changes expected.

**Interfaces:**
- Consumes: GitHub branch pushed in Task 4.
- Consumes: second app environment values from Task 5.
- Produces: running Dokploy app `telegram-mcp-main`.
- Produces: HTTPS MCP endpoint `https://tg-mcp-main.351hub.space/mcp`.

- [ ] **Step 1: Create Dokploy app**

In Dokploy, create application `telegram-mcp-main` using:

```text
Source: same GitHub fork and branch as the existing Telegram MCP app
Build type: dockerfile
Dockerfile path: Dockerfile
Context path: .
Port: 8000
Domain: tg-mcp-main.351hub.space
```

Expected: Dokploy app exists and is ready for environment variables.

- [ ] **Step 2: Add environment variables**

Set the values from Task 5 in the `telegram-mcp-main` environment.

Expected: Dokploy app has no missing required environment variables.

- [ ] **Step 3: Configure Cloudflare Access**

Configure Cloudflare Access for `tg-mcp-main.351hub.space` with the same service-auth pattern used by the existing Telegram MCP app.

Expected: requests without Cloudflare Access service-token headers receive Cloudflare `403` before reaching the MCP server.

- [ ] **Step 4: Deploy second app**

Trigger deployment for `telegram-mcp-main`.

Expected: build succeeds, container starts, and Dokploy health check passes.

- [ ] **Step 5: Verify unauthenticated Cloudflare behavior**

Run:

```bash
curl -i https://tg-mcp-main.351hub.space/health
```

Expected: Cloudflare returns `403`.

- [ ] **Step 6: Verify app health behind Cloudflare Access**

Run a curl request with Cloudflare Access headers and no MCP bearer token:

```bash
TOKEN=$(security find-generic-password -s "infisical" -a "INFISICAL_SERVICE_TOKEN" -w)
PROJECT_ID="a86e9a93-11b6-41fb-92e7-6cb9bf8d2cb9"
CF_ID=$(infisical secrets get DOKPLOY_CF_ACCESS_CLIENT_ID_DOKPLOY --token="$TOKEN" --projectId="$PROJECT_ID" --env prod --plain --silent 2>/dev/null | tail -n 1)
CF_SECRET=$(infisical secrets get DOKPLOY_CF_ACCESS_CLIENT_SECRET_DOKPLOY --token="$TOKEN" --projectId="$PROJECT_ID" --env prod --plain --silent 2>/dev/null | tail -n 1)
curl -sS \
  -H "CF-Access-Client-Id: $CF_ID" \
  -H "CF-Access-Client-Secret: $CF_SECRET" \
  https://tg-mcp-main.351hub.space/health
```

Expected JSON:

```json
{"status":"ok","account_name":"main","transport":"streamable-http"}
```

- [ ] **Step 7: Verify MCP bearer auth still protects `/mcp`**

Run:

```bash
TOKEN=$(security find-generic-password -s "infisical" -a "INFISICAL_SERVICE_TOKEN" -w)
PROJECT_ID="a86e9a93-11b6-41fb-92e7-6cb9bf8d2cb9"
CF_ID=$(infisical secrets get DOKPLOY_CF_ACCESS_CLIENT_ID_DOKPLOY --token="$TOKEN" --projectId="$PROJECT_ID" --env prod --plain --silent 2>/dev/null | tail -n 1)
CF_SECRET=$(infisical secrets get DOKPLOY_CF_ACCESS_CLIENT_SECRET_DOKPLOY --token="$TOKEN" --projectId="$PROJECT_ID" --env prod --plain --silent 2>/dev/null | tail -n 1)
curl -sS -i \
  -H "CF-Access-Client-Id: $CF_ID" \
  -H "CF-Access-Client-Secret: $CF_SECRET" \
  https://tg-mcp-main.351hub.space/mcp
```

Expected: HTTP `401` from the app with code `mcp_bearer_token_missing`.

- [ ] **Step 8: Verify MCP client identity**

Connect an MCP client to:

```text
https://tg-mcp-main.351hub.space/mcp
```

Include:

```text
CF-Access-Client-Id: <Cloudflare Access client id>
CF-Access-Client-Secret: <Cloudflare Access client secret>
Authorization: Bearer <second app MCP bearer token>
```

Call:

```text
get_server_info
get_me
```

Expected: `get_server_info` shows account name `main`, and `get_me` returns the expected second Telegram account.

## Self-Review Notes

- Spec coverage: account identity, one repo/many apps, non-secret GitHub docs, tool distribution, second app deployment, and verification are covered.
- Placeholder scan: no `TBD`, `TODO`, or incomplete implementation steps remain.
- Type consistency: `_server_info_payload() -> dict[str, str]`, `TELEGRAM_ACCOUNT_NAME`, and `get_server_info() -> str` are used consistently across tasks.
