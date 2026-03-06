"use client";

import { useEffect, useState } from "react";
import { api, type StandingsData } from "@/lib/api";

function RankCell({ rank }: { rank: number }) {
  const cls = rank <= 4 ? "rank-strong" : rank <= 8 ? "rank-mid" : "rank-weak";
  return <span className={cls}>{rank}</span>;
}

const ALL_CATS = ["OBP", "R", "TB", "RBI", "SB", "QS", "SH", "K", "ERA", "WHIP"];

export default function StandingsPanel() {
  const [data, setData] = useState<StandingsData | null>(null);

  useEffect(() => {
    api.standings().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted">
        Loading standings...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Gap Analysis */}
      {data.gap_analysis && data.gap_analysis.length > 0 && (
        <div className="bg-white rounded-lg border border-border overflow-hidden">
          <div className="bg-mlb-red px-3 py-2">
            <span className="text-white text-xs font-bold uppercase tracking-wider">Category Gap Analysis</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-surface text-subtle">
                  <th className="text-left py-1.5 px-2 font-semibold">Cat</th>
                  <th className="text-center py-1.5 px-2 font-semibold">Rank</th>
                  <th className="text-right py-1.5 px-2 font-semibold">Value</th>
                  <th className="text-right py-1.5 px-2 font-semibold">Lg Avg</th>
                  <th className="text-right py-1.5 px-2 font-semibold">Gap</th>
                  <th className="text-center py-1.5 px-2 font-semibold">Priority</th>
                </tr>
              </thead>
              <tbody>
                {data.gap_analysis.map((gap, i) => (
                  <tr key={gap.category} className={`border-t border-border ${i % 2 === 0 ? "" : "bg-surface/50"}`}>
                    <td className="py-1.5 px-2 font-bold">{gap.category === "SH" ? "S+H" : gap.category}</td>
                    <td className="text-center py-1.5 px-2"><RankCell rank={gap.my_rank} /></td>
                    <td className="text-right py-1.5 px-2 tabular-nums">
                      {gap.my_value != null ? (gap.my_value < 1 && gap.my_value > 0 ? gap.my_value.toFixed(3) : gap.my_value.toFixed(gap.my_value % 1 === 0 ? 0 : 2)) : "—"}
                    </td>
                    <td className="text-right py-1.5 px-2 tabular-nums text-muted">
                      {gap.league_avg != null ? (gap.league_avg < 1 && gap.league_avg > 0 ? gap.league_avg.toFixed(3) : gap.league_avg.toFixed(gap.league_avg % 1 === 0 ? 0 : 2)) : "—"}
                    </td>
                    <td className="text-right py-1.5 px-2 tabular-nums">
                      {gap.gap_to_next != null ? (gap.gap_to_next < 1 && gap.gap_to_next > 0 ? gap.gap_to_next.toFixed(3) : gap.gap_to_next.toFixed(gap.gap_to_next % 1 === 0 ? 0 : 2)) : "—"}
                    </td>
                    <td className="text-center py-1.5 px-2">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        gap.priority === "high" ? "bg-red-50 text-red-700" :
                        gap.priority === "medium" ? "bg-amber-50 text-amber-700" :
                        "bg-green-50 text-green-700"
                      }`}>
                        {gap.priority}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* League Standings */}
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <div className="bg-navy px-3 py-2">
          <span className="text-white text-xs font-bold uppercase tracking-wider">League Standings</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-surface text-subtle">
                <th className="text-center py-1.5 px-1.5 font-semibold w-8">#</th>
                <th className="text-left py-1.5 px-2 font-semibold">Team</th>
                <th className="text-center py-1.5 px-1.5 font-semibold">W-L-T</th>
                {ALL_CATS.map((cat) => (
                  <th key={cat} className="text-center py-1.5 px-1 font-semibold">
                    {cat === "SH" ? "S+H" : cat}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.standings.map((team, i) => {
                const isMyTeam = team.team_key === data.my_team_key;
                return (
                  <tr
                    key={team.team_key}
                    className={`border-t border-border ${
                      isMyTeam ? "bg-blue-50/60 font-medium" : i % 2 === 0 ? "" : "bg-surface/50"
                    }`}
                  >
                    <td className="text-center py-1.5 px-1.5 text-muted">{team.rank}</td>
                    <td className="py-1.5 px-2 whitespace-nowrap">
                      {isMyTeam && <span className="inline-block w-1.5 h-1.5 rounded-full bg-mlb-red mr-1.5" />}
                      {team.team_name}
                    </td>
                    <td className="text-center py-1.5 px-1.5 tabular-nums text-muted">
                      {team.record ? `${team.record.wins}-${team.record.losses}-${team.record.ties}` : "—"}
                    </td>
                    {ALL_CATS.map((cat) => (
                      <td key={cat} className="text-center py-1.5 px-1">
                        <RankCell rank={(team.category_ranks ?? {})[cat] || 0} />
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
