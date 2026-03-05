"use client";

import { useEffect, useState } from "react";
import { api, type KeeperData } from "@/lib/api";

export default function KeeperPanel() {
  const [data, setData] = useState<KeeperData | null>(null);

  useEffect(() => {
    api.keepers().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted">
        Loading keeper analysis...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <div className="bg-navy px-3 py-2 flex items-center justify-between">
          <span className="text-white text-xs font-bold uppercase tracking-wider">Keeper Calculator</span>
          <span className="text-white/50 text-[10px]">Max 8 keepers</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-surface text-subtle">
                <th className="text-center py-1.5 px-2 font-semibold w-8">#</th>
                <th className="text-left py-1.5 px-2 font-semibold">Player</th>
                <th className="text-center py-1.5 px-2 font-semibold">Round Cost</th>
                <th className="text-center py-1.5 px-2 font-semibold">Value</th>
                <th className="text-left py-1.5 px-2 font-semibold">Rule</th>
              </tr>
            </thead>
            <tbody>
              {data.keepers.map((keeper, i) => {
                const isGreatValue = keeper.value_score >= 15;
                const isGoodValue = keeper.value_score >= 10;
                return (
                  <tr
                    key={keeper.player}
                    className={`border-t border-border ${i % 2 === 0 ? "" : "bg-surface/50"}`}
                  >
                    <td className="text-center py-2 px-2 text-muted">{i + 1}</td>
                    <td className="py-2 px-2 font-semibold">{keeper.player}</td>
                    <td className="text-center py-2 px-2">
                      <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-[11px] font-bold ${
                        keeper.round_cost <= 3 ? "bg-red-100 text-red-800" :
                        keeper.round_cost <= 10 ? "bg-amber-100 text-amber-800" :
                        "bg-green-100 text-green-800"
                      }`}>
                        {keeper.round_cost}
                      </span>
                    </td>
                    <td className="text-center py-2 px-2">
                      <span className={`text-sm font-bold ${
                        isGreatValue ? "text-green-600" :
                        isGoodValue ? "text-amber-600" :
                        "text-gray-500"
                      }`}>
                        {keeper.value_score.toFixed(0)}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      <span className="text-[10px] text-muted">{keeper.notes}</span>
                      {keeper.collision_note && (
                        <div className="text-[10px] text-red-600 mt-0.5">{keeper.collision_note}</div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Value Legend */}
      <div className="bg-white rounded-lg border border-border px-3 py-2">
        <div className="text-[10px] text-muted font-medium mb-1.5">VALUE GUIDE</div>
        <div className="flex gap-4 text-[10px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span>15+ = Elite value</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span>10-14 = Good value</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-gray-400" />
            <span>&lt;10 = Consider alternatives</span>
          </div>
        </div>
        <div className="text-[10px] text-muted mt-1.5">
          Value = 20 - Round Cost. Higher = better deal. Round cost based on Bush League constitution rules 6.2, 6.3, 6.9.
        </div>
      </div>
    </div>
  );
}
