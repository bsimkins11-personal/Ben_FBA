import json
import logging

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from backend.api.league import get_league_config
from backend.api.roster import get_my_roster, get_roster_stats
from backend.api.waivers import get_free_agents
from backend.api.player import get_draft_history, get_matchup
from backend.logic.category_scorer import analyze_category_gaps, get_weak_categories
from backend.logic.keeper_calc import calculate_team_keepers, resolve_collisions
from backend.logic.waiver_ranker import rank_free_agents
from backend.api.standings import get_standings
from backend.agent.copilot import stream_copilot_response
from backend.news.news_engine import get_curated_news
from backend.logic.matchup_advisor import generate_matchup_advice
from backend.logic.critical_alerts import get_critical_alerts
from backend.api.mlb_live import get_todays_schedule
from backend.auth.yahoo_auth import (
    get_login_url,
    exchange_code,
    get_token_store,
    restore_tokens_from_db,
    clear_stored_tokens,
)
from backend.api.yahoo_client import discover_league
from backend.config import FRONTEND_URL

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Bush League Co-Pilot", version="0.1.0")


@app.on_event("startup")
async def _startup():
    restored = await restore_tokens_from_db()
    if restored:
        store = get_token_store()
        logging.getLogger(__name__).info(
            "Auto-restored Yahoo session (league=%s)", store.league_key
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://benfba.vercel.app",
        "https://benfba-bryan-simkins.vercel.app",
        "https://benfba-git-main-bryan-simkins.vercel.app",
    ],
    allow_origin_regex=r"https://ben-.*-bryan-simkins\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ── Yahoo OAuth Routes ──────────────────────────────────────────────


@app.get("/auth/yahoo")
async def auth_yahoo_login():
    """Redirect user to Yahoo OAuth login page."""
    url = get_login_url()
    return RedirectResponse(url)


@app.get("/auth/yahoo/callback")
async def auth_yahoo_callback(code: str = "", state: str = "", error: str = ""):
    """Handle Yahoo OAuth callback — exchange code, discover league, redirect."""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}?auth=error&reason={error}")

    try:
        await exchange_code(code, state)
        await discover_league()
        from backend.auth.yahoo_auth import _persist_tokens
        await _persist_tokens()
        return RedirectResponse(f"{FRONTEND_URL}?auth=success")
    except Exception as e:
        logging.getLogger(__name__).error("Yahoo OAuth callback failed: %s", e)
        return RedirectResponse(f"{FRONTEND_URL}?auth=error&reason=token_exchange_failed")


@app.get("/auth/status")
async def auth_status():
    """Return current authentication state for the frontend."""
    store = get_token_store()
    return {
        "authenticated": store.is_authenticated,
        "mode": "live" if store.is_authenticated else "synthetic",
        "league_key": store.league_key,
        "team_key": store.team_key,
    }


@app.post("/auth/logout")
async def auth_logout():
    """Clear stored tokens from memory and Postgres."""
    await clear_stored_tokens()
    return {"status": "logged_out", "mode": "synthetic"}


@app.get("/api/league")
async def api_league():
    return await get_league_config()


@app.get("/api/roster")
async def api_roster():
    return await get_my_roster()


@app.get("/api/standings")
async def api_standings():
    standings_data = await get_standings()
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
    standings_data = await get_standings()

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


@app.get("/api/alerts")
async def api_alerts():
    """Mission-critical alerts only — IL moves, DTD starters, elite pickups."""
    alerts = await get_critical_alerts()
    return {"alerts": alerts}


@app.get("/api/matchup/advisor")
async def api_matchup_advisor():
    """Game-by-game matchup advice with per-player verdicts and rationale."""
    matchup_data = await get_matchup()
    try:
        schedule = await get_todays_schedule()
    except Exception:
        schedule = []
    return generate_matchup_advice(matchup_data, schedule)


@app.get("/api/news")
async def api_news():
    """Proactive news feed — roster-aware, prioritized, free data sources."""
    return await get_curated_news()


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
