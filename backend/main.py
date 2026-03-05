import json
import logging

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.api.league import get_league_config
from backend.api.roster import get_my_roster, get_roster_stats
from backend.api.waivers import get_free_agents
from backend.api.player import get_draft_history, get_matchup
from backend.logic.category_scorer import analyze_category_gaps, get_weak_categories
from backend.logic.keeper_calc import calculate_team_keepers, resolve_collisions
from backend.logic.waiver_ranker import rank_free_agents
from backend.cache.league_cache import LeagueCache
from backend.agent.copilot import stream_copilot_response

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Bush League Co-Pilot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/league")
async def api_league():
    return await get_league_config()


@app.get("/api/roster")
async def api_roster():
    return await get_my_roster()


@app.get("/api/standings")
async def api_standings():
    standings_data = LeagueCache().get_standings()
    roster_data = await get_my_roster()
    my_ranks = roster_data.get("category_ranks", {})
    team_totals = [
        t.get("category_totals", {})
        for t in standings_data.get("standings", [])
    ]
    gaps = analyze_category_gaps(my_ranks, team_totals)
    return {
        **standings_data,
        "gap_analysis": gaps,
        "weak_categories": get_weak_categories(gaps),
    }


@app.get("/api/matchup")
async def api_matchup():
    return await get_matchup()


@app.get("/api/free-agents")
async def api_free_agents(position: str | None = Query(None)):
    fa_data = await get_free_agents(position=position)
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
        max_results=15,
    )
    return {"recommendations": ranked, "targeting": weak}


@app.get("/api/keepers")
async def api_keepers():
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
    return {"keepers": keepers}


@app.post("/api/chat")
async def api_chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")
    history = body.get("history", [])

    async def event_stream():
        async for event in stream_copilot_response(user_message, history):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
