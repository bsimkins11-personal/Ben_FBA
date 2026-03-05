"""Yahoo OAuth 2.0 PKCE — wired in Phase 4.

Token storage uses environment variables (Railway is ephemeral).
"""

from backend.config import YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET

YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"


class YahooAuth:
    """Placeholder for Yahoo OAuth 2.0 PKCE flow."""

    def __init__(self) -> None:
        self.client_id = YAHOO_CLIENT_ID
        self.client_secret = YAHOO_CLIENT_SECRET
        self.access_token: str = ""
        self.refresh_token: str = ""

    def get_auth_url(self, callback_url: str) -> str:
        raise NotImplementedError("Yahoo OAuth not yet implemented — Phase 4")

    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        raise NotImplementedError("Yahoo OAuth not yet implemented — Phase 4")

    async def refresh(self) -> str:
        raise NotImplementedError("Yahoo OAuth not yet implemented — Phase 4")
