# Dokploy Runbook

## 1. Required environment variables
Use `docs/dokploy.env.example` as the template and set all values in Dokploy secrets:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION_STRING`
- `MCP_TRANSPORT=streamable-http`
- `MCP_HOST=0.0.0.0`
- `MCP_PORT=8000`
- `MCP_PATH=/mcp`
- `MCP_BEARER_TOKEN`
- `MCP_ALLOWED_HOSTS`

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

## 3. Cloudflare Access
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

## 4. Health and endpoint checks
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

## 5. Rotate bearer token
1. Generate a new random token.
2. Update `MCP_BEARER_TOKEN` in Dokploy env.
3. Redeploy application.
4. Update client config headers.

## 6. Rotate Cloudflare Access service token
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

## 7. Update from upstream
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
