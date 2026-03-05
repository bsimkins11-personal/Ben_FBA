from backend.cache.league_cache import LeagueCache
from backend.config import USE_SYNTHETIC_DATA


async def get_free_agents(position: str | None = None) -> dict:
    """Return available free agents, optionally filtered by position."""
    if USE_SYNTHETIC_DATA:
        data = LeagueCache().get_free_agents()
        if position:
            data = {
                "free_agents": [
                    fa for fa in data.get("free_agents", [])
                    if position in fa.get("eligible_positions", [])
                ]
            }
        return data
    raise NotImplementedError("Live Yahoo not yet wired")
