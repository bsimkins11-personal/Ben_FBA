"use client";

import { useEffect, useState } from "react";
import { api, type MatchupData } from "@/lib/api";

const ALL_CATS = ["OBP", "R", "TB", "RBI", "SB", "QS", "SH", "K", "ERA", "WHIP"];

export default function MatchupBar() {
  const [data, setData] = useState<MatchupData | null>(null);

  useEffect(() => {
    api.matchup().then(setData).catch(console.error);
  }, []);

  if (!data || !data.category_results || !data.my_team || !data.opponent) return null;

  const catResults = data.category_results ?? {};
  const wins = Object.values(catResults).filter((v) => v === "winning").length;
  const losses = Object.values(catResults).filter((v) => v === "losing").length;
  const ties = Object.values(catResults).filter((v) => v === "tied").length;

  return (
    <div className="bg-white rounded-lg border border-border overflow-hidden">
      <div className="bg-navy px-3 py-2 flex items-center justify-between">
        <span className="text-white text-xs font-bold uppercase tracking-wider">
          Week {data.week} Matchup
        </span>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
          wins > losses ? "bg-green-500/20 text-green-200" :
          wins < losses ? "bg-red-500/20 text-red-200" :
          "bg-yellow-500/20 text-yellow-200"
        }`}>
          {wins}-{losses}{ties > 0 ? `-${ties}` : ""}
        </span>
      </div>

      {/* Team names row */}
      <div className="grid grid-cols-[1fr_auto_1fr] text-[11px] py-1.5 px-2 bg-surface border-b border-border">
        <span className="font-bold text-navy">{data.my_team.team_name}</span>
        <span className="text-muted px-2">vs</span>
        <span className="font-bold text-right text-subtle">{data.opponent.team_name}</span>
      </div>

      {/* Category-by-category */}
      <div className="divide-y divide-border">
        {ALL_CATS.map((cat) => {
          const myStats = (data.my_team.stats ?? {}) as Record<string, number>;
          const oppStats = (data.opponent.stats ?? {}) as Record<string, number>;
          const myStat = myStats[cat];
          const oppStat = oppStats[cat];
          const result = catResults[cat] || "tied";
          const cellClass = result === "winning" ? "cat-win" : result === "losing" ? "cat-lose" : "cat-tie";

          const fmtStat = (v: number | undefined) => {
            if (v == null) return "—";
            return v < 1 && v > 0 ? v.toFixed(3) : v.toFixed(v % 1 === 0 ? 0 : 2);
          };

          return (
            <div key={cat} className={`grid grid-cols-[1fr_auto_1fr] text-[12px] py-1 px-2 ${cellClass}`}>
              <span className={`tabular-nums ${result === "winning" ? "font-bold text-green-800" : ""}`}>
                {fmtStat(myStat)}
              </span>
              <span className="text-[10px] text-muted font-semibold px-2 text-center w-10">
                {cat === "SH" ? "S+H" : cat}
              </span>
              <span className={`tabular-nums text-right ${result === "losing" ? "font-bold text-red-800" : ""}`}>
                {fmtStat(oppStat)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
