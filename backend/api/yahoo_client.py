import httpx

from backend.config import YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET  # noqa: F401

YAHOO_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"


class YahooClient:
    """Read-only async wrapper around the Yahoo Fantasy Sports API.

    All methods raise ``NotImplementedError`` until Yahoo OAuth is wired
    in Phase 4.  URL construction for each endpoint is already in place.
    """

    def __init__(self, access_token: str = "") -> None:
        self.access_token = access_token
        self.client = httpx.AsyncClient(
            base_url=YAHOO_BASE,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

    def _not_configured(self) -> None:
        raise NotImplementedError(
            "Yahoo OAuth not configured — use synthetic data"
        )

    # GET /fantasy/v2/league/{league_key}/settings
    async def get_league(self, league_key: str) -> dict:
        """Fetch league metadata and scoring settings."""
        _url = f"/league/{league_key}/settings"  # noqa: F841
        self._not_configured()
        return {}

    # GET /fantasy/v2/league/{league_key}/standings
    async def get_standings(self, league_key: str) -> dict:
        """Fetch current league standings."""
        _url = f"/league/{league_key}/standings"  # noqa: F841
        self._not_configured()
        return {}

    # GET /fantasy/v2/league/{league_key}/scoreboard;week={week}
    async def get_scoreboard(
        self, league_key: str, week: int | None = None
    ) -> dict:
        """Fetch the weekly scoreboard (matchup results)."""
        week_param = f";week={week}" if week else ""
        _url = f"/league/{league_key}/scoreboard{week_param}"  # noqa: F841
        self._not_configured()
        return {}

    # GET /fantasy/v2/team/{team_key}/roster;week={week}
    async def get_roster(
        self, team_key: str, week: int | None = None
    ) -> dict:
        """Fetch a team's roster for a given week."""
        week_param = f";week={week}" if week else ""
        _url = f"/team/{team_key}/roster{week_param}"  # noqa: F841
        self._not_configured()
        return {}

    # GET /fantasy/v2/team/{team_key}/stats;type=week;week={week}
    async def get_team_stats(
        self, team_key: str, week: int | None = None
    ) -> dict:
        """Fetch a team's aggregated stats."""
        week_param = f";type=week;week={week}" if week else ""
        _url = f"/team/{team_key}/stats{week_param}"  # noqa: F841
        self._not_configured()
        return {}

    # GET /fantasy/v2/league/{league_key}/players;status=FA;position={pos};sort={stat}
    async def get_free_agents(
        self,
        league_key: str,
        position: str | None = None,
        sort_stat: str | None = None,
    ) -> dict:
        """List available free agents with optional position/sort filters."""
        params = ";status=FA"
        if position:
            params += f";position={position}"
        if sort_stat:
            params += f";sort={sort_stat}"
        _url = f"/league/{league_key}/players{params}"  # noqa: F841
        self._not_configured()
        return {}

    # GET /fantasy/v2/player/{player_key}/stats;type=week;week={week}
    async def get_player_stats(
        self, player_key: str, week: int | None = None
    ) -> dict:
        """Fetch individual player stats."""
        week_param = f";type=week;week={week}" if week else ""
        _url = f"/player/{player_key}/stats{week_param}"  # noqa: F841
        self._not_configured()
        return {}

    # GET /fantasy/v2/league/{league_key}/draftresults
    async def get_draft_results(self, league_key: str) -> dict:
        """Fetch draft results for the league."""
        _url = f"/league/{league_key}/draftresults"  # noqa: F841
        self._not_configured()
        return {}

    # GET /fantasy/v2/league/{league_key}/players;player_keys={player_key}/ownership
    async def check_ownership(
        self, league_key: str, player_key: str
    ) -> dict:
        """Check roster ownership status for a specific player."""
        _url = f"/league/{league_key}/players;player_keys={player_key}/ownership"  # noqa: F841
        self._not_configured()
        return {}
