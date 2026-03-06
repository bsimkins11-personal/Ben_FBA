"use client";

import { useEffect, useState } from "react";
import {
  api,
  type MatchupAdvisorData,
  type MatchupGameGroup,
  type MatchupPlayerAdvice,
  type CategoryAnalysis,
} from "@/lib/api";

const VERDICT_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; icon: string }
> = {
  confirmed: {
    label: "Locked In",
    color: "text-green-800",
    bg: "bg-green-50 border-green-200",
    icon: "✓",
  },
  start: {
    label: "Start",
    color: "text-green-700",
    bg: "bg-green-50/60 border-green-200",
    icon: "▶",
  },
  caution: {
    label: "Caution",
    color: "text-amber-700",
    bg: "bg-amber-50 border-amber-200",
    icon: "⚠",
  },
  monitor: {
    label: "Monitor",
    color: "text-amber-600",
    bg: "bg-amber-50/60 border-amber-200",
    icon: "👁",
  },
  consider: {
    label: "Consider",
    color: "text-blue-700",
    bg: "bg-blue-50 border-blue-200",
    icon: "↑",
  },
  bench: {
    label: "Bench",
    color: "text-gray-500",
    bg: "bg-gray-50 border-gray-200",
    icon: "—",
  },
  out: {
    label: "Out",
    color: "text-red-600",
    bg: "bg-red-50 border-red-200",
    icon: "✕",
  },
  no_game: {
    label: "Off Day",
    color: "text-gray-400",
    bg: "bg-gray-50/50 border-gray-100",
    icon: "○",
  },
  not_starting: {
    label: "Not Starting",
    color: "text-gray-400",
    bg: "bg-gray-50/50 border-gray-100",
    icon: "○",
  },
};

function ScoreBadge({ score }: { score: { winning: number; losing: number } }) {
  const winning = score.winning >= 6;
  const close = Math.abs(score.winning - score.losing) <= 2;
  return (
    <span
      className={`text-sm font-black px-2.5 py-1 rounded-full ${
        winning
          ? "bg-green-100 text-green-800"
          : close
          ? "bg-amber-100 text-amber-800"
          : "bg-red-100 text-red-800"
      }`}
    >
      {score.winning}-{score.losing}
    </span>
  );
}

function CategoryBar({ cat }: { cat: CategoryAnalysis }) {
  const statusColor =
    cat.status === "winning"
      ? "text-green-700 bg-green-50"
      : cat.status === "losing"
      ? "text-red-600 bg-red-50"
      : "text-gray-600 bg-gray-50";
  const flipBadge = cat.flippable && cat.status === "losing";

  return (
    <div
      className={`flex items-center justify-between px-2 py-1 rounded text-[11px] ${statusColor}`}
    >
      <span className="font-bold w-8">{cat.category}</span>
      <span className="tabular-nums">
        {typeof cat.my_value === "number" && cat.my_value < 1
          ? cat.my_value.toFixed(3)
          : cat.my_value}
      </span>
      <span className="text-[10px] text-gray-400">vs</span>
      <span className="tabular-nums">
        {typeof cat.opp_value === "number" && cat.opp_value < 1
          ? cat.opp_value.toFixed(3)
          : cat.opp_value}
      </span>
      {flipBadge && (
        <span className="text-[9px] font-bold text-amber-700 bg-amber-100 px-1 rounded">
          FLIP
        </span>
      )}
    </div>
  );
}

function PlayerCard({ player }: { player: MatchupPlayerAdvice }) {
  const cfg = VERDICT_CONFIG[player.verdict] || VERDICT_CONFIG.bench;
  return (
    <div className={`p-2.5 rounded border ${cfg.bg}`}>
      <div className="flex items-start gap-2">
        <span className="text-base mt-0.5 flex-shrink-0 w-5 text-center">
          {cfg.icon}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[13px] font-semibold">{player.name}</span>
            <span className="text-[10px] text-muted font-medium">
              {player.position} · {player.mlb_team}
            </span>
            {player.status && (
              <span
                className={`text-[9px] font-bold px-1 py-0.5 rounded ${
                  player.status.startsWith("IL")
                    ? "bg-red-600 text-white"
                    : "bg-amber-500 text-white"
                }`}
              >
                {player.status}
              </span>
            )}
            <span className={`text-[10px] font-bold uppercase ${cfg.color}`}>
              {cfg.label}
            </span>
          </div>
          <p className="text-[11px] text-gray-600 mt-1 leading-snug">
            {player.rationale}
          </p>
          {player.impact.length > 0 && (
            <div className="flex gap-1 mt-1.5">
              {player.impact.map((cat) => (
                <span
                  key={cat}
                  className="text-[9px] font-bold bg-navy/10 text-navy px-1.5 py-0.5 rounded"
                >
                  {cat}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function GameCard({ game }: { game: MatchupGameGroup }) {
  const hasBothSides = game.my_players.length > 0 && game.opp_players.length > 0;
  const hasAction = game.my_players.some(
    (p) => !["confirmed", "bench", "no_game", "not_starting"].includes(p.verdict)
  );

  return (
    <div className="bg-white rounded-lg border border-border overflow-hidden">
      {/* Game Header */}
      <div
        className={`px-3 py-2 flex items-center justify-between ${
          hasBothSides ? "bg-navy-dark" : "bg-gray-700"
        }`}
      >
        <div className="flex items-center gap-2">
          <span className="text-white text-xs font-bold">
            {game.game_label}
          </span>
          {hasBothSides && (
            <span className="text-[9px] font-bold bg-amber-400 text-navy px-1.5 py-0.5 rounded">
              HEAD TO HEAD
            </span>
          )}
          {hasAction && (
            <span className="text-[9px] font-bold bg-mlb-red text-white px-1.5 py-0.5 rounded">
              ACTION
            </span>
          )}
        </div>
        {game.venue && (
          <span className="text-white/40 text-[10px]">{game.venue}</span>
        )}
      </div>

      {/* Probable Pitchers */}
      {(game.away_pitcher || game.home_pitcher) &&
        game.away_pitcher !== "TBD" && (
          <div className="px-3 py-1.5 bg-surface/50 border-b border-border text-[10px] text-muted">
            <span className="font-medium">Probable:</span>{" "}
            {game.away_pitcher} vs {game.home_pitcher}
          </div>
        )}

      <div className="p-2 space-y-1.5">
        {/* Ben's players */}
        {game.my_players.map((p) => (
          <PlayerCard key={p.name} player={p} />
        ))}

        {/* Opponent's players */}
        {game.opp_players.length > 0 && (
          <div className="mt-1 pt-1 border-t border-dashed border-gray-200">
            <span className="text-[10px] font-bold text-muted uppercase tracking-wider px-1">
              Opponent
            </span>
            {game.opp_players.map((p) => (
              <div
                key={p.name}
                className="flex items-center gap-2 px-2 py-1 text-[11px] text-gray-500"
              >
                <span className="w-5 text-center text-[10px]">👤</span>
                <span className="font-medium">{p.name}</span>
                <span className="text-[10px]">
                  {p.position} · {p.mlb_team}
                </span>
                {p.status && (
                  <span
                    className={`text-[9px] font-bold px-1 py-0.5 rounded ${
                      p.status.startsWith("IL")
                        ? "bg-red-100 text-red-600"
                        : "bg-amber-100 text-amber-600"
                    }`}
                  >
                    {p.status}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MatchupAdvisorPanel() {
  const [data, setData] = useState<MatchupAdvisorData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .matchupAdvisor()
      .then(setData)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted">
        Unable to load matchup advisor
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted">
        Analyzing matchup...
      </div>
    );
  }

  const actionGames = data.games.filter((g) =>
    g.my_players.some(
      (p) => !["confirmed", "bench", "no_game", "not_starting"].includes(p.verdict)
    )
  );
  const steadyGames = data.games.filter(
    (g) => !actionGames.includes(g) && g.my_players.length > 0
  );
  const oppOnlyGames = data.games.filter(
    (g) => g.my_players.length === 0 && g.opp_players.length > 0
  );

  const hittingCats = data.category_analysis.filter((c) =>
    ["OBP", "R", "TB", "RBI", "SB"].includes(c.category)
  );
  const pitchingCats = data.category_analysis.filter((c) =>
    ["QS", "SH", "K", "ERA", "WHIP"].includes(c.category)
  );

  return (
    <div className="space-y-3">
      {/* Scoreboard + Summary */}
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <div className="bg-navy px-3 py-2 flex items-center justify-between">
          <span className="text-white text-xs font-bold uppercase tracking-wider">
            Week {data.week} Matchup Advisor
          </span>
          <ScoreBadge score={data.score} />
        </div>
        <div className="px-3 py-2 border-b border-border">
          <div className="flex items-center justify-between text-[12px] font-semibold">
            <span>{data.my_team}</span>
            <span className="text-muted text-[10px]">vs</span>
            <span>{data.opponent}</span>
          </div>
        </div>
        <div className="px-3 py-2 text-[12px] text-gray-700 bg-surface/30">
          {data.summary}
        </div>

        {/* Category Scoreboard */}
        <div className="grid grid-cols-2 gap-px bg-border">
          <div className="bg-white p-2 space-y-0.5">
            {hittingCats.map((c) => (
              <CategoryBar key={c.category} cat={c} />
            ))}
          </div>
          <div className="bg-white p-2 space-y-0.5">
            {pitchingCats.map((c) => (
              <CategoryBar key={c.category} cat={c} />
            ))}
          </div>
        </div>
      </div>

      {/* Action Required */}
      {actionGames.length > 0 && (
        <div className="space-y-2">
          <div className="text-[11px] font-bold uppercase tracking-wider text-mlb-red px-1">
            Action Required
          </div>
          {actionGames.map((g, i) => (
            <GameCard key={i} game={g} />
          ))}
        </div>
      )}

      {/* Lineup Confirmed */}
      {steadyGames.length > 0 && (
        <div className="space-y-2">
          <div className="text-[11px] font-bold uppercase tracking-wider text-green-700 px-1">
            Lineup Confirmed
          </div>
          {steadyGames.map((g, i) => (
            <GameCard key={i} game={g} />
          ))}
        </div>
      )}

      {/* Opponent Activity */}
      {oppOnlyGames.length > 0 && (
        <div className="space-y-2">
          <div className="text-[11px] font-bold uppercase tracking-wider text-muted px-1">
            Opponent Activity
          </div>
          {oppOnlyGames.map((g, i) => (
            <GameCard key={i} game={g} />
          ))}
        </div>
      )}
    </div>
  );
}
