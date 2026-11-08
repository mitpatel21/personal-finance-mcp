import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import auth

AUTH_VARS = [
    "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "ALLOWED_GITHUB_USERS",
    "PUBLIC_URL", "RENDER_EXTERNAL_URL", "RENDER", "JWT_SIGNING_KEY",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in AUTH_VARS:
        monkeypatch.delenv(name, raising=False)


def test_parse_allowlist_normalizes():
    assert auth.parse_allowlist(" MitPatel21, bob  carol ") == {"mitpatel21", "bob", "carol"}
    assert auth.parse_allowlist("") == frozenset()
    assert auth.parse_allowlist(None) == frozenset()


def test_is_allowed():
    allow = frozenset({"mitpatel21"})
    assert auth.is_allowed("MITPATEL21", allow)
    assert not auth.is_allowed("someone-else", allow)
    assert not auth.is_allowed(None, allow)
    assert not auth.is_allowed("", allow)


def test_no_auth_locally():
    assert auth.auth_from_env() is None


def test_refuses_unauthenticated_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(SystemExit, match="Refusing to start on Render"):
        auth.auth_from_env()


@pytest.mark.parametrize("drop", ["GITHUB_CLIENT_SECRET", "ALLOWED_GITHUB_USERS", "PUBLIC_URL"])
def test_half_configured_fails_closed(monkeypatch, drop):
    env = {
        "GITHUB_CLIENT_ID": "id",
        "GITHUB_CLIENT_SECRET": "secret",
        "ALLOWED_GITHUB_USERS": "mitpatel21",
        "PUBLIC_URL": "https://example.onrender.com",
    }
    env.pop(drop)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(SystemExit, match=drop):
        auth.auth_from_env()


def test_render_external_url_is_used(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ALLOWED_GITHUB_USERS", "mitpatel21")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://x.onrender.com/")
    captured = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    with patch.object(auth, "_make_provider_class", return_value=FakeProvider):
        auth.auth_from_env()
    assert captured["base_url"] == "https://x.onrender.com"
    assert captured["allowed_logins"] == {"mitpatel21"}
    assert "https://claude.ai/api/mcp/auth_callback" in captured["allowed_client_redirect_uris"]


def test_provider_rejects_other_github_users():
    pytest.importorskip("fastmcp")
    from fastmcp.server.auth.providers.github import GitHubProvider

    cls = auth._make_provider_class()
    provider = cls.__new__(cls)  # skip OAuth setup; only the allowlist check is under test
    provider._allowed_logins = frozenset({"mitpatel21"})

    async def fake_super(self, token):
        return SimpleNamespace(claims={"login": token})

    with patch.object(GitHubProvider, "load_access_token", fake_super):
        assert asyncio.run(provider.load_access_token("MitPatel21")) is not None
        assert asyncio.run(provider.load_access_token("attacker")) is None
