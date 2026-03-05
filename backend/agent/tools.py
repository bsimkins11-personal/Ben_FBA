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
        "Get Ben's full active roster with per-player week stats, "
        "team category ranks (1-12, 1=best in league), and a gap analysis "
        "showing which categories are weakest, how far behind the next rank, "
        "and the league average for each. Use this to diagnose roster strengths, "
        "identify category gaps, and inform any roster move recommendation."
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
        "Search available free agents, scored and ranked by projected impact on "
        "Ben's weakest categories. Returns waiver scores, which categories each "
        "player helps, multi-position eligibility, injury status, and a recommendation. "
        "Use position filter to find specific needs (e.g. 'RP' for S+H help, "
        "'OF' for outfield depth, 'SS' for MI-eligible speed). Call without a "
        "position to get the overall best available."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "position": {
                "type": "string",
                "description": (
                    "Position filter: C, 1B, 2B, 3B, SS, OF, SP, RP. "
                    "Omit for best available across all positions."
                ),
            },
        },
        "required": [],
    },
}

TOOL_MATCHUP = {
    "name": "get_matchup_analysis",
    "description": (
        "Get this week's H2H category matchup — both teams' stats in all 10 "
        "categories and which categories Ben is currently winning, losing, or "
        "tied in. Use this to make tactical in-week decisions: which categories "
        "to push for, which to protect, whether to stream or sit pitchers, "
        "and where a single roster move could flip a category."
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
        "Calculate keeper costs for all roster players using Bush League "
        "constitution rules (6.2, 6.3, 6.7, 6.9). Returns round cost, value "
        "score (20 minus round cost), rule citation, and collision notes for "
        "same-round conflicts. Use this when Ben asks about keepers, dynasty "
        "value, or whether a player is worth holding through a rebuild."
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
