"""Agent tools for the Bush League Co-Pilot.

Six tools: 4 league tools + 2 live MLB intel tools.
All MLB/news tools use free APIs — zero LLM cost.
"""

from __future__ import annotations

import json
import logging

from backend.api.league import get_league_config
from backend.api.roster import get_my_roster
from backend.api.waivers import get_free_agents
from backend.api.player import get_draft_history, get_matchup
from backend.api.mlb_live import (
    get_todays_schedule,
    get_transactions,
    search_player,
)
from backend.api.web_search import search_player_news, search_news
from backend.cache.league_cache import LeagueCache
from backend.logic.category_scorer import analyze_category_gaps, get_weak_categories
from backend.logic.keeper_calc import calculate_team_keepers, resolve_collisions
from backend.logic.waiver_ranker import rank_free_agents
from backend.trimmer.payload_trimmer import (
    trim_and_log, trim_roster, trim_free_agents, trim_matchup,
)

logger = logging.getLogger(__name__)

# ── League Tools ──────────────────────────────────────────────

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

# ── Live MLB Intel Tools ──────────────────────────────────────

TOOL_MLB_UPDATES = {
    "name": "get_mlb_updates",
    "description": (
        "Get LIVE MLB intel: today's schedule with probable pitchers and venues, "
        "plus recent transactions (IL moves, call-ups, DFAs, trades) from the "
        "last several days. Use this PROACTIVELY before recommending any roster "
        "move to check if a player just hit the IL, got called up, was traded, "
        "or has a start today. Also use when Ben asks about today's games, "
        "pitching matchups, or recent MLB news."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "transaction_days": {
                "type": "integer",
                "description": "How many days of transactions to fetch (default 3, max 7).",
            },
        },
        "required": [],
    },
}

TOOL_PLAYER_LOOKUP = {
    "name": "search_player_info",
    "description": (
        "Deep lookup on a specific player: MLB bio (team, position, bats/throws, "
        "age, status), current season stats from MLB.com, and the latest news "
        "headlines about them. Use this when Ben asks about a specific player, "
        "when you need to verify a player's current status before recommending "
        "a move, or to get injury/performance context for analysis."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "player_name": {
                "type": "string",
                "description": "Full or partial player name (e.g. 'Ohtani', 'Kyle Tucker').",
            },
        },
        "required": ["player_name"],
    },
}

TOOLS = [
    TOOL_GET_ROSTER,
    TOOL_SEARCH_FA,
    TOOL_MATCHUP,
    TOOL_KEEPERS,
    TOOL_MLB_UPDATES,
    TOOL_PLAYER_LOOKUP,
]


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
        matchup_data = await get_matchup()
        trimmed = trim_and_log(matchup_data, trim_matchup, "matchup")
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

    if tool_name == "get_mlb_updates":
        days = min(tool_input.get("transaction_days", 3), 7)
        try:
            schedule = await get_todays_schedule()
        except Exception as exc:
            logger.warning("Schedule fetch failed: %s", exc)
            schedule = []

        try:
            txns = await get_transactions(days=days)
        except Exception as exc:
            logger.warning("Transactions fetch failed: %s", exc)
            txns = []

        return json.dumps({
            "todays_games": schedule[:12],
            "recent_transactions": txns[:25],
            "games_count": len(schedule),
            "transaction_count": len(txns),
        }, default=str)

    if tool_name == "search_player_info":
        player_name = tool_input.get("player_name", "")
        if not player_name:
            return json.dumps({"error": "player_name is required"})

        mlb_data = None
        try:
            mlb_data = await search_player(player_name)
        except Exception as exc:
            logger.warning("MLB player search failed: %s", exc)

        news = []
        try:
            news = await search_player_news(player_name)
        except Exception as exc:
            logger.warning("Player news search failed: %s", exc)

        result = {
            "player": mlb_data or {"error": "Player not found in MLB database"},
            "recent_news": news[:5],
        }
        return json.dumps(result, default=str)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})
