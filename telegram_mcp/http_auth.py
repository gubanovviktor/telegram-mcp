"""Bearer-token auth and a configurable mount path for the streamable HTTP
transport.

Upstream's plain "http" transport (see runner._serve) is intentionally
unauthenticated and meant to be published on localhost only. Our Dokploy
deployments expose the server on a public domain behind a reverse proxy, so
they need a second auth layer on top of Cloudflare Access. Activated by
setting MCP_BEARER_TOKEN (and, for the historic Dokploy env value, by
MCP_TRANSPORT=streamable-http).
"""

import secrets
from contextlib import asynccontextmanager, AsyncExitStack

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route


class BearerTokenAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str):
        super().__init__(app)
        self.token = token

    @staticmethod
    def _unauthorized_response(code: str, message: str) -> JSONResponse:
        return JSONResponse(
            {
                "error": "Unauthorized",
                "code": code,
                "message": message,
            },
            status_code=401,
            headers={
                "WWW-Authenticate": (f'Bearer error="invalid_token", error_description="{code}"')
            },
        )

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return self._unauthorized_response(
                "mcp_bearer_token_missing",
                "Missing Authorization: Bearer <MCP_BEARER_TOKEN> header.",
            )

        provided_token = auth_header.split(" ", 1)[1].strip()
        if not secrets.compare_digest(provided_token, self.token):
            return self._unauthorized_response(
                "mcp_bearer_token_invalid",
                (
                    "MCP bearer token is invalid. It may have been rotated or expired. "
                    "Update the Authorization: Bearer <MCP_BEARER_TOKEN> header in your "
                    "MCP client."
                ),
            )

        return await call_next(request)


async def _healthcheck(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _normalize_mount_path(path: str) -> str:
    path = path.strip() or "/mcp"
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path


async def serve_authenticated_http(
    mcp, *, host: str, port: int, bearer_token: str, mount_path: str
) -> None:
    """Serve `mcp` over streamable HTTP behind bearer-token auth at
    `mount_path`, with an unauthenticated `/health` route for container
    health checks (e.g. Dockerfile HEALTHCHECK, Dokploy).
    """
    mount_path = _normalize_mount_path(mount_path)

    @asynccontextmanager
    async def _lifespan(_app: Starlette):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(mcp.session_manager.run())
            yield

    # The streamable-HTTP app is mounted at "/" internally; the outer
    # Starlette app remounts it under `mount_path` so MCP_PATH stays
    # configurable independently of FastMCP's own default.
    mcp.settings.streamable_http_path = "/"
    mcp_app = mcp.streamable_http_app()
    app = Starlette(
        routes=[
            Route("/health", _healthcheck, methods=["GET"]),
            Mount(mount_path, app=mcp_app),
        ],
        lifespan=_lifespan,
    )
    app.add_middleware(BearerTokenAuthMiddleware, token=bearer_token)

    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config=config)
    await server.serve()
