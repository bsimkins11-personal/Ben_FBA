"""Four agent tools for the Bush League Co-Pilot."""

from __future__ import annotations

import json

from backend.api.league import get_league_config
from backend.api.roster import get_my_roster
from backend.api.waivers import get_free_agents
from backend.api.player import get_draft_history, get_matchup
from backend.cache.league_cache import LeagueCache
from backend.logic.category_scorer import analyze_category_gaps, get_weak_categories
from backend.logic.keeper_calc import calculate_team_keepers, resolve_collisions
from backend.logic.waiver_ranker import rank_free_agents
from backend.trimmer.payload_trimmer import trim_and_log, trim_roster, trim_free_agents, trim_matchup

TOOL_GET_ROSTER = {
    "name": "get_roster_and_standings",
    "description": (
        "Returns the manager's current roster with player stats, "
        "category ranks (1-12 per category), and a gap analysis "
        "showing which categories are weakest and how far behind the next rank."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

TOOL_SEARCH_FA = {
    "name": "search_free_agents",
    "description": (
        "Search available free agents on the waiver wire. "
        "Returns players ranked by how much they help the team's weakest categories. "
        "Optionally filter by position."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "position": {
                "type": "string",
                "description": "Filter by position (e.g. 'SS', 'OF', 'SP', 'RP'). Optional.",
            },
        },
        "required": [],
    },
}

TOOL_MATCHUP = {
    "name": "get_matchup_analysis",
    "description": (
        "Returns the current week's H2H category matchup breakdown — "
        "stats for both teams and which categories are winning/losing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

TOOL_KEEPERS = {
    "name": "calculate_keepers",
    "description": (
        "Calculate keeper costs for all roster players based on draft history "
        "and Bush League constitution rules. Returns each player's round cost, "
        "value score, and any collision notes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

TOOLS = [TOOL_GET_ROSTER, TOOL_SEARCH_FA, TOOL_MATCHUP, TOOL_KEEPERS]


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return a JSON string result."""

    if tool_name == "get_roster_and_standings":
        roster_data = await get_my_roster()
        standings_data = LeagueCache().get_standings()

        my_ranks = roster_data.get("category_ranks", {})
        team_totals = [
            t.get("category_totals", {})
            for t in standings_data.get("standings", [])
        ]
        gaps = analyze_category_gaps(my_ranks, team_totals)
        weak = get_weak_categories(gaps)

        trimmed = trim_and_log(
            {"players": roster_data.get("roster", [])},
            trim_roster,
            "roster",
        )

        result = {
            "team_name": roster_data.get("team_name"),
            "week_stats": roster_data.get("week_stats"),
            "category_ranks": my_ranks,
            "gap_analysis": gaps,
            "weakest_categories": weak,
            "roster": trimmed.get("players", []),
        }
        return json.dumps(result, default=str)

    if tool_name == "search_free_agents":
        position = tool_input.get("position")
        fa_data = await get_free_agents(position=None)
        roster_data = await get_my_roster()
        standings_data = LeagueCache().get_standings()

        my_ranks = roster_data.get("category_ranks", {})
        team_totals = [
            t.get("category_totals", {})
            for t in standings_data.get("standings", [])
        ]
        gaps = analyze_category_gaps(my_ranks, team_totals)
        weak = get_weak_categories(gaps)

        ranked = rank_free_agents(
            fa_data.get("free_agents", []),
            weak,
            position_filter=position,
            max_results=10,
        )
        return json.dumps({"recommendations": ranked, "targeting": weak}, default=str)

    if tool_name == "get_matchup_analysis":
        matchup = await get_matchup()
        trimmed = trim_and_log(matchup, trim_matchup, "matchup")
        return json.dumps(trimmed, default=str)

    if tool_name == "calculate_keepers":
        roster_data = await get_my_roster()
        draft_data = await get_draft_history()
        config = await get_league_config()

        keepers = calculate_team_keepers(
            roster_data.get("roster", []),
            draft_data.get("draft", []),
            teams_in_league=config.get("num_teams", 12),
            max_keepers=config.get("max_keepers", 8),
        )
        keepers = resolve_collisions(keepers, config.get("num_teams", 12))
        return json.dumps({"keepers": keepers}, default=str)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})
