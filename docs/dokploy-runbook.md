# Dokploy Runbook

## 1. Required environment variables
Use `docs/dokploy.env.example` as the template and set all values in Dokploy secrets:

- `TELEGRAM_ACCOUNT_NAME`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION_STRING`
- `MCP_TRANSPORT=streamable-http`
- `MCP_HOST=0.0.0.0`
- `MCP_PORT=8000`
- `MCP_PATH=/mcp`
- `MCP_BEARER_TOKEN`
- `MCP_ALLOWED_HOSTS`

For multiple Telegram accounts, create one Dokploy application per account.
Each application uses the same GitHub repository, branch, Dockerfile, and port.
Only the environment variables, domain, and bearer token differ.

Recommended app/domain pairs:

| Account | Dokploy app | Domain |
| --- | --- | --- |
| Existing account | existing Dokploy app | `tg-mcp.351hub.space` |
| New main account | `telegram-mcp-main` | `tg-mcp-main.351hub.space` |

## 2. Create application in Dokploy
- Source: your GitHub fork (`main` branch)
- Build type: `dockerfile`
- Dockerfile path: `Dockerfile`
- Context path: `.`
- Port: `8000`
- Domain: configure Traefik HTTPS domain
- If using Docker Compose directly, bind the app port to localhost only
  (`127.0.0.1:8000:8000`) so the MCP endpoint is reachable through the
  reverse proxy but not directly from the public internet.

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
TELEGRAM_SESSION_STRING=your_second_account_session_string_here
MCP_BEARER_TOKEN=replace_with_second_account_bearer_token
MCP_ALLOWED_HOSTS=localhost,localhost:8000,tg-mcp-main.351hub.space,tg-mcp-main.351hub.space:443
```

Use the same `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` if both accounts use the
same Telegram API application. Keep all secret values in Dokploy and/or
Infisical, not in GitHub.

## 4. Cloudflare Access
For internet-facing deployments, protect the hostname with Cloudflare Access:

- DNS record for `<domain>` must be proxied through Cloudflare.
- Access application type: self-hosted.
- Application domain: `<domain>`.
- Policy action: Service Auth.
- Include rule: Cloudflare Access service token used by the MCP client.

The MCP client must send both Cloudflare Access headers and the internal MCP
bearer token:

```text
CF-Access-Client-Id: <CLOUDFLARE_ACCESS_CLIENT_ID>
CF-Access-Client-Secret: <CLOUDFLARE_ACCESS_CLIENT_SECRET>
Authorization: Bearer <MCP_BEARER_TOKEN>
```

## 5. Health and endpoint checks
After deploy:

- Without Cloudflare Access headers, both `https://<domain>/health` and
  `https://<domain>/mcp` should return Cloudflare `403`.
- With Cloudflare Access headers but without `Authorization`, the request should
  reach the MCP server and return `401` with `code:
  mcp_bearer_token_missing`.
- With Cloudflare Access headers and a stale MCP bearer token, the request
  should return `401` with `code: mcp_bearer_token_invalid`.
- With both valid auth layers, the MCP client can connect to
  `https://<domain>/mcp`.

## 6. Rotate bearer token
1. Generate a new random token.
2. Update `MCP_BEARER_TOKEN` in Dokploy env.
3. Redeploy application.
4. Update client config headers.

## 7. Rotate Cloudflare Access service token
Current token:

- Name: `mcp-telegram`
- Lifetime: 1 year
- Expires: `2027-07-27 15:54:19 UTC`
- Client ID: `afce22953c447a252fa61b9aa2e00450.access`

Rotate this before the expiry date. If it expires first, Codex will receive
Cloudflare `403` responses and the request will not reach the MCP server.

1. Create a new Cloudflare Access service token.
2. Update the Access policy to include the new service token.
3. Update MCP client headers with the new `CF-Access-Client-Id` and
   `CF-Access-Client-Secret`.
4. Confirm `https://<domain>/mcp` reaches the MCP server when both auth layers
   are present.
5. Delete the old Cloudflare Access service token.

If the Cloudflare service token is missing or expired, the MCP server will not
see the request. Cloudflare returns `403` before the request reaches the
application. If the MCP bearer token is missing or stale, the application
returns JSON with `mcp_bearer_token_missing` or `mcp_bearer_token_invalid`.

## 8. Distribute tool updates to all account servers

All account servers run the same code. To publish a new MCP tool or tool fix:

1. Implement the tool change once in this repository.
2. Run the test suite locally.
3. Push the branch to GitHub.
4. Redeploy the existing app for `tg-mcp.351hub.space`.
5. Redeploy `telegram-mcp-main`.
6. Check `https://tg-mcp.351hub.space/health` and
   `https://tg-mcp-main.351hub.space/health` with Cloudflare Access headers.
7. Call `get_server_info` and `get_me` through each MCP connection to confirm
   the connected account.

If Dokploy provides a bulk redeploy action for apps from the same repo revision,
use it. Otherwise, redeploy each app manually.

## 9. Update from upstream
Keep these remotes configured:

- `origin`: your fork
- `upstream`: `chigwell/telegram-mcp`

Typical update flow:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

If conflicts happen, resolve only in local customizations (transport/auth/runtime docs), then redeploy.
