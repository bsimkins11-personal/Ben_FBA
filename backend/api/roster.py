from backend.cache.league_cache import LeagueCache
from backend.auth.yahoo_auth import get_token_store
from backend.api import yahoo_client


async def get_my_roster() -> dict:
    """Return the manager's full roster with stats."""
    store = get_token_store()
    if store.is_authenticated and store.team_key:
        return await yahoo_client.get_roster(store.team_key)
    return LeagueCache().get_roster()


async def get_roster_stats() -> dict:
    """Return just the aggregate stats portion of the roster."""
    roster = await get_my_roster()
    return {
        "team_key": roster.get("team_key"),
        "team_name": roster.get("team_name"),
        "week_stats": roster.get("week_stats", {}),
        "category_ranks": roster.get("category_ranks", {}),
    }
