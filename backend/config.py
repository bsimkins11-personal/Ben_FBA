import os

USE_SYNTHETIC_DATA = os.getenv("USE_SYNTHETIC_DATA", "true").lower() == "true"

LLM_MODEL = "claude-haiku-4-5-20251001"
LLM_MAX_TOKENS = 1200
SYSTEM_PROMPT_TOKEN_BUDGET = 2000

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
YAHOO_CLIENT_ID = os.getenv("YAHOO_CLIENT_ID", "")
YAHOO_CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET", "")
YAHOO_REDIRECT_URI = os.getenv(
    "YAHOO_REDIRECT_URI",
    "https://benfba-production.up.railway.app/auth/yahoo/callback",
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://benfba.vercel.app")

YAHOO_STAT_IDS = {
    "OBP": 13,
    "R": 7,
    "TB": 310,
    "RBI": 12,
    "SB": 16,
    "QS": 50,
    "SH": 57,
    "K": 48,
    "ERA": 26,
    "WHIP": 27,
}

ROSTER_FIELDS = ["name", "position", "eligible_positions", "status", "stats"]
FA_FIELDS = ["name", "position", "status", "ownership", "projected_stats"]
STANDINGS_FIELDS = ["category", "my_rank", "league_avg", "gap_to_next"]

TRIMMER_MAX_TOKENS = 800
