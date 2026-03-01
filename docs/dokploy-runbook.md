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

## 2. Create application in Dokploy
- Source: your GitHub fork (`main` branch)
- Build type: `dockerfile`
- Dockerfile path: `Dockerfile`
- Context path: `.`
- Port: `8000`
- Domain: configure Traefik HTTPS domain

## 3. Health and endpoint checks
After deploy:

- Health: `GET https://<domain>/health` should return HTTP 200
- MCP endpoint without token: `https://<domain>/mcp` should return HTTP 401
- MCP endpoint with token: connect MCP client using header
  - `Authorization: Bearer <MCP_BEARER_TOKEN>`

## 4. Rotate bearer token
1. Generate a new random token.
2. Update `MCP_BEARER_TOKEN` in Dokploy env.
3. Redeploy application.
4. Update client config headers.

## 5. Update from upstream
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
