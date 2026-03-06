"use client";

import { useEffect, useState } from "react";
import {
  api,
  type MatchupAdvisorData,
  type MatchupGameGroup,
  type MatchupPlayerAdvice,
  type CategoryAnalysis,
  type CriticalAlert,
  type NewsData,
  type NewsItem,
} from "@/lib/api";

/* ── Helpers ─────────────────────────────────────────────────── */

const ACTION_VERDICTS = new Set([
  "caution",
  "monitor",
  "consider",
  "out",
  "start",
]);
const QUIET_VERDICTS = new Set([
  "confirmed",
  "bench",
  "no_game",
  "not_starting",
]);

function fmtStat(val: number): string {
  return val < 1 && val > 0 ? val.toFixed(3) : String(val);
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ZONE 1 — SCOREBOARD
   Where you stand at a glance.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function Scoreboard({
  data,
  hittingCats,
  pitchingCats,
  lastUpdate,
  onRefresh,
}: {
  data: MatchupAdvisorData;
  hittingCats: CategoryAnalysis[];
  pitchingCats: CategoryAnalysis[];
  lastUpdate: Date | null;
  onRefresh: () => void;
}) {
  const { score } = data;
  const up = score.winning > score.losing;
  const even = score.winning === score.losing;
  const scoreBg = up
    ? "bg-green-600"
    : even
    ? "bg-amber-500"
    : "bg-red-600";

  return (
    <div className="bg-white rounded-lg border border-border overflow-hidden">
      <div className="bg-navy-dark px-4 py-2.5 flex items-center justify-between">
        <div>
          <div className="text-white/50 text-[10px] font-semibold uppercase tracking-widest">
            Week {data.week} · H2H Categories
          </div>
          <div className="text-white text-sm font-bold mt-0.5">
            {data.my_team}
            <span className="text-white/30 mx-2 font-normal">vs</span>
            {data.opponent}
          </div>
        </div>
        <div
          className={`${scoreBg} text-white text-lg font-black px-3 py-1 rounded-md tabular-nums`}
        >
          {score.winning}–{score.losing}
        </div>
      </div>

      <div className="px-4 py-2 bg-surface/60 border-b border-border flex items-start justify-between gap-3">
        <span className="text-[12px] text-gray-600 leading-snug">
          {data.summary}
        </span>
        <div className="flex items-center gap-2 flex-shrink-0">
          {lastUpdate && (
            <span className="text-[9px] text-gray-400 tabular-nums">
              {lastUpdate.toLocaleTimeString([], {
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
          )}
          <button
            onClick={onRefresh}
            className="text-[9px] text-navy/60 hover:text-navy font-semibold uppercase tracking-wider transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-10 text-center text-[10px]">
        {[...hittingCats, ...pitchingCats].map((c) => (
          <div
            key={c.category}
            className="border-r border-border last:border-r-0"
          >
            <div className="py-1 bg-gray-50 font-bold text-gray-500 border-b border-border">
              {c.category}
            </div>
            <div
              className={`py-1.5 font-bold tabular-nums ${
                c.status === "winning"
                  ? "text-green-700 bg-green-50/50"
                  : c.status === "losing"
                  ? "text-red-600 bg-red-50/50"
                  : "text-gray-500"
              }`}
            >
              {fmtStat(c.my_value)}
            </div>
            <div className="py-1 text-gray-400 tabular-nums border-t border-border">
              {fmtStat(c.opp_value)}
            </div>
            {c.flippable && c.status === "losing" && (
              <div className="pb-1">
                <span className="text-[8px] font-bold text-amber-600 bg-amber-50 px-1 rounded">
                  FLIP
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ZONE 2 — ACTION ITEMS
   Roster decisions that need your attention right now.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function ActionCard({
  player,
}: {
  player: MatchupPlayerAdvice & { game_label?: string };
}) {
  const isCritical = player.verdict === "out" || player.verdict === "caution";
  const borderColor = isCritical ? "border-l-red-500" : "border-l-amber-400";
  const actionLabel =
    player.verdict === "out"
      ? "Replace"
      : player.verdict === "caution"
      ? "Review"
      : player.verdict === "monitor"
      ? "Watch"
      : player.verdict === "consider"
      ? "Activate"
      : "Decide";

  const actionColor =
    player.verdict === "out"
      ? "text-red-600 border-red-200 bg-red-50"
      : player.verdict === "caution"
      ? "text-amber-700 border-amber-200 bg-amber-50"
      : "text-blue-700 border-blue-200 bg-blue-50";

  return (
    <div
      className={`bg-white rounded-md border border-border border-l-[3px] ${borderColor} p-3`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[13px] font-bold">{player.name}</span>
            <span className="text-[10px] text-muted">
              {player.position} · {player.mlb_team}
            </span>
            {player.status && (
              <span
                className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                  player.status.startsWith("IL")
                    ? "bg-red-100 text-red-700"
                    : "bg-amber-100 text-amber-700"
                }`}
              >
                {player.status}
              </span>
            )}
          </div>
          <p className="text-[11px] text-gray-500 mt-1 leading-snug">
            {player.rationale}
          </p>
          {player.impact.length > 0 && (
            <div className="flex gap-1 mt-1.5">
              {player.impact.map((cat) => (
                <span
                  key={cat}
                  className="text-[9px] font-semibold bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
                >
                  {cat}
                </span>
              ))}
            </div>
          )}
        </div>
        <span
          className={`text-[10px] font-bold px-2 py-1 rounded border flex-shrink-0 ${actionColor}`}
        >
          {actionLabel}
        </span>
      </div>
      {player.game_label && (
        <div className="text-[10px] text-muted mt-1.5">{player.game_label}</div>
      )}
    </div>
  );
}

function ActionItems({ data }: { data: MatchupAdvisorData }) {
  const actionItems: (MatchupPlayerAdvice & { game_label?: string })[] = [];

  for (const game of data.games) {
    for (const p of game.my_players) {
      if (ACTION_VERDICTS.has(p.verdict)) {
        actionItems.push({ ...p, game_label: game.game_label });
      }
    }
  }

  if (actionItems.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-[12px] text-green-800 font-medium">
        Lineup looks good — no moves needed right now.
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {actionItems.map((p) => (
        <ActionCard key={`${p.name}-${p.verdict}`} player={p} />
      ))}
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ZONE 3 — ALERTS
   IL moves, DTD starters, must-grab free agents.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function AlertCard({ alert }: { alert: CriticalAlert }) {
  const isCritical = alert.severity === "critical";
  const iconBg = isCritical ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600";
  const icon =
    alert.type === "injury" ? "+" : alert.type === "pickup" ? "↑" : "!";
  const actionColor = isCritical
    ? "text-red-600 border-red-200 bg-red-50"
    : "text-amber-700 border-amber-200 bg-amber-50";

  return (
    <div className="flex items-start gap-2.5 px-3 py-2.5 border-b border-border last:border-b-0">
      <span
        className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-black flex-shrink-0 mt-0.5 ${iconBg}`}
      >
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[12px] font-semibold text-gray-800">
          {alert.headline}
        </div>
        <div className="text-[10px] text-gray-500 mt-0.5 leading-snug line-clamp-2">
          {alert.detail}
        </div>
      </div>
      <span
        className={`text-[9px] font-bold px-1.5 py-0.5 rounded border flex-shrink-0 ${actionColor}`}
      >
        {alert.action}
      </span>
    </div>
  );
}

function AlertsModule({ alerts }: { alerts: CriticalAlert[] }) {
  if (alerts.length === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-border overflow-hidden">
      {alerts.map((a, i) => (
        <AlertCard key={`${a.type}-${a.player}-${i}`} alert={a} />
      ))}
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ZONE 4 — INTEL & NEWS
   Game monitor, MLB news, scouting notes.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

const NEWS_ICONS: Record<string, string> = {
  injury: "🏥",
  transaction: "📋",
  pitching: "⚾",
  schedule: "📅",
  callup: "🔼",
  news: "📰",
};

function NewsRow({ item }: { item: NewsItem }) {
  const icon = NEWS_ICONS[item.icon] || "📰";
  const isRoster = item.roster_tag === "my_roster";
  const isOpp = item.roster_tag === "opponent";

  return (
    <div className="flex items-start gap-2 px-3 py-2 border-b border-border last:border-b-0 hover:bg-gray-50/50">
      <span className="text-sm flex-shrink-0 mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          {isRoster && (
            <span className="text-[8px] font-bold bg-navy text-white px-1 py-0.5 rounded uppercase">
              Roster
            </span>
          )}
          {isOpp && (
            <span className="text-[8px] font-bold bg-gray-500 text-white px-1 py-0.5 rounded uppercase">
              Opp
            </span>
          )}
          <span className="text-[11px] font-semibold text-gray-800 truncate">
            {item.headline}
          </span>
        </div>
        {item.detail && item.type !== "start_today" && (
          <p className="text-[10px] text-gray-400 mt-0.5 line-clamp-1">
            {item.detail}
          </p>
        )}
      </div>
      {item.source && (
        <span className="text-[9px] text-gray-300 flex-shrink-0">
          {item.source}
        </span>
      )}
    </div>
  );
}

function GameRow({ game }: { game: MatchupGameGroup }) {
  const [open, setOpen] = useState(false);
  const hasBoth =
    game.my_players.length > 0 && game.opp_players.length > 0;
  const mine = game.my_players.filter(
    (p) => !ACTION_VERDICTS.has(p.verdict)
  );

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50/50 transition-colors text-left"
      >
        <span className="text-[9px] text-gray-300 w-3">
          {open ? "▾" : "▸"}
        </span>
        <span className="text-[11px] font-semibold text-gray-700 flex-1">
          {game.game_label}
        </span>
        {hasBoth && (
          <span className="text-[8px] font-bold text-navy/60 bg-navy/5 px-1 py-0.5 rounded">
            H2H
          </span>
        )}
        <span className="text-[10px] text-gray-400 tabular-nums">
          {mine.length} player{mine.length !== 1 ? "s" : ""}
        </span>
      </button>
      {open && (
        <div className="pb-1.5 pl-6 pr-3 space-y-0">
          {mine.map((p) => (
            <div
              key={p.name}
              className="flex items-center gap-2 py-0.5 text-[10px] text-gray-600"
            >
              <span className="w-6 text-gray-400">{p.position}</span>
              <span className="flex-1">{p.name}</span>
              <span className="text-gray-400">{p.mlb_team}</span>
              <span className="text-green-600 text-[9px]">✓</span>
            </div>
          ))}
          {game.opp_players.length > 0 && (
            <>
              <div className="text-[8px] text-gray-300 uppercase tracking-wider pt-1 pb-0.5 font-semibold">
                Opponent
              </div>
              {game.opp_players.map((p) => (
                <div
                  key={p.name}
                  className="flex items-center gap-2 py-0.5 text-[10px] text-gray-400"
                >
                  <span className="w-6">{p.position}</span>
                  <span className="flex-1">{p.name}</span>
                  <span>{p.mlb_team}</span>
                  {p.status && (
                    <span className="text-[8px] font-bold text-amber-400">
                      {p.status}
                    </span>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function IntelModule({
  data,
  news,
}: {
  data: MatchupAdvisorData;
  news: NewsData | null;
}) {
  const [tab, setTab] = useState<"games" | "news">("games");
  const gamesWithPlayers = data.games.filter(
    (g) => g.my_players.length > 0 || g.opp_players.length > 0
  );

  return (
    <div className="bg-white rounded-lg border border-border overflow-hidden">
      <div className="flex items-center border-b border-border">
        <button
          onClick={() => setTab("games")}
          className={`flex-1 text-[11px] font-bold uppercase tracking-wider py-2 transition-colors ${
            tab === "games"
              ? "text-navy border-b-2 border-navy"
              : "text-gray-400 hover:text-gray-600"
          }`}
        >
          Games ({gamesWithPlayers.length})
        </button>
        <button
          onClick={() => setTab("news")}
          className={`flex-1 text-[11px] font-bold uppercase tracking-wider py-2 transition-colors ${
            tab === "news"
              ? "text-navy border-b-2 border-navy"
              : "text-gray-400 hover:text-gray-600"
          }`}
        >
          News {news ? `(${news.total_items})` : ""}
        </button>
      </div>

      <div className="max-h-[400px] overflow-y-auto">
        {tab === "games" && (
          <>
            {gamesWithPlayers.length === 0 ? (
              <div className="p-4 text-center text-[11px] text-muted">
                No games with roster interest today
              </div>
            ) : (
              gamesWithPlayers.map((g, i) => <GameRow key={i} game={g} />)
            )}
          </>
        )}

        {tab === "news" && (
          <>
            {!news || news.items.length === 0 ? (
              <div className="p-4 text-center text-[11px] text-muted">
                No news updates
              </div>
            ) : (
              news.items.map((item, i) => <NewsRow key={i} item={item} />)
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SECTION HEADER
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function SectionLabel({
  number,
  title,
  count,
  accent,
}: {
  number: string;
  title: string;
  count?: number;
  accent?: string;
}) {
  return (
    <div className="flex items-center gap-2 px-1 py-1">
      <span
        className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-black text-white ${
          accent || "bg-navy"
        }`}
      >
        {number}
      </span>
      <span className="text-[11px] font-bold uppercase tracking-wider text-gray-600">
        {title}
      </span>
      {count !== undefined && count > 0 && (
        <span className="text-[10px] text-muted bg-gray-100 px-1.5 py-0.5 rounded-full tabular-nums">
          {count}
        </span>
      )}
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   MAIN PANEL
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

const POLL_MS = 600_000; // all data refreshes every 10 min

export default function MatchupAdvisorPanel() {
  const [data, setData] = useState<MatchupAdvisorData | null>(null);
  const [alerts, setAlerts] = useState<CriticalAlert[]>([]);
  const [news, setNews] = useState<NewsData | null>(null);
  const [error, setError] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const refreshScores = () => {
    api.matchupAdvisor().then((d) => {
      setData(d);
      setLastUpdate(new Date());
    }).catch(() => {});
  };

  useEffect(() => {
    api.matchupAdvisor().then((d) => {
      setData(d);
      setLastUpdate(new Date());
    }).catch(() => setError(true));

    api.alerts().then((d) => setAlerts(d.alerts)).catch(() => {});
    api.news().then(setNews).catch(() => {});

    const interval = setInterval(() => {
      refreshScores();
      api.alerts().then((d) => setAlerts(d.alerts)).catch(() => {});
      api.news().then(setNews).catch(() => {});
    }, POLL_MS);

    return () => clearInterval(interval);
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

  const hittingCats = data.category_analysis.filter((c) =>
    ["OBP", "R", "TB", "RBI", "SB"].includes(c.category)
  );
  const pitchingCats = data.category_analysis.filter((c) =>
    ["QS", "SH", "K", "ERA", "WHIP"].includes(c.category)
  );

  const actionCount = data.games.reduce(
    (n, g) => n + g.my_players.filter((p) => ACTION_VERDICTS.has(p.verdict)).length,
    0
  );

  return (
    <div className="space-y-4">
      {/* Scoreboard */}
      <Scoreboard
        data={data}
        hittingCats={hittingCats}
        pitchingCats={pitchingCats}
        lastUpdate={lastUpdate}
        onRefresh={refreshScores}
      />

      {/* 1. Action Items */}
      <div className="space-y-2">
        <SectionLabel
          number="1"
          title="Action Items"
          count={actionCount}
          accent={actionCount > 0 ? "bg-amber-500" : "bg-green-600"}
        />
        <ActionItems data={data} />
      </div>

      {/* 2. Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          <SectionLabel
            number="2"
            title="Alerts"
            count={alerts.length}
            accent="bg-red-500"
          />
          <AlertsModule alerts={alerts} />
        </div>
      )}

      {/* 3. Intel & News */}
      <div className="space-y-2">
        <SectionLabel
          number={alerts.length > 0 ? "3" : "2"}
          title="Intel & News"
        />
        <IntelModule data={data} news={news} />
      </div>
    </div>
  );
}
