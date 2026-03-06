from backend.cache.league_cache import LeagueCache
from backend.auth.yahoo_auth import get_token_store
from backend.api import yahoo_client


async def get_league_config() -> dict:
    """Return league configuration (scoring categories, roster slots, etc.)."""
    store = get_token_store()
    if store.is_authenticated and store.league_key:
        return await yahoo_client.get_league_settings(store.league_key)
    return LeagueCache().get_league_config()
