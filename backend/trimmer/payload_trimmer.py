import json
import logging
from typing import Callable

from backend.config import (
    FA_FIELDS,
    ROSTER_FIELDS,
    STANDINGS_FIELDS,
    TRIMMER_MAX_TOKENS,
)

logger = logging.getLogger(__name__)


def _pick(source: dict, fields: list[str]) -> dict:
    """Return a new dict containing only *fields* present in *source*."""
    return {k: v for k, v in source.items() if k in fields}


def _compact_stats(stats: dict) -> dict:
    """Round floats to save tokens."""
    return {
        k: round(v, 3) if isinstance(v, float) and v < 1 else
           round(v, 2) if isinstance(v, float) else v
        for k, v in stats.items()
    }


def trim_roster(roster_data: dict, max_players: int = 15) -> dict:
    """Keep only ROSTER_FIELDS, skip BN/DL slots, cap at *max_players*."""
    players = roster_data.get("players", [])
    active = [p for p in players if p.get("position") not in ("BN", "DL", "NA")]
    trimmed = []
    for p in active[:max_players]:
        entry = _pick(p, ROSTER_FIELDS)
        if "stats" in entry:
            entry["stats"] = _compact_stats(entry["stats"])
        trimmed.append(entry)
    return {"players": trimmed}


def trim_free_agents(fa_data: dict, max_players: int = 10) -> dict:
    """Keep only FA_FIELDS, cap at *max_players*."""
    agents = fa_data.get("free_agents", [])
    trimmed = []
    for a in agents[:max_players]:
        entry = _pick(a, FA_FIELDS)
        if "projected_stats" in entry:
            entry["projected_stats"] = _compact_stats(entry["projected_stats"])
        trimmed.append(entry)
    return {"free_agents": trimmed}


def trim_standings(standings_data: dict) -> dict:
    """Keep only STANDINGS_FIELDS-relevant data."""
    categories = standings_data.get("categories", [])
    return {"categories": [_pick(c, STANDINGS_FIELDS) for c in categories]}


def trim_matchup(matchup_data: dict) -> dict:
    """Keep team names, stats, and category results only."""
    allowed = {"team_name", "stats", "category_results", "week", "score"}
    teams = matchup_data.get("teams", [])
    trimmed_teams = [{k: v for k, v in t.items() if k in allowed} for t in teams]
    result: dict = {"teams": trimmed_teams}
    if "week" in matchup_data:
        result["week"] = matchup_data["week"]
    return result


def estimate_tokens(data: dict) -> int:
    """Rough token estimate: len(json.dumps(data)) / 4."""
    return len(json.dumps(data, default=str)) // 4


def trim_and_log(
    data: dict,
    trimmer_fn: Callable[[dict], dict],
    label: str = "",
) -> dict:
    """Apply trimmer, log pre/post token counts, warn if > TRIMMER_MAX_TOKENS."""
    pre_tokens = estimate_tokens(data)
    trimmed = trimmer_fn(data)
    post_tokens = estimate_tokens(trimmed)

    tag = f"[{label}] " if label else ""
    logger.info("%strimmed %d → %d est. tokens", tag, pre_tokens, post_tokens)

    if post_tokens > TRIMMER_MAX_TOKENS:
        logger.warning(
            "%spost-trim payload (%d tokens) exceeds TRIMMER_MAX_TOKENS (%d)",
            tag,
            post_tokens,
            TRIMMER_MAX_TOKENS,
        )
    return trimmed
