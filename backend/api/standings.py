from backend.cache.league_cache import LeagueCache
from backend.auth.yahoo_auth import get_token_store
from backend.api import yahoo_client


async def get_standings() -> dict:
    """Return league standings — live Yahoo when authenticated, else synthetic."""
    store = get_token_store()
    if store.is_authenticated and store.league_key:
        result = await yahoo_client.get_standings(store.league_key)
        result["my_team_key"] = store.team_key
        return result
    return LeagueCache().get_standings()
