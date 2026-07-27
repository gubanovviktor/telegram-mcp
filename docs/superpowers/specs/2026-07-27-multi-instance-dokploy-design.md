# Multi-Instance Telegram MCP on Dokploy Design

## Goal

Run multiple Telegram MCP servers for separate Telegram accounts while keeping one shared codebase and one deployment artifact. The second account should be deployable to Dokploy now, and future tool changes should roll out to every account without copying code between servers.

## Decision

Keep the MCP server single-account per process, and run one Dokploy application per Telegram account.

Each Dokploy app uses the same GitHub repository, branch, Dockerfile, and runtime code. Apps differ only by environment variables and external routing:

- `TELEGRAM_SESSION_STRING`
- `MCP_BEARER_TOKEN`
- `MCP_ALLOWED_HOSTS`
- domain or route
- optional account label such as `TELEGRAM_ACCOUNT_NAME`

This avoids adding account-selection parameters to every tool. It also makes it harder for an MCP client or agent to accidentally send messages from the wrong Telegram account.

## Architecture

```text
GitHub repo
  -> shared Docker image build
      -> Dokploy app: telegram-mcp-main
      -> Dokploy app: telegram-mcp-second
      -> Dokploy app: telegram-mcp-next
```

Every app exposes the same MCP endpoint shape:

```text
https://<account-domain>/mcp
```

Every app keeps the existing two-layer protection:

- Cloudflare Access in front of the public hostname.
- MCP bearer token checked by the application.

## Components

### Shared Server Code

The codebase remains the source of truth for all tools. Adding or changing a tool in `main.py` affects all Telegram account servers after redeploy.

The server should gain a lightweight account identity setting:

```text
TELEGRAM_ACCOUNT_NAME=main
```

The account name is not a secret. It is used for diagnostics and to reduce confusion when several servers are connected to the same MCP client.

### Dokploy Applications

Create a separate Dokploy app for each Telegram account. Each app points to the same GitHub repo and branch.

Recommended naming:

```text
telegram-mcp-main
telegram-mcp-second
telegram-mcp-<purpose>
```

Each app has its own domain and environment variables. The second app should be created from the same Dockerfile setup as the first already-running app.

### GitHub Configuration

GitHub should contain only reproducible, non-secret configuration:

- deployment docs
- env examples
- naming conventions
- local compose examples when useful
- redeploy procedure

GitHub must not contain Telegram session strings, bearer tokens, Cloudflare Access secrets, Dokploy API keys, or Infisical values.

### Secrets

Secrets stay in Dokploy and/or Infisical. For the second Telegram account, generate a separate Telegram session string locally, then store it in the second Dokploy app's environment.

Required per-account secret values:

```text
TELEGRAM_SESSION_STRING
MCP_BEARER_TOKEN
```

Shared or per-app values depending on routing:

```text
TELEGRAM_API_ID
TELEGRAM_API_HASH
MCP_ALLOWED_HOSTS
Cloudflare Access client credentials
```

## Data Flow

1. MCP client connects to the account-specific domain.
2. Cloudflare Access validates service-token headers.
3. The Telegram MCP server validates the `Authorization: Bearer ...` header.
4. The app uses the single configured Telegram session string for all tool calls.
5. Tool results return through the same MCP connection.

There is no runtime account switching inside one process.

## Tool Distribution Flow

1. Implement or update tools once in the shared repo.
2. Run tests locally.
3. Push to GitHub.
4. Redeploy each Dokploy app that should receive the update.
5. Verify `/health` and MCP connection for each account.

If Dokploy supports redeploying all apps from the same repo revision, use that. Otherwise, redeploy the apps one by one.

## Error Handling

The second server should fail fast on missing required environment variables, matching the current server behavior.

Useful operational checks:

- `/health` returns healthy for the app process.
- MCP without bearer token returns the existing unauthorized error.
- MCP with stale bearer token returns the existing invalid-token error.
- MCP with valid auth can call `get_me` and returns the expected Telegram account.

If account identity support is added, health or a diagnostic MCP tool should show the configured account name without exposing secrets.

## Testing

Use focused tests for any code changes:

- Existing auth middleware tests.
- Existing validation and file-path security tests.
- New tests for account identity behavior if implemented.

Deployment verification for the second account:

- Dokploy build succeeds.
- Health endpoint reaches the app behind Cloudflare Access.
- MCP endpoint rejects missing or invalid bearer token.
- MCP client can connect with both Cloudflare Access and bearer auth.
- `get_me` confirms the expected second Telegram account.

## Out of Scope

- One process managing multiple Telegram accounts.
- Adding `account` parameters to every tool.
- Automatic secret provisioning.
- Cross-account orchestration tools.
- Database-backed account registry.

## Success Criteria

- A second Telegram MCP Dokploy app runs from the same GitHub repo as the first.
- The second app uses its own Telegram session and MCP bearer token.
- No secrets are committed to GitHub.
- Future tool changes can be pushed once and deployed to all account apps.
- Operators can tell which account an instance represents during health checks or MCP diagnostics.
