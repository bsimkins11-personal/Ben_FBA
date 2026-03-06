"""PostgreSQL connection pool and schema initialization.

Uses asyncpg for async Postgres access. Single table for now:
  - yahoo_tokens: persists OAuth tokens across Railway redeploys
"""

from __future__ import annotations

import logging

import asyncpg

from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS yahoo_tokens (
    id          INTEGER PRIMARY KEY DEFAULT 1,
    access_token  TEXT NOT NULL DEFAULT '',
    refresh_token TEXT NOT NULL DEFAULT '',
    expires_at    DOUBLE PRECISION NOT NULL DEFAULT 0,
    league_key    TEXT NOT NULL DEFAULT '',
    team_key      TEXT NOT NULL DEFAULT '',
    updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT single_row CHECK (id = 1)
);

INSERT INTO yahoo_tokens (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;
"""


async def get_pool() -> asyncpg.Pool | None:
    global _pool
    if _pool is not None:
        return _pool

    if not DATABASE_URL:
        logger.info("DATABASE_URL not set — Postgres disabled")
        return None

    try:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
        async with _pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
        logger.info("Postgres pool initialized, schema ready")
        return _pool
    except Exception as exc:
        logger.error("Postgres connection failed: %s", exc)
        return None


async def save_tokens(
    access_token: str,
    refresh_token: str,
    expires_at: float,
    league_key: str = "",
    team_key: str = "",
) -> None:
    pool = await get_pool()
    if not pool:
        return

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE yahoo_tokens SET
                access_token = $1,
                refresh_token = $2,
                expires_at = $3,
                league_key = $4,
                team_key = $5,
                updated_at = NOW()
            WHERE id = 1
            """,
            access_token,
            refresh_token,
            expires_at,
            league_key,
            team_key,
        )
    logger.info("Tokens persisted to Postgres")


async def load_tokens() -> dict | None:
    pool = await get_pool()
    if not pool:
        return None

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT access_token, refresh_token, expires_at, league_key, team_key "
            "FROM yahoo_tokens WHERE id = 1"
        )

    if not row or not row["access_token"]:
        return None

    return {
        "access_token": row["access_token"],
        "refresh_token": row["refresh_token"],
        "expires_at": row["expires_at"],
        "league_key": row["league_key"],
        "team_key": row["team_key"],
    }


async def clear_tokens() -> None:
    pool = await get_pool()
    if not pool:
        return

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE yahoo_tokens SET
                access_token = '',
                refresh_token = '',
                expires_at = 0,
                league_key = '',
                team_key = '',
                updated_at = NOW()
            WHERE id = 1
            """
        )
    logger.info("Tokens cleared from Postgres")
