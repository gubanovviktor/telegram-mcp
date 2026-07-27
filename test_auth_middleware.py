import os

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from test_support import VALID_DUMMY_TELEGRAM_SESSION_STRING

os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "dummy_hash")
os.environ.setdefault("TELEGRAM_SESSION_STRING", VALID_DUMMY_TELEGRAM_SESSION_STRING)

from main import BearerTokenAuthMiddleware


async def _ok(_request):
    return JSONResponse({"status": "ok"})


def _client(token="current-token"):
    app = Starlette(routes=[Route("/mcp", _ok, methods=["GET"])])
    app.add_middleware(BearerTokenAuthMiddleware, token=token)
    return TestClient(app)


def test_invalid_bearer_token_reports_rotated_or_expired_token():
    response = _client().get("/mcp", headers={"Authorization": "Bearer old-token"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")
    assert response.json() == {
        "error": "Unauthorized",
        "code": "mcp_bearer_token_invalid",
        "message": (
            "MCP bearer token is invalid. It may have been rotated or expired. "
            "Update the Authorization: Bearer <MCP_BEARER_TOKEN> header in your MCP client."
        ),
    }


def test_missing_bearer_token_reports_required_header():
    response = _client().get("/mcp")

    assert response.status_code == 401
    assert response.json() == {
        "error": "Unauthorized",
        "code": "mcp_bearer_token_missing",
        "message": "Missing Authorization: Bearer <MCP_BEARER_TOKEN> header.",
    }
