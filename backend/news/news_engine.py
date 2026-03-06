"""Proactive news engine — surfaces MLB intel relevant to Ben's roster.

All data sources are FREE (MLB Stats API + Google News RSS).
No LLM calls — pure data curation. Zero cost.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date

from backend.api.mlb_live import (
    get_todays_schedule,
    get_transactions,
    search_player,
)
from backend.api.web_search import search_news
from backend.api.roster import get_my_roster
from backend.api.player import get_matchup

logger = logging.getLogger(__name__)

_cache: dict = {}
_cache_ts: float = 0
CACHE_TTL = 300  # 5 minutes


def _normalize(name: str) -> str:
    return name.strip().lower()


def _match_player(
    text: str,
    my_names: set[str],
    opp_names: set[str],
) -> tuple[str | None, str]:
    """Check if a player from either roster appears in text.

    Returns (matched_name, "my_roster" | "opponent" | "").
    """
    text_lower = text.lower()
    for name in my_names:
        if name in text_lower:
            return name, "my_roster"
    for name in opp_names:
        if name in text_lower:
            return name, "opponent"
    return None, ""


async def _build_roster_alerts(
    my_names: set[str],
    opp_names: set[str],
    transactions: list[dict],
) -> list[dict]:
    """Flag transactions involving players on either roster."""
    alerts = []
    for txn in transactions:
        player_lower = _normalize(txn.get("player", ""))
        if player_lower in my_names:
            tag = "my_roster"
            priority = "high"
        elif player_lower in opp_names:
            tag = "opponent"
            priority = "medium"
        else:
            continue

        alerts.append({
            "type": "roster_alert",
            "priority": priority,
            "icon": "injury" if "disabled" in txn.get("type", "").lower()
                    else "transaction",
            "headline": txn["description"][:140],
            "player": txn["player"],
            "detail": txn["type"],
            "date": txn.get("date", ""),
            "source": "MLB Transactions",
            "roster_tag": tag,
        })
    return alerts


async def _build_schedule_intel(
    my_names: set[str],
    opp_names: set[str],
    schedule: list[dict],
) -> list[dict]:
    """Today's games with probable pitchers — flag pitchers from both rosters."""
    items = []
    pitcher_items = []

    for game in schedule:
        for side in ("away", "home"):
            pitcher = game.get(f"{side}_pitcher", "TBD")
            pitcher_lower = _normalize(pitcher)
            opponent_side = "home" if side == "away" else "away"

            if pitcher_lower in my_names:
                pitcher_items.append({
                    "type": "start_today",
                    "priority": "high",
                    "icon": "pitching",
                    "headline": (
                        f"{pitcher} starts today vs "
                        f"{game[f'{opponent_side}_team']}"
                    ),
                    "player": pitcher,
                    "detail": f"at {game.get('venue', '')}",
                    "date": date.today().isoformat(),
                    "source": "MLB Schedule",
                    "roster_tag": "my_roster",
                })
            elif pitcher_lower in opp_names:
                pitcher_items.append({
                    "type": "start_today",
                    "priority": "medium",
                    "icon": "pitching",
                    "headline": (
                        f"Opponent's {pitcher} starts today vs "
                        f"{game[f'{opponent_side}_team']}"
                    ),
                    "player": pitcher,
                    "detail": f"at {game.get('venue', '')}",
                    "date": date.today().isoformat(),
                    "source": "MLB Schedule",
                    "roster_tag": "opponent",
                })

    if schedule:
        items.append({
            "type": "schedule_summary",
            "priority": "low",
            "icon": "schedule",
            "headline": f"{len(schedule)} MLB games today",
            "player": "",
            "detail": ", ".join(
                f"{g['away_team']} @ {g['home_team']}"
                for g in schedule[:6]
            ),
            "date": date.today().isoformat(),
            "source": "MLB Schedule",
        })

    return pitcher_items + items


async def _build_waiver_intel(transactions: list[dict]) -> list[dict]:
    """Surface notable call-ups, DFAs, and signings as waiver wire opportunities."""
    items = []
    for txn in transactions:
        desc = txn.get("description", "").lower()
        txn_type = txn.get("type", "").lower()

        is_callup = "recall" in txn_type or "selected" in desc
        is_dfa = "designation" in txn_type
        is_il_return = "reinstated" in desc or "activated" in desc

        if is_callup or is_dfa or is_il_return:
            if is_callup:
                icon, label = "callup", "Call-Up"
            elif is_il_return:
                icon, label = "return", "IL Return"
            else:
                icon, label = "dfa", "DFA"

            items.append({
                "type": "waiver_intel",
                "priority": "medium",
                "icon": icon,
                "headline": txn["description"][:140],
                "player": txn["player"],
                "detail": label,
                "date": txn.get("date", ""),
                "source": "MLB Transactions",
            })

    return items[:10]


_NON_MLB_KEYWORDS = {
    "college", "ncaa", "draft prospect", "high school",
    "wbc", "world baseball classic", "nippon", "kbo",
    "little league", "softball", "cricket",
}


def _is_mlb_article(title: str, snippet: str) -> bool:
    """Filter out non-MLB content (college, international, etc.)."""
    combined = f"{title} {snippet}".lower()
    return not any(kw in combined for kw in _NON_MLB_KEYWORDS)


async def _build_news_items(
    my_names: set[str],
    opp_names: set[str],
) -> list[dict]:
    """Fetch MLB fantasy baseball news, tag items from either roster."""
    try:
        articles = await search_news(
            "MLB fantasy baseball injury roster moves waiver wire",
            max_results=12,
        )
    except Exception:
        logger.warning("News search failed, skipping")
        return []

    items = []
    for article in articles:
        title = article.get("title", "")
        snippet = article.get("snippet", "")

        if not _is_mlb_article(title, snippet):
            continue

        combined = f"{title} {snippet}"
        matched_player, roster_tag = _match_player(combined, my_names, opp_names)

        if roster_tag == "my_roster":
            priority = "high"
        elif roster_tag == "opponent":
            priority = "medium"
        else:
            priority = "low"

        items.append({
            "type": "news",
            "priority": priority,
            "icon": "news",
            "headline": title[:140],
            "player": matched_player or "",
            "detail": snippet[:200],
            "date": article.get("published", ""),
            "source": article.get("source", ""),
            "url": article.get("url", ""),
            "roster_tag": roster_tag,
        })

    return items[:8]


async def get_curated_news() -> dict:
    """Main entry point — returns prioritized, roster-aware news feed.

    Cached for 5 minutes to avoid hammering external APIs.
    """
    global _cache, _cache_ts

    if _cache and (time.time() - _cache_ts) < CACHE_TTL:
        return _cache

    roster_data, matchup_data = await asyncio.gather(
        get_my_roster(),
        get_matchup(),
        return_exceptions=True,
    )

    if isinstance(roster_data, Exception):
        logger.warning("Roster fetch failed: %s", roster_data)
        roster_data = {}
    if isinstance(matchup_data, Exception):
        logger.warning("Matchup fetch failed: %s", matchup_data)
        matchup_data = {}

    my_names = {
        _normalize(p.get("name", ""))
        for p in roster_data.get("roster", [])
        if p.get("name")
    }

    opp_roster = matchup_data.get("opponent", {}).get("roster", [])
    opp_names = {
        _normalize(p.get("name", ""))
        for p in opp_roster
        if p.get("name")
    }

    schedule, transactions = await asyncio.gather(
        get_todays_schedule(),
        get_transactions(days=3),
        return_exceptions=True,
    )

    if isinstance(schedule, Exception):
        logger.warning("Schedule fetch failed: %s", schedule)
        schedule = []
    if isinstance(transactions, Exception):
        logger.warning("Transactions fetch failed: %s", transactions)
        transactions = []

    roster_alerts, schedule_intel, waiver_intel, news_items = (
        await asyncio.gather(
            _build_roster_alerts(my_names, opp_names, transactions),
            _build_schedule_intel(my_names, opp_names, schedule),
            _build_waiver_intel(transactions),
            _build_news_items(my_names, opp_names),
            return_exceptions=True,
        )
    )

    for result_name, result in [
        ("roster_alerts", roster_alerts),
        ("schedule_intel", schedule_intel),
        ("waiver_intel", waiver_intel),
        ("news_items", news_items),
    ]:
        if isinstance(result, Exception):
            logger.warning("%s failed: %s", result_name, result)

    all_items = []
    for batch in [roster_alerts, schedule_intel, waiver_intel, news_items]:
        if isinstance(batch, list):
            all_items.extend(batch)

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
    all_items.sort(key=lambda x: PRIORITY_ORDER.get(x.get("priority", "low"), 2))

    _cache = {
        "generated_at": date.today().isoformat(),
        "total_items": len(all_items),
        "items": all_items,
        "games_today": len(schedule) if isinstance(schedule, list) else 0,
    }
    _cache_ts = time.time()

    return _cache
