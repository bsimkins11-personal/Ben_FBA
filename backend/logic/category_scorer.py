"""H2H category gap analysis for 5x5 Bush League."""

from __future__ import annotations

HITTING_CATS = ["OBP", "R", "TB", "RBI", "SB"]
PITCHING_CATS = ["QS", "SH", "K", "ERA", "WHIP"]
ALL_CATS = HITTING_CATS + PITCHING_CATS
LOWER_BETTER = {"ERA", "WHIP"}


def _direction(cat: str) -> str:
    return "lower_better" if cat in LOWER_BETTER else "higher_better"


def _priority_label(rank: int) -> str:
    if rank >= 9:
        return "high"
    if rank >= 5:
        return "medium"
    return "low"


def _priority_sort_key(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}[priority]


def analyze_category_gaps(
    my_ranks: dict, standings: list[dict]
) -> list[dict]:
    """Compute per-category gap analysis from H2H standings.

    Parameters
    ----------
    my_ranks : dict
        ``{category: rank}`` where rank is 1-12 (1 = best).
    standings : list[dict]
        One dict per team with at least each category as a key holding the
        team's *value* (e.g. ``{"OBP": .340, "ERA": 3.12, ...}``).

    Returns
    -------
    list[dict]
        Sorted by priority (high first), then by gap descending.
    """
    if not standings:
        return []

    num_teams = len(standings)
    results: list[dict] = []

    for cat in ALL_CATS:
        rank = my_ranks.get(cat)
        if rank is None:
            continue

        values = [t.get(cat, 0) for t in standings]
        league_avg = sum(values) / len(values) if values else 0.0

        # Sort values to find the team one rank above ours.
        # For "higher_better" cats, rank 1 has the highest value.
        # For "lower_better" cats, rank 1 has the lowest value.
        if cat in LOWER_BETTER:
            sorted_vals = sorted(values)  # ascending — rank 1 is lowest
        else:
            sorted_vals = sorted(values, reverse=True)  # descending — rank 1 is highest

        my_value = sorted_vals[rank - 1] if rank <= len(sorted_vals) else 0.0

        if rank == 1:
            gap_to_next = 0.0
        else:
            next_better_value = sorted_vals[rank - 2]
            gap_to_next = abs(next_better_value - my_value)

        results.append(
            {
                "category": cat,
                "my_rank": rank,
                "my_value": round(my_value, 4),
                "league_avg": round(league_avg, 4),
                "gap_to_next": round(gap_to_next, 4),
                "direction": _direction(cat),
                "priority": _priority_label(rank),
            }
        )

    results.sort(key=lambda r: (_priority_sort_key(r["priority"]), -r["gap_to_next"]))
    return results


def get_weak_categories(gaps: list[dict], max_results: int = 3) -> list[str]:
    """Return the *max_results* weakest category names (highest priority first)."""
    sorted_gaps = sorted(
        gaps, key=lambda r: (_priority_sort_key(r["priority"]), -r["my_rank"])
    )
    return [g["category"] for g in sorted_gaps[:max_results]]


def get_strong_categories(gaps: list[dict], max_results: int = 3) -> list[str]:
    """Return the *max_results* strongest category names (best rank first)."""
    sorted_gaps = sorted(
        gaps, key=lambda r: (r["my_rank"], _priority_sort_key(r["priority"]))
    )
    return [g["category"] for g in sorted_gaps[:max_results]]
