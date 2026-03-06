"""Yahoo OAuth 2.0 Authorization Code flow.

Tokens are stored in-memory for speed and persisted to Postgres so
they survive Railway redeploys. On startup, tokens are loaded from
Postgres automatically — no re-auth needed after a deploy.
"""

from __future__ import annotations

import base64
import logging
import time
import uuid
from urllib.parse import urlencode

import httpx

from backend.config import (
    YAHOO_CLIENT_ID,
    YAHOO_CLIENT_SECRET,
    YAHOO_REDIRECT_URI,
)

logger = logging.getLogger(__name__)

YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

YAHOO_SCOPE = "fspt-r"


class YahooTokenStore:
    """In-memory token store for a single user (Ben)."""

    def __init__(self) -> None:
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.expires_at: float = 0
        self.league_key: str = ""
        self.team_key: str = ""
        self._pending_state: str = ""

    @property
    def is_authenticated(self) -> bool:
        return bool(self.access_token)

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        return self.is_authenticated and self.is_expired

    def clear(self) -> None:
        self.access_token = ""
        self.refresh_token = ""
        self.expires_at = 0
        self.league_key = ""
        self.team_key = ""


_store = YahooTokenStore()


def get_token_store() -> YahooTokenStore:
    return _store


def _basic_auth_header() -> str:
    creds = f"{YAHOO_CLIENT_ID}:{YAHOO_CLIENT_SECRET}"
    encoded = base64.b64encode(creds.encode()).decode()
    return f"Basic {encoded}"


def get_login_url() -> str:
    """Build the Yahoo OAuth authorization URL."""
    state = uuid.uuid4().hex
    _store._pending_state = state

    params = {
        "client_id": YAHOO_CLIENT_ID,
        "redirect_uri": YAHOO_REDIRECT_URI,
        "response_type": "code",
        "scope": YAHOO_SCOPE,
        "state": state,
    }
    return f"{YAHOO_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str, state: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    if state != _store._pending_state:
        raise ValueError("OAuth state mismatch — possible CSRF")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            YAHOO_TOKEN_URL,
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "redirect_uri": YAHOO_REDIRECT_URI,
                "code": code,
            },
        )

    if resp.status_code != 200:
        logger.error("Token exchange failed: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Yahoo token exchange failed: {resp.status_code}")

    data = resp.json()
    _store.access_token = data["access_token"]
    _store.refresh_token = data["refresh_token"]
    _store.expires_at = time.time() + data.get("expires_in", 3600) - 60

    await _persist_tokens()
    logger.info("Yahoo OAuth tokens acquired, expires in %ss", data.get("expires_in"))
    return data


async def refresh_tokens() -> str:
    """Refresh the access token using the stored refresh token."""
    if not _store.refresh_token:
        raise RuntimeError("No refresh token available — re-authenticate")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            YAHOO_TOKEN_URL,
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "redirect_uri": YAHOO_REDIRECT_URI,
                "refresh_token": _store.refresh_token,
            },
        )

    if resp.status_code != 200:
        logger.error("Token refresh failed: %s %s", resp.status_code, resp.text)
        _store.clear()
        raise RuntimeError("Yahoo token refresh failed — re-authenticate")

    data = resp.json()
    _store.access_token = data["access_token"]
    if "refresh_token" in data:
        _store.refresh_token = data["refresh_token"]
    _store.expires_at = time.time() + data.get("expires_in", 3600) - 60

    await _persist_tokens()
    logger.info("Yahoo tokens refreshed")
    return _store.access_token


async def get_valid_token() -> str:
    """Return a valid access token, refreshing if needed."""
    if not _store.is_authenticated:
        raise RuntimeError("Not authenticated with Yahoo")

    if _store.needs_refresh:
        return await refresh_tokens()

    return _store.access_token


# ── Postgres persistence helpers ─────────────────────────────

async def _persist_tokens() -> None:
    """Save current in-memory tokens to Postgres (fire-and-forget safe)."""
    try:
        from backend.db.postgres import save_tokens
        await save_tokens(
            access_token=_store.access_token,
            refresh_token=_store.refresh_token,
            expires_at=_store.expires_at,
            league_key=_store.league_key,
            team_key=_store.team_key,
        )
    except Exception as exc:
        logger.warning("Failed to persist tokens to Postgres: %s", exc)


async def restore_tokens_from_db() -> bool:
    """Load tokens from Postgres into the in-memory store.

    Returns True if tokens were restored (i.e., Ben is auto-authenticated).
    Called once at startup so redeploys don't require re-auth.
    """
    try:
        from backend.db.postgres import load_tokens
        row = await load_tokens()
        if not row:
            return False

        _store.access_token = row["access_token"]
        _store.refresh_token = row["refresh_token"]
        _store.expires_at = row["expires_at"]
        _store.league_key = row["league_key"]
        _store.team_key = row["team_key"]
        logger.info(
            "Restored Yahoo tokens from Postgres (league=%s, expires_at=%.0f)",
            _store.league_key,
            _store.expires_at,
        )
        return True
    except Exception as exc:
        logger.warning("Could not restore tokens from Postgres: %s", exc)
        return False


async def clear_stored_tokens() -> None:
    """Clear tokens from both memory and Postgres."""
    _store.clear()
    try:
        from backend.db.postgres import clear_tokens
        await clear_tokens()
    except Exception as exc:
        logger.warning("Failed to clear Postgres tokens: %s", exc)
