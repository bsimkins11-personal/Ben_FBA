"""Critical alerts — mission-critical roster situations only.

These fire for genuinely urgent events that require immediate action:
  - Active roster player placed on IL
  - Active starter marked DTD (not bench)
  - Elite free agent just became available (call-up, another team's drop)
  - Roster player traded or DFA'd

NOT for: general news, schedule info, low-priority intel.
Zero LLM cost — pure data logic.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date

from backend.api.roster import get_my_roster
from backend.api.mlb_live import get_transactions
from backend.api.waivers import get_free_agents

logger = logging.getLogger(__name__)

_cache: list[dict] = []
_cache_ts: float = 0
CACHE_TTL = 120  # 2 minutes — alerts need freshness

IL_STATUSES = {"IL10", "IL60", "IL15"}
ACTIVE_POSITIONS = {
    "C", "1B", "2B", "3B", "SS", "OF", "CI", "MI", "Util",
    "SP", "RP", "P",
}

# Thresholds for "elite pickup" detection
ELITE_HITTER_OBP = 0.340
ELITE_HITTER_SB = 5
ELITE_PITCHER_K = 12
ELITE_PITCHER_SH = 4


def _normalize(name: str) -> str:
    return name.strip().lower()


def _check_injured_starters(roster: list[dict]) -> list[dict]:
    """Flag active-slot players with IL or DTD status."""
    alerts = []
    for p in roster:
        pos = p.get("position", "")
        status = p.get("status", "")
        name = p.get("name", "")

        if not status:
            continue

        if pos not in ACTIVE_POSITIONS and pos != "DL":
            continue

        if status in IL_STATUSES:
            if pos == "DL":
                continue
            alerts.append({
                "severity": "critical",
                "type": "injury",
                "headline": f"{name} is on the {status}",
                "detail": (
                    f"{name} ({pos}) is on the injured list. "
                    f"Move to DL slot and find a replacement."
                ),
                "player": name,
                "action": "Replace",
            })
        elif status == "DTD" and pos in ACTIVE_POSITIONS:
            alerts.append({
                "severity": "warning",
                "type": "injury",
                "headline": f"{name} is day-to-day",
                "detail": (
                    f"{name} ({pos}) is DTD — monitor pregame lineups. "
                    f"Have a bench replacement ready."
                ),
                "player": name,
                "action": "Monitor",
            })

    return alerts


def _check_roster_transactions(
    roster_names: set[str],
    transactions: list[dict],
) -> list[dict]:
    """Flag transactions that hit roster players (DFA, trade, IL placement)."""
    alerts = []
    critical_types = {"trade", "dfa", "released", "designated for assignment"}

    for txn in transactions:
        player_lower = _normalize(txn.get("player", ""))
        if player_lower not in roster_names:
            continue

        txn_type = txn.get("type", "").lower()
        desc = txn.get("description", "")

        if any(ct in txn_type for ct in critical_types):
            alerts.append({
                "severity": "critical",
                "type": "transaction",
                "headline": f"{txn['player']} — {txn['type']}",
                "detail": desc[:200],
                "player": txn["player"],
                "action": "Evaluate",
            })
        elif "disabled" in txn_type or "injured" in txn_type:
            alerts.append({
                "severity": "critical",
                "type": "injury",
                "headline": f"{txn['player']} placed on IL",
                "detail": desc[:200],
                "player": txn["player"],
                "action": "Replace",
            })

    return alerts


def _check_elite_pickups(free_agents: list[dict]) -> list[dict]:
    """Flag elite-caliber players sitting on the waiver wire."""
    alerts = []
    for fa in free_agents:
        status = fa.get("status", "")
        if status in IL_STATUSES:
            continue

        name = fa.get("name", "")
        stats = fa.get("projected_stats", {})
        reasons = []

        obp = stats.get("OBP", 0)
        sb = stats.get("SB", 0)
        k = stats.get("K", 0)
        sh = stats.get("SH", 0)

        if obp >= ELITE_HITTER_OBP and sb >= ELITE_HITTER_SB:
            reasons.append(f".{int(obp*1000)} OBP + {sb} SB")
        if k >= ELITE_PITCHER_K:
            reasons.append(f"{k} K projected")
        if sh >= ELITE_PITCHER_SH:
            reasons.append(f"{sh} S+H projected")

        if reasons:
            pos = fa.get("position", "")
            alerts.append({
                "severity": "warning",
                "type": "pickup",
                "headline": f"{name} available on waivers",
                "detail": (
                    f"{name} ({pos}) is a free agent with elite upside: "
                    f"{', '.join(reasons)}. Grab before opponents notice."
                ),
                "player": name,
                "action": "Claim",
            })

    return alerts


async def get_critical_alerts() -> list[dict]:
    """Return only mission-critical alerts. Cached 2 min."""
    global _cache, _cache_ts

    if _cache and (time.time() - _cache_ts) < CACHE_TTL:
        return _cache

    roster_data, fa_data = await asyncio.gather(
        get_my_roster(),
        get_free_agents(),
        return_exceptions=True,
    )

    if isinstance(roster_data, Exception):
        logger.warning("Roster fetch failed for alerts: %s", roster_data)
        roster_data = {}
    if isinstance(fa_data, Exception):
        logger.warning("FA fetch failed for alerts: %s", fa_data)
        fa_data = {}

    roster = roster_data.get("roster", [])
    roster_names = {_normalize(p["name"]) for p in roster if p.get("name")}
    free_agents = fa_data.get("free_agents", [])

    try:
        transactions = await get_transactions(days=2)
    except Exception:
        transactions = []

    alerts: list[dict] = []
    alerts.extend(_check_injured_starters(roster))
    alerts.extend(_check_roster_transactions(roster_names, transactions))
    alerts.extend(_check_elite_pickups(free_agents))

    seen = set()
    deduped = []
    for a in alerts:
        key = (a["type"], _normalize(a.get("player", "")))
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    deduped.sort(key=lambda x: 0 if x["severity"] == "critical" else 1)

    _cache = deduped
    _cache_ts = time.time()
    return _cache
