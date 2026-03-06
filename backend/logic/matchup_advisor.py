"""Roster Advisor — game-by-game roster recommendations with rationale.

Cross-references Ben's roster with today's MLB schedule and generates
category-aware start/sit/swap advice for Roto optimization.
No LLM calls — pure rule-based logic. Zero cost.
"""

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)

HITTING_CATS = ["OBP", "R", "TB", "RBI", "SB"]
PITCHING_CATS = ["QS", "SH", "K", "ERA", "WHIP"]
LOWER_BETTER = {"ERA", "WHIP"}

# MLB team abbreviation → full name mapping for schedule matching
_TEAM_ABBREVS = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles", "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs", "CWS": "Chicago White Sox",
    "CIN": "Cincinnati Reds", "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies", "DET": "Detroit Tigers",
    "HOU": "Houston Astros", "KC": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins", "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "OAK": "Oakland Athletics",
    "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates",
    "SD": "San Diego Padres", "SF": "San Francisco Giants",
    "SEA": "Seattle Mariners", "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays", "TEX": "Texas Rangers",
    "TOR": "Toronto Blue Jays", "WSH": "Washington Nationals",
}

_FULL_TO_ABBREV = {v: k for k, v in _TEAM_ABBREVS.items()}


def _abbrev_from_full(full_name: str) -> str:
    if full_name in _FULL_TO_ABBREV:
        return _FULL_TO_ABBREV[full_name]
    for abbr, fn in _TEAM_ABBREVS.items():
        if fn.lower() in full_name.lower() or full_name.lower() in fn.lower():
            return abbr
    return full_name[:3].upper()


def _is_pitcher(pos: str) -> bool:
    return pos in ("SP", "RP", "P")


def _category_gap_analysis(my_stats: dict, opp_stats: dict) -> list[dict]:
    """Analyze each category: margin, status, and whether it's flippable."""
    analysis = []
    for cat in HITTING_CATS + PITCHING_CATS:
        my_val = my_stats.get(cat, 0)
        opp_val = opp_stats.get(cat, 0)

        if cat in LOWER_BETTER:
            winning = my_val < opp_val
            margin = opp_val - my_val
        else:
            winning = my_val > opp_val
            margin = my_val - opp_val

        if my_val == opp_val:
            status = "tied"
        elif winning:
            status = "winning"
        else:
            status = "losing"

        closeness = abs(margin)
        if cat in LOWER_BETTER:
            flippable = closeness < 0.50
        elif cat in ("OBP",):
            flippable = closeness < 0.015
        else:
            flippable = closeness < 8

        analysis.append({
            "category": cat,
            "my_value": my_val,
            "opp_value": opp_val,
            "margin": round(margin, 3),
            "status": status,
            "flippable": flippable,
        })
    return analysis


def _find_game_for_team(abbrev: str, schedule: list[dict]) -> dict | None:
    full_name = _TEAM_ABBREVS.get(abbrev, abbrev)
    for game in schedule:
        away = game.get("away_team", "")
        home = game.get("home_team", "")
        if full_name in away or full_name in home:
            return game
        if abbrev.lower() in away.lower() or abbrev.lower() in home.lower():
            return game
    return None


def _pitcher_rationale(player: dict, game: dict | None, cat_analysis: list[dict]) -> dict:
    """Generate start/sit advice for a pitcher."""
    name = player["name"]
    pos = player["position"]
    status = player.get("status", "")

    if status in ("IL10", "IL60"):
        return {
            "verdict": "out",
            "rationale": f"{name} is on the IL — cannot start.",
            "impact": [],
        }

    era_cat = next((c for c in cat_analysis if c["category"] == "ERA"), None)
    whip_cat = next((c for c in cat_analysis if c["category"] == "WHIP"), None)
    k_cat = next((c for c in cat_analysis if c["category"] == "K"), None)
    qs_cat = next((c for c in cat_analysis if c["category"] == "QS"), None)

    if not game:
        return {
            "verdict": "no_game",
            "rationale": f"{name} — no game scheduled today.",
            "impact": [],
        }

    opp_team = game.get("away_team", "")
    if player.get("mlb_team") and _TEAM_ABBREVS.get(player["mlb_team"], "") in game.get("home_team", ""):
        opp_team = game.get("away_team", "")
    else:
        opp_team = game.get("home_team", "")
    opp_abbrev = _abbrev_from_full(opp_team)

    if pos == "SP":
        is_probable = (
            name.lower() in game.get("away_pitcher", "").lower() or
            name.lower() in game.get("home_pitcher", "").lower()
        )

        if not is_probable:
            return {
                "verdict": "not_starting",
                "rationale": f"{name} is not the probable starter today.",
                "impact": [],
            }

        winning_era = era_cat and era_cat["status"] == "winning"
        winning_whip = whip_cat and whip_cat["status"] == "winning"
        era_close = era_cat and era_cat["flippable"]
        losing_k = k_cat and k_cat["status"] == "losing"

        if winning_era and winning_whip and era_close:
            return {
                "verdict": "caution",
                "rationale": (
                    f"{name} starts vs {opp_abbrev}. You're ahead in ERA and WHIP "
                    f"but the lead is thin. A blowup risks both ratio categories. "
                    f"Consider sitting if you can afford to lose K/QS."
                ),
                "impact": ["ERA", "WHIP", "K", "QS"],
            }

        if losing_k or (qs_cat and qs_cat["status"] == "losing"):
            return {
                "verdict": "start",
                "rationale": (
                    f"{name} starts vs {opp_abbrev}. You need K and QS ground — "
                    f"start him and chase counting stats."
                ),
                "impact": ["K", "QS", "ERA", "WHIP"],
            }

        return {
            "verdict": "start",
            "rationale": (
                f"{name} starts vs {opp_abbrev}. Good matchup to gain in K and QS."
            ),
            "impact": ["K", "QS"],
        }

    # RP
    if status == "DTD":
        return {
            "verdict": "monitor",
            "rationale": f"{name} is DTD — check pregame availability.",
            "impact": ["SH", "ERA", "WHIP"],
        }

    sh_cat = next((c for c in cat_analysis if c["category"] == "SH"), None)
    if sh_cat and sh_cat["status"] == "winning":
        return {
            "verdict": "confirmed",
            "rationale": (
                f"{name} — you're ahead in S+H. Solid ratio anchor if he enters."
            ),
            "impact": ["SH", "ERA", "WHIP"],
        }

    return {
        "verdict": "start",
        "rationale": f"{name} — active and available for S+H and ratio help.",
        "impact": ["SH", "K"],
    }


def _hitter_rationale(player: dict, game: dict | None, cat_analysis: list[dict]) -> dict:
    """Generate start/sit advice for a hitter."""
    name = player["name"]
    status = player.get("status", "")
    pos = player.get("position", "")

    if status in ("IL10", "IL60"):
        return {
            "verdict": "out",
            "rationale": f"{name} is on the IL — slot a bench bat.",
            "impact": [],
        }

    if not game:
        if pos == "BN":
            return {
                "verdict": "bench",
                "rationale": f"{name} — on bench, no game today. No action needed.",
                "impact": [],
            }
        return {
            "verdict": "no_game",
            "rationale": f"{name} — no game scheduled today. Consider swapping in a bench player who is active.",
            "impact": ["R", "TB", "RBI", "OBP"],
        }

    if status == "DTD":
        return {
            "verdict": "monitor",
            "rationale": (
                f"{name} is DTD. Monitor pregame lineups — if he sits, "
                f"swap in your best available bench bat."
            ),
            "impact": ["OBP", "R", "TB", "RBI"],
        }

    if pos == "BN":
        losing_cats = [c for c in cat_analysis
                       if c["category"] in HITTING_CATS
                       and c["status"] == "losing" and c["flippable"]]
        if losing_cats:
            cat_names = ", ".join(c["category"] for c in losing_cats)
            return {
                "verdict": "consider",
                "rationale": (
                    f"{name} is on the bench but has a game today. "
                    f"You're close in {cat_names} — consider activating."
                ),
                "impact": [c["category"] for c in losing_cats],
            }
        return {
            "verdict": "bench",
            "rationale": f"{name} — bench bat with a game. Current starters look solid.",
            "impact": [],
        }

    sb_cat = next((c for c in cat_analysis if c["category"] == "SB"), None)
    obp_cat = next((c for c in cat_analysis if c["category"] == "OBP"), None)

    strengths = []
    if obp_cat and obp_cat["status"] == "winning":
        strengths.append("protecting your OBP lead")
    if sb_cat and sb_cat["status"] == "winning":
        strengths.append("holding SB")

    if strengths:
        return {
            "verdict": "confirmed",
            "rationale": f"{name} — locked in. {', '.join(strengths).capitalize()}.",
            "impact": [],
        }

    return {
        "verdict": "confirmed",
        "rationale": f"{name} — in the lineup, contributing across categories.",
        "impact": [],
    }


def generate_matchup_advice(
    matchup_data: dict,
    schedule: list[dict],
    bench_players: list[dict] | None = None,
) -> dict:
    """Generate game-by-game matchup advice.

    Returns structured advice grouped by MLB game, with per-player
    verdicts and rationale.
    """
    my_team = matchup_data.get("my_team", {})
    opponent = matchup_data.get("opponent", {})

    cat_analysis = _category_gap_analysis(
        my_team.get("stats", {}),
        opponent.get("stats", {}),
    )

    my_roster = my_team.get("roster", [])
    opp_roster = opponent.get("roster", [])

    score_winning = sum(1 for c in cat_analysis if c["status"] == "winning")
    score_losing = sum(1 for c in cat_analysis if c["status"] == "losing")
    score_tied = sum(1 for c in cat_analysis if c["status"] == "tied")

    # Group players by MLB game
    game_groups: dict[str, dict] = {}

    for player in my_roster:
        mlb_team = player.get("mlb_team", "")
        game = _find_game_for_team(mlb_team, schedule) if mlb_team else None

        if game:
            game_id = str(game.get("game_id", ""))
            away = _abbrev_from_full(game.get("away_team", ""))
            home = _abbrev_from_full(game.get("home_team", ""))
            game_label = f"{away} @ {home}"
        else:
            game_id = f"no_game_{mlb_team}"
            game_label = f"{mlb_team} — Off day"

        if game_id not in game_groups:
            game_groups[game_id] = {
                "game_label": game_label,
                "venue": game.get("venue", "") if game else "",
                "status": game.get("status", "") if game else "No game",
                "away_pitcher": game.get("away_pitcher", "") if game else "",
                "home_pitcher": game.get("home_pitcher", "") if game else "",
                "my_players": [],
                "opp_players": [],
            }

        if _is_pitcher(player.get("position", "")):
            advice = _pitcher_rationale(player, game, cat_analysis)
        else:
            advice = _hitter_rationale(player, game, cat_analysis)

        game_groups[game_id]["my_players"].append({
            **player,
            **advice,
        })

    for player in opp_roster:
        mlb_team = player.get("mlb_team", "")
        game = _find_game_for_team(mlb_team, schedule) if mlb_team else None

        if game:
            game_id = str(game.get("game_id", ""))
            away = _abbrev_from_full(game.get("away_team", ""))
            home = _abbrev_from_full(game.get("home_team", ""))
            game_label = f"{away} @ {home}"
        else:
            game_id = f"no_game_opp_{mlb_team}"
            game_label = f"{mlb_team} — Off day"

        if game_id not in game_groups:
            game_groups[game_id] = {
                "game_label": game_label,
                "venue": game.get("venue", "") if game else "",
                "status": game.get("status", "") if game else "No game",
                "away_pitcher": game.get("away_pitcher", "") if game else "",
                "home_pitcher": game.get("home_pitcher", "") if game else "",
                "my_players": [],
                "opp_players": [],
            }

        game_groups[game_id]["opp_players"].append(player)

    games_list = sorted(
        game_groups.values(),
        key=lambda g: (
            0 if g["my_players"] and g["opp_players"] else
            1 if g["my_players"] else 2,
            -len(g["my_players"]),
        ),
    )

    flippable_cats = [c for c in cat_analysis if c["flippable"]]
    losing_flippable = [c for c in flippable_cats if c["status"] == "losing"]
    winning_close = [c for c in flippable_cats if c["status"] == "winning"]

    top_cats = sum(1 for c in cat_analysis if c["status"] == "winning")
    bottom_cats = sum(1 for c in cat_analysis if c["status"] == "losing")

    if losing_flippable:
        flip_names = ", ".join(c["category"] for c in losing_flippable[:3])
        summary = (
            f"Top-half in {top_cats} categories, bottom-half in {bottom_cats}. "
            f"Best rank-gain targets: **{flip_names}**. Focus roster moves there."
        )
    elif top_cats >= 7:
        summary = (
            f"Strong position — top-half in {top_cats} of 10 categories. "
            f"Protect ratios and maintain counting stat volume."
        )
    elif bottom_cats >= 5:
        summary = (
            f"Behind in {bottom_cats} categories. Aggressive mode — "
            f"activate bench bats, stream starters when ratio-safe, chase volume."
        )
    else:
        summary = (
            f"Competitive across the board — {top_cats} categories in top half. "
            f"Every stat counts. Maximize active roster spots."
        )

    return {
        "week": matchup_data.get("week"),
        "my_team": my_team.get("team_name", ""),
        "opponent": opponent.get("team_name", ""),
        "score": {"winning": score_winning, "losing": score_losing, "tied": score_tied},
        "summary": summary,
        "category_analysis": cat_analysis,
        "games": games_list,
        "date": date.today().isoformat(),
    }
