"""Rank free agents by contribution to weak categories."""

from __future__ import annotations

HITTING_CATS = ["OBP", "R", "TB", "RBI", "SB"]
PITCHING_CATS = ["QS", "SH", "K", "ERA", "WHIP"]
LOWER_BETTER = {"ERA", "WHIP"}

_STAT_BENCHMARKS = {
    "OBP": 0.330, "R": 5, "TB": 15, "RBI": 5, "SB": 2,
    "QS": 1, "SH": 2, "K": 8, "ERA": 3.80, "WHIP": 1.20,
}


def _score_player(
    player: dict, weak_categories: list[str]
) -> tuple[float, list[str]]:
    stats = player.get("projected_stats") or player.get("stats", {})
    score = 0.0
    helps: list[str] = []

    for cat in weak_categories:
        val = stats.get(cat)
        if val is None:
            continue

        bench = _STAT_BENCHMARKS.get(cat, 0)
        if cat in LOWER_BETTER:
            if bench > 0 and val > 0:
                score += max(0, (bench - val) / bench) * 10
                if val < bench:
                    helps.append(cat)
        else:
            if bench > 0:
                score += (val / bench) * 10
                if val >= bench:
                    helps.append(cat)

    if len(player.get("eligible_positions", [])) > 2:
        score += 2.0

    status = player.get("status", "")
    if status in ("DTD", "IL10", "IL60"):
        score *= 0.6

    return round(score, 2), helps


def _recommendation_text(player: dict, helps: list[str]) -> str:
    if not helps:
        return "Marginal contributor — monitor for now"

    status = player.get("status", "")
    prefix = f"({status}) " if status else ""
    cats = " and ".join(helps)

    if len(helps) >= 3:
        return f"{prefix}Multi-category boost in {cats}"
    if "SB" in helps:
        return f"{prefix}Speed upside to address SB weakness"
    if "ERA" in helps or "WHIP" in helps:
        return f"{prefix}Elite ratios help close the gap in {cats}"
    if "SH" in helps:
        return f"{prefix}Saves+Holds upside to climb in S+H"
    return f"{prefix}Strong contributor in {cats}"


def rank_free_agents(
    free_agents: list[dict],
    weak_categories: list[str],
    position_filter: str | None = None,
    max_results: int = 10,
) -> list[dict]:
    """Score and rank free agents by impact on *weak_categories*.

    Returns sorted list (best first), capped at *max_results*.
    """
    candidates = free_agents
    if position_filter:
        candidates = [
            fa for fa in candidates
            if position_filter in fa.get("eligible_positions", [])
        ]

    scored: list[dict] = []
    for fa in candidates:
        ws, helps = _score_player(fa, weak_categories)
        scored.append({
            "name": fa["name"],
            "position": fa["position"],
            "eligible_positions": fa.get("eligible_positions", []),
            "status": fa.get("status", ""),
            "projected_stats": fa.get("projected_stats", {}),
            "waiver_score": ws,
            "helps_categories": helps,
            "recommendation": _recommendation_text(fa, helps),
        })

    scored.sort(key=lambda x: -x["waiver_score"])
    return scored[:max_results]
