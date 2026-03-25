from backend.cache.league_cache import LeagueCache
from backend.auth.yahoo_auth import get_token_store
from backend.api import yahoo_client


async def get_my_roster() -> dict:
    """Return the manager's full roster with stats."""
    store = get_token_store()
    if store.is_authenticated and store.team_key:
        roster_data = await yahoo_client.get_roster(store.team_key)
        # Enrich with category_ranks from standings
        standings_result = await yahoo_client.get_standings(store.league_key)
        my_team = next(
            (t for t in standings_result.get("standings", [])
             if t["team_key"] == store.team_key), None
        )
        if my_team:
            roster_data["category_ranks"] = my_team.get("category_ranks", {})
            roster_data["week_stats"] = my_team.get("category_totals", {})
        return roster_data
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
