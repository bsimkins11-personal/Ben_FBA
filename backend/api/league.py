from backend.cache.league_cache import LeagueCache
from backend.config import USE_SYNTHETIC_DATA


async def get_league_config() -> dict:
    """Return league configuration (scoring categories, roster slots, etc.)."""
    if USE_SYNTHETIC_DATA:
        return LeagueCache().get_league_config()
    raise NotImplementedError("Live Yahoo not yet wired")
