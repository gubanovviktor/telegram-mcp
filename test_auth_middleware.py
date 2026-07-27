import os

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from test_support import VALID_DUMMY_TELEGRAM_SESSION_STRING

os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "dummy_hash")
os.environ.setdefault("TELEGRAM_SESSION_STRING", VALID_DUMMY_TELEGRAM_SESSION_STRING)

from main import BearerTokenAuthMiddleware, _healthcheck, _server_info_payload


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
