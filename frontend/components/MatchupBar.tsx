"use client";

import { useEffect, useState } from "react";
import { api, type StandingsData } from "@/lib/api";

const ALL_CATS = ["OBP", "R", "TB", "RBI", "SB", "QS", "SH", "K", "ERA", "WHIP"];

export default function MatchupBar() {
  const [data, setData] = useState<StandingsData | null>(null);

  useEffect(() => {
    api.standings().then(setData).catch(console.error);
  }, []);

  if (!data || !data.gap_analysis || data.gap_analysis.length === 0) return null;

  const topHalf = data.gap_analysis.filter((g) => g.my_rank <= Math.ceil((data.standings?.length || 11) / 2)).length;

  return (
    <div className="bg-white rounded-lg border border-border overflow-hidden">
      <div className="bg-navy px-3 py-2 flex items-center justify-between">
        <span className="text-white text-xs font-bold uppercase tracking-wider">
          Roto Category Ranks
        </span>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
          topHalf >= 6 ? "bg-green-500/20 text-green-200" :
          topHalf >= 4 ? "bg-yellow-500/20 text-yellow-200" :
          "bg-red-500/20 text-red-200"
        }`}>
          {topHalf} of 10 top half
        </span>
      </div>

      <div className="divide-y divide-border">
        {data.gap_analysis.map((gap) => {
          const numTeams = data.standings?.length || 11;
          const isTopHalf = gap.my_rank <= Math.ceil(numTeams / 2);

          const fmtVal = (v: number | undefined) => {
            if (v == null) return "—";
            return v < 1 && v > 0 ? v.toFixed(3) : v.toFixed(v % 1 === 0 ? 0 : 2);
          };

          return (
            <div key={gap.category} className={`grid grid-cols-[auto_1fr_auto] text-[12px] py-1 px-2 ${
              isTopHalf ? "cat-win" : "cat-lose"
            }`}>
              <span className="text-[10px] text-muted font-semibold w-10">
                {gap.category === "SH" ? "S+H" : gap.category}
              </span>
              <span className={`tabular-nums text-center ${
                isTopHalf ? "font-bold text-green-800" : "text-red-800"
              }`}>
                {fmtVal(gap.my_value)}
              </span>
              <span className={`text-[11px] font-bold w-8 text-right ${
                gap.my_rank <= 3 ? "text-green-700" : gap.my_rank >= 8 ? "text-red-600" : "text-gray-500"
              }`}>
                {gap.my_rank}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
