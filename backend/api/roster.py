from backend.cache.league_cache import LeagueCache
from backend.config import USE_SYNTHETIC_DATA


async def get_my_roster() -> dict:
    """Return the manager's full roster with stats."""
    if USE_SYNTHETIC_DATA:
        return LeagueCache().get_roster()
    raise NotImplementedError("Live Yahoo not yet wired")


async def get_roster_stats() -> dict:
    """Return just the aggregate stats portion of the roster."""
    roster = await get_my_roster()
    return {
        "team_key": roster.get("team_key"),
        "team_name": roster.get("team_name"),
        "week_stats": roster.get("week_stats", {}),
        "category_ranks": roster.get("category_ranks", {}),
    }
