from backend.cache.league_cache import LeagueCache
from backend.auth.yahoo_auth import get_token_store
from backend.api import yahoo_client


async def get_free_agents(position: str | None = None) -> dict:
    """Return available free agents, optionally filtered by position."""
    store = get_token_store()
    if store.is_authenticated and store.league_key:
        return await yahoo_client.get_free_agents(
            store.league_key, position=position
        )

    data = LeagueCache().get_free_agents()
    if position:
        data = {
            "free_agents": [
                fa for fa in data.get("free_agents", [])
                if position in fa.get("eligible_positions", [])
            ]
        }
    return data
