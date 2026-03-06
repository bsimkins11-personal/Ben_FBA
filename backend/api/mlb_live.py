"""Real-time MLB data from the public Stats API (statsapi.mlb.com).

No authentication required. All endpoints return JSON.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

MLB_API = "https://statsapi.mlb.com/api/v1"
TIMEOUT = httpx.Timeout(10.0)


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{MLB_API}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()


async def get_todays_schedule() -> list[dict]:
    """Today's MLB games with probable pitchers, status, and venue."""
    today = date.today().isoformat()
    data = await _get("/schedule", {
        "sportId": 1,
        "date": today,
        "hydrate": "probablePitcher,venue,linescore",
    })
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            away = g.get("teams", {}).get("away", {})
            home = g.get("teams", {}).get("home", {})
            games.append({
                "game_id": g.get("gamePk"),
                "status": g.get("status", {}).get("detailedState", ""),
                "away_team": away.get("team", {}).get("name", ""),
                "away_pitcher": away.get("probablePitcher", {}).get("fullName", "TBD"),
                "away_score": away.get("score"),
                "home_team": home.get("team", {}).get("name", ""),
                "home_pitcher": home.get("probablePitcher", {}).get("fullName", "TBD"),
                "home_score": home.get("score"),
                "venue": g.get("venue", {}).get("name", ""),
            })
    return games


MLB_TEAM_IDS = {
    108, 109, 110, 111, 112, 113, 114, 115, 116, 117,  # AL
    118, 119, 120, 121, 133, 134, 135, 136, 137, 138,  # NL
    139, 140, 141, 142, 143, 144, 145, 146, 147, 158,  # NL + AL
}

_NON_MLB_TEAM_KEYWORDS = {
    "united states", "dominican republic", "puerto rico", "venezuela",
    "japan", "korea", "chinese taipei", "mexico", "cuba", "canada",
    "great britain", "netherlands", "italy", "israel", "australia",
    "colombia", "panama", "nicaragua", "czech republic", "brazil",
    "south africa", "germany", "france", "spain", "hong kong",
    "new zealand", "philippines",
}

_MLB_TEAM_NAMES = {
    "arizona diamondbacks", "atlanta braves", "baltimore orioles",
    "boston red sox", "chicago cubs", "chicago white sox",
    "cincinnati reds", "cleveland guardians", "colorado rockies",
    "detroit tigers", "houston astros", "kansas city royals",
    "los angeles angels", "los angeles dodgers", "miami marlins",
    "milwaukee brewers", "minnesota twins", "new york mets",
    "new york yankees", "oakland athletics", "philadelphia phillies",
    "pittsburgh pirates", "san diego padres", "san francisco giants",
    "seattle mariners", "st. louis cardinals", "tampa bay rays",
    "texas rangers", "toronto blue jays", "washington nationals",
}


async def get_transactions(days: int = 5) -> list[dict]:
    """Recent MLB transactions: IL moves, call-ups, DFAs, trades, signings.

    Filters to fantasy-relevant types from the 30 MLB clubs only —
    excludes international, college, and minor-league-only moves.
    """
    end = date.today()
    start = end - timedelta(days=days)
    data = await _get("/transactions", {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
    })

    RELEVANT_TYPES = {
        "Disabled List", "Reassignment", "Roster Swap",
        "Status Change", "Trade", "Signing", "Waiver Claim",
        "Free Agent Signing", "Optional Assignment", "Outright Assignment",
        "Recall", "Designation for Assignment",
    }

    EXCLUDE_KEYWORDS = {
        "high school", "workout", "minor league camp",
        "assigned to spring training",
    }

    txns = []
    for t in data.get("transactions", []):
        type_cd = t.get("typeDesc", "")
        if not any(rt.lower() in type_cd.lower() for rt in RELEVANT_TYPES):
            continue

        team = t.get("team", {})
        team_id = team.get("id")
        team_name_lower = team.get("name", "").lower()

        if team_id and team_id not in MLB_TEAM_IDS:
            continue
        if any(kw in team_name_lower for kw in _NON_MLB_TEAM_KEYWORDS):
            continue

        desc_lower = t.get("description", "").lower()
        if any(kw in desc_lower for kw in EXCLUDE_KEYWORDS):
            continue

        if any(kw in desc_lower for kw in _NON_MLB_TEAM_KEYWORDS):
            continue

        # When team data is missing (common in pre-season), only keep
        # transactions that reference a real MLB club by name
        if not team_id and not team.get("name"):
            if not any(tn in desc_lower for tn in _MLB_TEAM_NAMES):
                continue

        player = t.get("person", {})
        resolved_team = team.get("name", "")
        if not resolved_team:
            for tn in _MLB_TEAM_NAMES:
                if tn in desc_lower:
                    resolved_team = tn.title()
                    break

        txns.append({
            "player": player.get("fullName", "Unknown"),
            "player_id": player.get("id"),
            "team": resolved_team,
            "type": type_cd,
            "description": t.get("description", "")[:200],
            "date": t.get("date", ""),
        })

    return txns[:50]


async def search_player(name: str) -> dict | None:
    """Look up a player by name. Returns bio, position, team, and status."""
    data = await _get("/people/search", {"names": name, "sportId": 1})
    people = data.get("people", [])
    if not people:
        return None

    p = people[0]
    pid = p.get("id")

    result = {
        "id": pid,
        "name": p.get("fullName", ""),
        "team": p.get("currentTeam", {}).get("name", ""),
        "position": p.get("primaryPosition", {}).get("abbreviation", ""),
        "bats": p.get("batSide", {}).get("code", ""),
        "throws": p.get("pitchHand", {}).get("code", ""),
        "age": p.get("currentAge"),
        "status": p.get("status", {}).get("description", "Active"),
    }

    try:
        stats_data = await _get(f"/people/{pid}", {
            "hydrate": "currentTeam,stats(group=[hitting,pitching],type=season)",
        })
        person = stats_data.get("people", [{}])[0]
        for stat_group in person.get("stats", []):
            splits = stat_group.get("splits", [])
            if splits:
                result["season_stats"] = splits[0].get("stat", {})
                result["stat_group"] = stat_group.get("group", {}).get("displayName", "")
                break
    except Exception:
        logger.debug("Could not fetch season stats for %s", name)

    return result


async def get_standings_snapshot() -> list[dict]:
    """Current MLB division standings."""
    data = await _get("/standings", {
        "leagueId": "103,104",
        "season": str(date.today().year),
        "standingsTypes": "regularSeason",
    })
    teams = []
    for record in data.get("records", []):
        div = record.get("division", {}).get("name", "")
        for t in record.get("teamRecords", []):
            teams.append({
                "team": t.get("team", {}).get("name", ""),
                "division": div,
                "wins": t.get("wins", 0),
                "losses": t.get("losses", 0),
                "pct": t.get("winningPercentage", ""),
                "streak": t.get("streak", {}).get("streakCode", ""),
                "runs_scored": t.get("runsScored", 0),
                "runs_allowed": t.get("runsAllowed", 0),
            })
    return teams
