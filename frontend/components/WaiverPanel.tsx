"use client";

import { useEffect, useState } from "react";
import { api, type WaiverData } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  if (!status) return null;
  const cls = status.startsWith("IL") ? "badge-il" : "badge-dtd";
  return <span className={cls}>{status}</span>;
}

const POSITIONS = ["All", "C", "1B", "2B", "3B", "SS", "OF", "SP", "RP"];

export default function WaiverPanel() {
  const [data, setData] = useState<WaiverData | null>(null);
  const [position, setPosition] = useState("All");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const pos = position === "All" ? undefined : position;
    api.freeAgents(pos).then(setData).catch(console.error).finally(() => setLoading(false));
  }, [position]);

  return (
    <div className="space-y-3">
      {/* Position Filter */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {POSITIONS.map((pos) => (
          <button
            key={pos}
            onClick={() => setPosition(pos)}
            className={`text-[11px] px-2.5 py-1 rounded-full font-semibold transition-colors ${
              position === pos
                ? "bg-navy text-white"
                : "bg-white text-subtle border border-border hover:border-navy/30"
            }`}
          >
            {pos}
          </button>
        ))}
      </div>

      {/* Targeting Weak Categories */}
      {data?.targeting && data.targeting.length > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-lg px-3 py-2 flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-mlb-red shrink-0">
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="6" />
            <circle cx="12" cy="12" r="2" />
          </svg>
          <span className="text-[11px] text-red-800">
            <span className="font-bold">Targeting:</span>{" "}
            {data.targeting.map((c) => (c === "SH" ? "S+H" : c)).join(", ")}
          </span>
        </div>
      )}

      {/* FA Recommendations */}
      {loading ? (
        <div className="flex items-center justify-center h-32 text-sm text-muted">
          Loading free agents...
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-border overflow-hidden">
          <div className="bg-navy-dark px-3 py-2 flex items-center justify-between">
            <span className="text-white text-xs font-bold uppercase tracking-wider">Waiver Wire</span>
            <span className="text-white/50 text-[10px]">{data?.recommendations.length || 0} players</span>
          </div>
          <div className="divide-y divide-border">
            {data?.recommendations.map((fa, i) => {
              const isHitter = fa.projected_stats.OBP !== undefined;
              return (
                <div key={fa.name} className={`px-3 py-2.5 ${i % 2 === 0 ? "" : "bg-surface/50"}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[13px] font-semibold">{fa.name}</span>
                        <StatusBadge status={fa.status} />
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-muted font-medium">
                          {fa.eligible_positions.join(" / ")}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[11px] font-bold text-navy tabular-nums">
                        {fa.waiver_score.toFixed(1)}
                      </div>
                      <div className="text-[9px] text-muted">score</div>
                    </div>
                  </div>

                  {/* Projected Stats */}
                  <div className="flex gap-3 mt-1.5 text-[10px] tabular-nums text-subtle">
                    {isHitter ? (
                      <>
                        <span>OBP {fa.projected_stats.OBP?.toFixed(3)}</span>
                        <span>R {fa.projected_stats.R}</span>
                        <span>TB {fa.projected_stats.TB}</span>
                        <span>RBI {fa.projected_stats.RBI}</span>
                        <span>SB {fa.projected_stats.SB}</span>
                      </>
                    ) : (
                      <>
                        <span>QS {fa.projected_stats.QS}</span>
                        <span>S+H {fa.projected_stats.SH}</span>
                        <span>K {fa.projected_stats.K}</span>
                        <span>ERA {fa.projected_stats.ERA?.toFixed(2)}</span>
                        <span>WHIP {fa.projected_stats.WHIP?.toFixed(2)}</span>
                      </>
                    )}
                  </div>

                  {/* Recommendation */}
                  <div className="mt-1.5 flex items-center gap-1.5">
                    {fa.helps_categories.map((cat) => (
                      <span key={cat} className="text-[9px] px-1.5 py-0.5 rounded bg-green-50 text-green-800 font-semibold">
                        {cat === "SH" ? "S+H" : cat}
                      </span>
                    ))}
                    <span className="text-[10px] text-muted italic ml-1">{fa.recommendation}</span>
                  </div>
                </div>
              );
            })}
            {(!data?.recommendations || data.recommendations.length === 0) && (
              <div className="py-8 text-center text-sm text-muted">
                No free agents match this filter
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
