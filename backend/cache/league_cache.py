import json
import logging
from pathlib import Path

from backend.config import USE_SYNTHETIC_DATA

logger = logging.getLogger(__name__)

SYNTHETIC_DIR = Path(__file__).resolve().parent.parent / "synthetic"

_FILE_MAP: dict[str, str] = {
    "league_config": "league_config.json",
    "standings": "standings.json",
    "roster": "my_roster.json",
    "free_agents": "free_agents.json",
    "draft_history": "draft_history.json",
    "matchup": "current_matchup.json",
}


class LeagueCache:
    """Singleton in-memory cache backed by synthetic JSON files on disk."""

    _instance: "LeagueCache | None" = None

    def __new__(cls) -> "LeagueCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
            cls._instance._data: dict[str, dict] = {}
        return cls._instance

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load_synthetic()

    def _load_synthetic(self) -> None:
        """Load all 6 synthetic JSON files into memory."""
        if not USE_SYNTHETIC_DATA:
            logger.info("Synthetic data disabled — skipping cache load")
            return

        if not SYNTHETIC_DIR.is_dir():
            logger.warning("Synthetic directory not found: %s", SYNTHETIC_DIR)
            self._loaded = True
            return

        for key, filename in _FILE_MAP.items():
            path = SYNTHETIC_DIR / filename
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    self._data[key] = json.load(f)
                logger.info("Loaded %s (%d bytes)", filename, path.stat().st_size)
            else:
                logger.warning("Missing synthetic file: %s", path)
                self._data[key] = {}

        self._loaded = True

    def get_league_config(self) -> dict:
        self._ensure_loaded()
        return self._data.get("league_config", {})

    def get_standings(self) -> dict:
        self._ensure_loaded()
        return self._data.get("standings", {})

    def get_roster(self) -> dict:
        self._ensure_loaded()
        return self._data.get("roster", {})

    def get_free_agents(self) -> dict:
        self._ensure_loaded()
        return self._data.get("free_agents", {})

    def get_draft_history(self) -> dict:
        self._ensure_loaded()
        return self._data.get("draft_history", {})

    def get_matchup(self) -> dict:
        self._ensure_loaded()
        return self._data.get("matchup", {})

    def reload(self) -> None:
        """Force-reload synthetic data from disk."""
        self._loaded = False
        self._data.clear()
        self._load_synthetic()
