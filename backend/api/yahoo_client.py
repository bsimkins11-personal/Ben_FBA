"""Yahoo Fantasy Sports API v2 — live read-only client.

All endpoints return parsed JSON (using Yahoo's ?format=json parameter).
Token refresh is handled automatically via get_valid_token().
"""

from __future__ import annotations

import logging

import httpx

from backend.auth.yahoo_auth import get_valid_token, get_token_store
from backend.config import YAHOO_STAT_IDS

logger = logging.getLogger(__name__)

YAHOO_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"

_STAT_ID_TO_NAME = {v: k for k, v in YAHOO_STAT_IDS.items()}

_POSITION_MAP = {
    "C": "C", "1B": "1B", "2B": "2B", "3B": "3B", "SS": "SS",
    "OF": "OF", "LF": "OF", "CF": "OF", "RF": "OF",
    "Util": "Util", "CI": "CI", "MI": "MI",
    "SP": "SP", "RP": "RP", "P": "P",
    "BN": "BN", "DL": "DL", "IL": "DL", "IL+": "DL",
    "NA": "NA",
}


async def _get(path: str, params: dict | None = None) -> dict:
    """Authenticated GET against Yahoo Fantasy API, returns JSON."""
    token = await get_valid_token()
    url = f"{YAHOO_BASE}{path}"

    query = params or {}
    query["format"] = "json"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            url,
            params=query,
            headers={"Authorization": f"Bearer {token}"},
        )

    if resp.status_code == 401:
        logger.warning("Yahoo 401 — attempting token refresh")
        from backend.auth.yahoo_auth import refresh_tokens
        token = await refresh_tokens()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                params=query,
                headers={"Authorization": f"Bearer {token}"},
            )

    if resp.status_code != 200:
        logger.error("Yahoo API %s failed: %s", path, resp.status_code)
        raise RuntimeError(f"Yahoo API error: {resp.status_code}")

    return resp.json()


def _extract_stat_value(stat_obj: dict) -> float | int:
    """Convert Yahoo stat value strings to numbers."""
    val = stat_obj.get("value", "0")
    if val in ("", "-"):
        return 0
    try:
        return float(val) if "." in str(val) else int(val)
    except (ValueError, TypeError):
        return 0


def _parse_player_stats(stats_list: list) -> dict:
    """Convert Yahoo stat_id-based stats to our named stat dict."""
    result = {}
    for s in stats_list:
        stat = s.get("stat", s)
        stat_id = int(stat.get("stat_id", 0))
        name = _STAT_ID_TO_NAME.get(stat_id)
        if name:
            result[name] = _extract_stat_value(stat)
    return result


def _parse_eligible_positions(pos_list: list) -> list[str]:
    """Extract position abbreviations from Yahoo position objects."""
    positions = []
    for p in pos_list:
        pos_str = p if isinstance(p, str) else p.get("position", "")
        mapped = _POSITION_MAP.get(pos_str, pos_str)
        if mapped and mapped not in positions:
            positions.append(mapped)
    return positions


def _dig(data: dict, *keys):
    """Safely traverse nested Yahoo JSON response."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list):
            try:
                current = current[int(key)]
            except (IndexError, ValueError):
                return None
        else:
            return None
        if current is None:
            return None
    return current


async def discover_league() -> dict:
    """Find Ben's MLB league and team via the authenticated user's games."""
    data = await _get("/users;use_login=1/games;game_keys=mlb/teams")

    store = get_token_store()
    games = _dig(data, "fantasy_content", "users", "0", "user")
    if not games:
        logger.warning("discover_league: no user data found in response")
        logger.debug("discover_league raw response keys: %s", list(data.keys()) if data else "None")
        return {"league_key": "", "team_key": "", "team_name": "", "league_name": ""}

    game_list = games[1].get("games", {}) if len(games) > 1 else {}

    if not game_list or game_list.get("count", 0) == 0:
        logger.warning("discover_league: user has no MLB fantasy games")
        return {"league_key": "", "team_key": "", "team_name": "", "league_name": ""}

    league_key = ""
    team_key = ""
    team_name = ""
    league_name = ""

    for k, v in game_list.items():
        if k == "count":
            continue
        game = v.get("game", []) if isinstance(v, dict) else v
        if isinstance(game, list) and len(game) > 1:
            teams_data = game[1].get("teams", {})
            for tk, tv in teams_data.items():
                if tk == "count":
                    continue
                team_info = tv.get("team", [[]])[0] if isinstance(tv, dict) else []
                for item in team_info:
                    if isinstance(item, dict):
                        if "team_key" in item:
                            team_key = item["team_key"]
                        if "team_id" in item:
                            pass
                        if "name" in item:
                            team_name = item["name"]
                        if "team_logos" in item:
                            pass

    if team_key:
        parts = team_key.rsplit(".t.", 1)
        if len(parts) == 2:
            league_key = parts[0]

    store.league_key = league_key
    store.team_key = team_key

    logger.info(
        "Discovered league=%s team=%s (%s)", league_key, team_key, team_name
    )

    return {
        "league_key": league_key,
        "team_key": team_key,
        "team_name": team_name,
        "league_name": league_name,
    }


async def get_league_settings(league_key: str) -> dict:
    """Fetch league metadata and scoring settings."""
    data = await _get(f"/league/{league_key}/settings")
    league = _dig(data, "fantasy_content", "league")
    if not league or not isinstance(league, list):
        return {}

    meta = league[0] if league else {}
    settings = league[1].get("settings", [{}])[0] if len(league) > 1 else {}

    scoring_cats = {"hitting": [], "pitching": []}
    for cat_wrapper in settings.get("stat_categories", {}).get("stats", []):
        cat = cat_wrapper.get("stat", {})
        stat_id = int(cat.get("stat_id", 0))
        name = _STAT_ID_TO_NAME.get(stat_id)
        if name:
            group = cat.get("position_type", "")
            if group == "B":
                scoring_cats["hitting"].append(name)
            else:
                scoring_cats["pitching"].append(name)

    roster_positions = []
    for rp_wrapper in settings.get("roster_positions", []):
        rp = rp_wrapper.get("roster_position", {})
        pos = rp.get("position", "")
        count = int(rp.get("count", 1))
        mapped = _POSITION_MAP.get(pos, pos)
        roster_positions.extend([mapped] * count)

    return {
        "league_key": meta.get("league_key", league_key),
        "name": meta.get("name", ""),
        "num_teams": int(meta.get("num_teams", 12)),
        "scoring_type": meta.get("scoring_type", ""),
        "current_week": int(meta.get("current_week", 1)),
        "season": meta.get("season", ""),
        "scoring_categories": scoring_cats,
        "roster_positions": roster_positions,
        "max_keepers": 8,
    }


async def get_standings(league_key: str) -> dict:
    """Fetch league standings with category totals."""
    data = await _get(f"/league/{league_key}/standings")
    league = _dig(data, "fantasy_content", "league")
    if not league or len(league) < 2:
        return {"standings": []}

    standings_data = league[1].get("standings", [{}])
    teams_wrapper = standings_data[0].get("teams", {}) if standings_data else {}

    standings = []
    for k, v in teams_wrapper.items():
        if k == "count":
            continue
        team_info = v.get("team", []) if isinstance(v, dict) else []
        if not team_info:
            continue

        meta_list = team_info[0] if isinstance(team_info[0], list) else [team_info[0]]
        meta = {}
        for item in meta_list:
            if isinstance(item, dict):
                meta.update(item)

        stats_block = team_info[1] if len(team_info) > 1 else {}
        team_standings = stats_block.get("team_standings", {})
        outcomes = team_standings.get("outcome_totals", {})

        stat_list = stats_block.get("team_stats", {}).get("stats", [])
        cat_totals = _parse_player_stats(stat_list)

        standings.append({
            "rank": int(team_standings.get("rank", 0)),
            "team_key": meta.get("team_key", ""),
            "team_name": meta.get("name", ""),
            "record": {
                "wins": int(outcomes.get("wins", 0)),
                "losses": int(outcomes.get("losses", 0)),
                "ties": int(outcomes.get("ties", 0)),
            },
            "points": float(team_standings.get("points_for", 0)),
            "category_ranks": {},
            "category_totals": cat_totals,
        })

    # Compute category_ranks from category_totals (Yahoo doesn't provide Roto ranks directly)
    from backend.logic.category_scorer import ALL_CATS, LOWER_BETTER
    for cat in ALL_CATS:
        values = [(i, t.get("category_totals", {}).get(cat, 0)) for i, t in enumerate(standings)]
        if cat in LOWER_BETTER:
            values.sort(key=lambda x: x[1])  # lowest = rank 1
        else:
            values.sort(key=lambda x: x[1], reverse=True)  # highest = rank 1
        for rank, (idx, _) in enumerate(values, 1):
            standings[idx]["category_ranks"][cat] = rank

    return {"standings": standings}


def _extract_selected_position(player_data) -> str:
    """Search player_data for selected_position value from Yahoo roster API."""

    def _find_sp(obj):
        """Find and return the selected_position subtree."""
        if isinstance(obj, dict):
            if "selected_position" in obj:
                return obj["selected_position"]
            for v in obj.values():
                r = _find_sp(v)
                if r is not None:
                    return r
        elif isinstance(obj, list):
            for item in obj:
                r = _find_sp(item)
                if r is not None:
                    return r
        return None

    def _pos_from_sp(sp) -> str:
        """Extract position string from selected_position value."""
        if isinstance(sp, str):
            return sp
        if isinstance(sp, dict):
            return sp.get("position", "")
        if isinstance(sp, list):
            for item in sp:
                if isinstance(item, dict) and "position" in item:
                    return item["position"]
        return ""

    sp_node = _find_sp(player_data)
    if sp_node is not None:
        pos = _pos_from_sp(sp_node)
        logger.debug("selected_position found: %s -> %s", sp_node, pos)
        return pos
    return ""


async def get_roster(team_key: str) -> dict:
    """Fetch team roster with player stats."""
    data = await _get(f"/team/{team_key}/roster/players/stats")
    team = _dig(data, "fantasy_content", "team")
    if not team or len(team) < 2:
        return {"roster": []}

    meta_list = team[0] if isinstance(team[0], list) else [team[0]]
    meta = {}
    for item in meta_list:
        if isinstance(item, dict):
            meta.update(item)

    players_wrapper = team[1].get("roster", {}).get("0", {}).get("players", {})
    if not players_wrapper:
        players_wrapper = _dig(team, "1", "roster", "0", "players") or {}

    roster = []
    for k, v in players_wrapper.items():
        if k == "count":
            continue
        player_data = v.get("player", []) if isinstance(v, dict) else []
        if not player_data:
            continue

        info_list = player_data[0] if isinstance(player_data[0], list) else [player_data[0]]
        info = {}
        eligible = []
        status = ""
        for item in info_list:
            if isinstance(item, dict):
                if "player_key" in item:
                    info.update(item)
                if "name" in item:
                    info["full_name"] = item["name"].get("full", "")
                if "eligible_positions" in item:
                    eligible = _parse_eligible_positions(
                        item["eligible_positions"]
                    )
                if "status" in item:
                    status = item.get("status", "")
                if "status_full" in item:
                    status = item.get("status_full", status)

        sel_pos = _extract_selected_position(player_data)
        if sel_pos:
            info["position"] = sel_pos

        stat_list = player_data[1].get("player_stats", {}).get("stats", []) if len(player_data) > 1 else []
        stats = _parse_player_stats(stat_list)

        name = info.get("full_name", info.get("name", {}).get("full", ""))
        raw_pos = info.get("position", "")
        position = _POSITION_MAP.get(raw_pos, raw_pos)

        if not position and eligible:
            position = _POSITION_MAP.get(eligible[0], eligible[0])

        if status and status not in ("IL10", "IL60", "IL15", "DTD"):
            if "IL" in status.upper():
                status = "IL10"
            elif "DTD" in status.upper() or "day" in status.lower():
                status = "DTD"

        roster.append({
            "name": name,
            "position": position,
            "eligible_positions": eligible,
            "status": status,
            "stats": stats,
        })

    return {
        "team_key": meta.get("team_key", team_key),
        "team_name": meta.get("name", ""),
        "roster": roster,
    }


async def get_scoreboard(league_key: str, week: int | None = None) -> dict:
    """Fetch the weekly matchup scoreboard."""
    week_param = f";week={week}" if week else ""
    data = await _get(f"/league/{league_key}/scoreboard{week_param}")
    league = _dig(data, "fantasy_content", "league")
    if not league or len(league) < 2:
        return {}

    scoreboard = league[1].get("scoreboard", {})
    matchups_wrapper = scoreboard.get("0", {}).get("matchups", {})
    if not matchups_wrapper:
        return {}

    store = get_token_store()

    for mk, mv in matchups_wrapper.items():
        if mk == "count":
            continue
        matchup = mv.get("matchup", {}) if isinstance(mv, dict) else {}
        teams_in_matchup = matchup.get("0", {}).get("teams", {})

        team_data = []
        for tk, tv in teams_in_matchup.items():
            if tk == "count":
                continue
            t = tv.get("team", []) if isinstance(tv, dict) else []
            if not t:
                continue

            t_meta_list = t[0] if isinstance(t[0], list) else [t[0]]
            t_meta = {}
            for item in t_meta_list:
                if isinstance(item, dict):
                    t_meta.update(item)

            stat_list = t[1].get("team_stats", {}).get("stats", []) if len(t) > 1 else []
            stats = _parse_player_stats(stat_list)

            team_data.append({
                "team_key": t_meta.get("team_key", ""),
                "team_name": t_meta.get("name", ""),
                "stats": stats,
            })

        my_idx = next(
            (i for i, td in enumerate(team_data) if td["team_key"] == store.team_key),
            None,
        )
        if my_idx is not None:
            opp_idx = 1 - my_idx
            stat_cats = matchup.get("stat_winners", [])
            cat_results = {}
            for sw in stat_cats:
                winner = sw.get("stat_winner", {})
                stat_id = int(winner.get("stat_id", 0))
                name = _STAT_ID_TO_NAME.get(stat_id)
                if not name:
                    continue
                winner_key = winner.get("winner_team_key", "")
                if winner.get("is_tied", "0") == "1":
                    cat_results[name] = "tied"
                elif winner_key == store.team_key:
                    cat_results[name] = "winning"
                else:
                    cat_results[name] = "losing"

            return {
                "week": matchup.get("week", week),
                "my_team": team_data[my_idx],
                "opponent": team_data[opp_idx],
                "category_results": cat_results,
            }

    return {}


async def get_free_agents(
    league_key: str,
    position: str | None = None,
    count: int = 25,
) -> dict:
    """Fetch free agents from the league."""
    params = ";status=FA"
    if position:
        params += f";position={position}"
    params += f";count={count}"

    try:
        data = await _get(f"/league/{league_key}/players{params}")
    except Exception as exc:
        logger.warning("Free agents fetch failed: %s", exc)
        return {"free_agents": []}

    league = _dig(data, "fantasy_content", "league")
    if not league or len(league) < 2:
        return {"free_agents": []}

    players_wrapper = league[1].get("players", {})
    agents = []

    for k, v in players_wrapper.items():
        if k == "count":
            continue
        player_data = v.get("player", []) if isinstance(v, dict) else []
        if not player_data:
            continue

        info_list = player_data[0] if isinstance(player_data[0], list) else [player_data[0]]
        info = {}
        eligible = []
        status = ""
        for item in info_list:
            if isinstance(item, dict):
                if "player_key" in item:
                    info.update(item)
                if "name" in item:
                    info["full_name"] = item["name"].get("full", "")
                if "eligible_positions" in item:
                    eligible = _parse_eligible_positions(item["eligible_positions"])
                if "status" in item:
                    status = item.get("status", "")

        stat_list = player_data[1].get("player_stats", {}).get("stats", []) if len(player_data) > 1 else []
        stats = _parse_player_stats(stat_list)

        name = info.get("full_name", info.get("name", {}).get("full", ""))
        position_primary = eligible[0] if eligible else ""

        agents.append({
            "name": name,
            "position": position_primary,
            "eligible_positions": eligible,
            "status": status,
            "ownership": "FA",
            "projected_stats": stats,
        })

    return {"free_agents": agents}


async def get_draft_results(league_key: str) -> dict:
    """Fetch draft results for keeper calculations."""
    data = await _get(f"/league/{league_key}/draftresults")
    league = _dig(data, "fantasy_content", "league")
    if not league or len(league) < 2:
        return {"draft": []}

    results_wrapper = league[1].get("draft_results", {})
    draft = []

    for k, v in results_wrapper.items():
        if k == "count":
            continue
        result = v.get("draft_result", {}) if isinstance(v, dict) else {}
        if not result:
            continue

        draft.append({
            "round": int(result.get("round", 0)),
            "pick": int(result.get("pick", 0)),
            "player": result.get("player_key", ""),
            "team_key": result.get("team_key", ""),
        })

    return {"draft": draft}
