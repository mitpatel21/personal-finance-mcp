"""Optional GitHub OAuth for remote deployments, limited to an allowlist.

Local use (Claude Code / Desktop on the same machine) needs no auth: leave
GITHUB_CLIENT_ID unset and the server binds to 127.0.0.1.

For a public deployment (Render, etc.) set:
    GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET   GitHub OAuth app credentials
    ALLOWED_GITHUB_USERS                     e.g. "mitpatel21" (comma/space separated)
    PUBLIC_URL                               e.g. https://my-finance.onrender.com
                                             (falls back to Render's RENDER_EXTERNAL_URL)
    JWT_SIGNING_KEY                          long random string; keeps sessions valid across restarts

GitHub login alone would admit *any* GitHub account, so every token is also
checked against ALLOWED_GITHUB_USERS. Anyone else gets a 401 on every request,
including tool listing.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

# Where MCP clients may be sent back to after login. claude.ai / claude.com use
# a fixed callback; Claude Code and Desktop use a localhost port.
DEFAULT_REDIRECT_PATTERNS = [
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
    "http://localhost/*",
    "http://127.0.0.1/*",
]


def parse_allowlist(raw: str | None) -> frozenset[str]:
    """'alice, Bob carol' -> {'alice', 'bob', 'carol'} (GitHub logins are case-insensitive)."""
    if not raw:
        return frozenset()
    return frozenset(u.strip().lower() for u in raw.replace(",", " ").split() if u.strip())


def is_allowed(login: str | None, allowlist: frozenset[str]) -> bool:
    return bool(login) and login.lower() in allowlist


def _make_provider_class():
    # Imported lazily so local/no-auth use and the allowlist tests don't depend
    # on the OAuth stack.
    from fastmcp.server.auth.providers.github import GitHubProvider

    class AllowlistGitHubProvider(GitHubProvider):
        """GitHubProvider that only accepts tokens for allowlisted GitHub logins."""

        def __init__(self, *, allowed_logins: frozenset[str], **kwargs):
            if not allowed_logins:
                raise ValueError("allowed_logins must not be empty")
            super().__init__(**kwargs)
            self._allowed_logins = allowed_logins

        async def load_access_token(self, token: str):  # verify_token delegates here
            access = await super().load_access_token(token)
            if access is None:
                return None
            login = (access.claims or {}).get("login")
            if not is_allowed(login, self._allowed_logins):
                log.warning("Rejected GitHub user %r: not in ALLOWED_GITHUB_USERS", login)
                return None
            return access

    return AllowlistGitHubProvider


def auth_from_env():
    """Return an auth provider if GitHub OAuth is configured, else None.

    Fails closed: a half-configured or allowlist-less setup refuses to start,
    and so does a Render deployment with no auth at all.
    """
    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip()
    if not client_id:
        if os.getenv("RENDER"):
            raise SystemExit(
                "Refusing to start on Render without auth: set GITHUB_CLIENT_ID, "
                "GITHUB_CLIENT_SECRET and ALLOWED_GITHUB_USERS (see docs/RENDER.md)."
            )
        return None

    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
    allowlist = parse_allowlist(os.getenv("ALLOWED_GITHUB_USERS"))
    base_url = (os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")

    missing = [
        name
        for name, value in [
            ("GITHUB_CLIENT_SECRET", client_secret),
            ("ALLOWED_GITHUB_USERS", allowlist),
            ("PUBLIC_URL", base_url),
        ]
        if not value
    ]
    if missing:
        raise SystemExit(f"GitHub auth is half-configured; missing: {', '.join(missing)}")

    jwt_key = os.getenv("JWT_SIGNING_KEY") or None
    if not jwt_key:
        log.warning("JWT_SIGNING_KEY not set; deriving one from the GitHub client secret.")

    provider_cls = _make_provider_class()
    log.info("GitHub OAuth enabled for: %s", ", ".join(sorted(allowlist)))
    return provider_cls(
        allowed_logins=allowlist,
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        jwt_signing_key=jwt_key,
        allowed_client_redirect_uris=DEFAULT_REDIRECT_PATTERNS,
        # Least privilege: only read the profile to learn the login name
        # (the library default, "user", would also allow profile writes).
        required_scopes=["read:user"],
    )
