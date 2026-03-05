from backend.cache.league_cache import LeagueCache
from backend.config import USE_SYNTHETIC_DATA


async def get_draft_history() -> dict:
    """Return draft history for keeper calculations."""
    if USE_SYNTHETIC_DATA:
        return LeagueCache().get_draft_history()
    raise NotImplementedError("Live Yahoo not yet wired")


async def get_matchup() -> dict:
    """Return the current week's H2H matchup."""
    if USE_SYNTHETIC_DATA:
        return LeagueCache().get_matchup()
    raise NotImplementedError("Live Yahoo not yet wired")
