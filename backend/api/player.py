from backend.cache.league_cache import LeagueCache
from backend.auth.yahoo_auth import get_token_store
from backend.api import yahoo_client


async def get_draft_history() -> dict:
    """Return draft history for keeper calculations."""
    store = get_token_store()
    if store.is_authenticated and store.league_key:
        return await yahoo_client.get_draft_results(store.league_key)
    return LeagueCache().get_draft_history()


async def get_matchup() -> dict:
    """Return the current week's H2H matchup."""
    store = get_token_store()
    if store.is_authenticated and store.league_key:
        return await yahoo_client.get_scoreboard(store.league_key)
    return LeagueCache().get_matchup()
