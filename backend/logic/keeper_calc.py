"""Bush League keeper cost calculator (Rules 6.2, 6.3, 6.9)."""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Default Yahoo-style rankings for synthetic / offline testing.
# Maps player name → overall rank (1-300).
# ---------------------------------------------------------------------------
DEFAULT_RANKINGS: dict[str, int] = {
    "Shohei Ohtani": 1, "Mookie Betts": 2, "Ronald Acuna Jr.": 3,
    "Trea Turner": 4, "Freddie Freeman": 5, "Aaron Judge": 6,
    "Juan Soto": 7, "Corey Seager": 8, "Julio Rodriguez": 9,
    "Corbin Carroll": 10, "Mike Trout": 11, "Bobby Witt Jr.": 12,
    "Marcus Semien": 13, "Fernando Tatis Jr.": 14, "Rafael Devers": 15,
    "Yordan Alvarez": 16, "Matt Olson": 17, "Kyle Tucker": 18,
    "Bo Bichette": 19, "Spencer Strider": 20, "Gerrit Cole": 21,
    "Zack Wheeler": 22, "Max Scherzer": 23, "Corbin Burnes": 24,
    "Shane McClanahan": 25, "Luis Castillo": 26, "Framber Valdez": 27,
    "Kevin Gausman": 28, "Blake Snell": 29, "Yu Darvish": 30,
    "Adolis Garcia": 31, "Elly De La Cruz": 32, "Gunnar Henderson": 33,
    "CJ Abrams": 34, "Jackson Chourio": 35, "Bryce Harper": 36,
    "Pete Alonso": 37, "Vladimir Guerrero Jr.": 38, "Jose Ramirez": 39,
    "Wander Franco": 40, "Ozzie Albies": 41, "Dansby Swanson": 42,
    "Alex Bregman": 43, "Lars Nootbaar": 44, "Cedric Mullins": 45,
    "Byron Buxton": 46, "Tyler Glasnow": 47, "Logan Webb": 48,
    "Yoshinobu Yamamoto": 49, "Paul Skenes": 50,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    return name.strip().lower()


def _find_in_draft(player_name: str, draft_history: list[dict]) -> dict | None:
    """Return the earliest draft entry for *player_name*, or ``None``."""
    target = _normalize_name(player_name)
    for entry in draft_history:
        if _normalize_name(entry.get("player", "")) == target:
            return entry
    return None


def _was_kept_previously(player_name: str, draft_history: list[dict]) -> bool:
    """Return ``True`` if *player_name* was ever kept by *any* team."""
    target = _normalize_name(player_name)
    return any(
        _normalize_name(e.get("player", "")) == target and e.get("kept", False)
        for e in draft_history
    )


def _yahoo_round(player_name: str,
                  yahoo_rankings: dict | None,
                  teams_in_league: int) -> int:
    """Derive a draft round from the Yahoo Top-300 ranking."""
    rankings = yahoo_rankings or DEFAULT_RANKINGS
    rank = rankings.get(player_name)
    if rank is None:
        for k, v in rankings.items():
            if _normalize_name(k) == _normalize_name(player_name):
                rank = v
                break
    if rank is None:
        return 20  # not ranked → treat as 20th-round value
    return max(1, math.ceil(rank / teams_in_league))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_keeper_cost(
    player_name: str,
    draft_history: list[dict],
    yahoo_rankings: dict | None = None,
    teams_in_league: int = 12,
) -> dict:
    """Determine the keeper round cost for a single player.

    Rules (Bush League constitution)
    --------------------------------
    - **6.9** Never drafted → 20th round (undrafted baseline).
    - **6.3** Previously kept by *any* team → Yahoo Top-300 ranking
      converted to round via ``ceil(rank / teams_in_league)``.
    - **6.2** Drafted but never kept → original draft round.
    """
    draft_entry = _find_in_draft(player_name, draft_history)

    if draft_entry is None:
        return {
            "player": player_name,
            "round_cost": 20,
            "notes": "Rule 6.9 — never drafted; 20th-round cost",
        }

    if _was_kept_previously(player_name, draft_history):
        rd = _yahoo_round(player_name, yahoo_rankings, teams_in_league)
        return {
            "player": player_name,
            "round_cost": rd,
            "notes": (
                f"Rule 6.3 — previously kept; Yahoo rank → round {rd}"
            ),
        }

    original_round = draft_entry.get("round", 20)
    return {
        "player": player_name,
        "round_cost": original_round,
        "notes": f"Rule 6.2 — drafted round {original_round}; never kept",
    }


def apply_undrafted_penalties(keepers: list[dict]) -> list[dict]:
    """Rule 6.9 escalation for multiple undrafted keepers.

    First undrafted keeper = round 20, second = 18, third = 16, etc.
    Each additional undrafted keeper costs 2 rounds earlier.
    """
    undrafted_idx: list[int] = []
    for i, k in enumerate(keepers):
        if k.get("round_cost") == 20 and "6.9" in k.get("notes", ""):
            undrafted_idx.append(i)

    for seq, idx in enumerate(undrafted_idx):
        new_round = 20 - (seq * 2)
        new_round = max(1, new_round)
        keepers[idx] = {
            **keepers[idx],
            "round_cost": new_round,
            "notes": keepers[idx]["notes"]
            + (
                f" | undrafted keeper #{seq + 1} → round {new_round}"
                if seq > 0
                else ""
            ),
        }
    return keepers


def resolve_collisions(
    keepers: list[dict], teams_in_league: int = 12
) -> list[dict]:
    """Resolve round collisions among keepers.

    Rounds 1-3: hard escalation 3 → 2 → 1.  If round 1 is already
    occupied the player **cannot be kept** (flagged in notes).

    Round 4+: the bumped player uses the pick 2 rounds earlier.
    """
    max_rounds = 20
    occupied: set[int] = set()
    result: list[dict] = []

    sorted_keepers = sorted(keepers, key=lambda k: k["round_cost"])

    for keeper in sorted_keepers:
        rd = keeper["round_cost"]
        collision_note = ""

        while rd in occupied:
            if rd <= 3:
                new_rd = rd - 1
                if new_rd < 1:
                    collision_note = (
                        f"Collision at round {keeper['round_cost']}; "
                        "no earlier round available — cannot keep"
                    )
                    rd = -1
                    break
                collision_note = (
                    f"Rounds 1-3 escalation: {rd} → {new_rd}"
                )
                rd = new_rd
            else:
                new_rd = max(1, rd - 2)
                collision_note = (
                    f"Round {keeper['round_cost']} occupied; "
                    f"bumped to round {new_rd}"
                )
                rd = new_rd

        entry = {**keeper, "round_cost": max(rd, 1)}
        if collision_note:
            entry["collision_note"] = collision_note
        if rd == -1:
            entry["round_cost"] = keeper["round_cost"]
            entry["collision_note"] = collision_note

        occupied.add(entry["round_cost"])
        result.append(entry)

    return result


def calculate_team_keepers(
    roster: list[dict],
    draft_history: list[dict],
    yahoo_rankings: dict | None = None,
    teams_in_league: int = 12,
    max_keepers: int = 8,
) -> list[dict]:
    """Calculate keeper costs for every player on a roster.

    Returns at most *max_keepers* entries sorted by best value.
    ``value_score = 20 - round_cost`` (higher = better deal).
    """
    costed: list[dict] = []
    for player in roster:
        name = player.get("player") or player.get("name", "")
        if not name:
            continue
        entry = calculate_keeper_cost(
            name, draft_history, yahoo_rankings, teams_in_league
        )
        entry["value_score"] = float(20 - entry["round_cost"])
        costed.append(entry)

    costed.sort(key=lambda k: -k["value_score"])

    keepers = costed[:max_keepers]
    keepers = apply_undrafted_penalties(keepers)
    keepers = resolve_collisions(keepers, teams_in_league)

    return keepers
