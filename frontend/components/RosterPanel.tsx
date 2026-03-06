"use client";

import { useEffect, useState } from "react";
import { api, type RosterData } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  if (!status) return null;
  const cls = status.startsWith("IL") ? "badge-il" : "badge-dtd";
  return <span className={cls}>{status}</span>;
}

function RankCell({ rank }: { rank: number }) {
  const cls = rank <= 4 ? "rank-strong" : rank <= 8 ? "rank-mid" : "rank-weak";
  return <span className={cls}>{rank}</span>;
}

const HITTING_CATS = ["OBP", "R", "TB", "RBI", "SB"];
const PITCHING_CATS = ["QS", "SH", "K", "ERA", "WHIP"];

export default function RosterPanel() {
  const [data, setData] = useState<RosterData | null>(null);

  useEffect(() => {
    api.roster().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted">
        Loading roster...
      </div>
    );
  }

  const roster = data.roster ?? [];
  const categoryRanks = data.category_ranks ?? {};

  const hitters = roster.filter(
    (p) => !["SP", "RP", "P"].some((pos) => (p.eligible_positions ?? []).includes(pos) && !(p.eligible_positions ?? []).includes("Util"))
  ).filter((p) => p.stats?.OBP !== undefined);

  const pitchers = roster.filter(
    (p) => ["SP", "RP", "P"].some((pos) => (p.eligible_positions ?? []).includes(pos))
  );

  if (roster.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-border p-6 text-center">
        <p className="text-sm font-semibold text-navy">No Roster Data</p>
        <p className="text-xs text-muted mt-1">Roster data will populate once the season starts or after syncing with Yahoo.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Category Ranks Summary */}
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <div className="bg-navy px-3 py-2">
          <span className="text-white text-xs font-bold uppercase tracking-wider">Category Ranks</span>
        </div>
        <div className="grid grid-cols-5 text-center text-[11px] border-b border-border">
          {HITTING_CATS.map((cat) => (
            <div key={cat} className="py-2 border-r border-border last:border-r-0">
              <div className="text-muted font-medium">{cat}</div>
              <div className="text-lg mt-0.5">
                <RankCell rank={categoryRanks[cat] || 0} />
              </div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-5 text-center text-[11px]">
          {PITCHING_CATS.map((cat) => (
            <div key={cat} className="py-2 border-r border-border last:border-r-0">
              <div className="text-muted font-medium">{cat === "SH" ? "S+H" : cat}</div>
              <div className="text-lg mt-0.5">
                <RankCell rank={categoryRanks[cat] || 0} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Hitters Table */}
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <div className="bg-navy-dark px-3 py-2 flex items-center justify-between">
          <span className="text-white text-xs font-bold uppercase tracking-wider">Hitters</span>
          <span className="text-white/50 text-[10px]">Week Stats</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-surface text-subtle">
                <th className="text-left py-1.5 px-2 font-semibold">Pos</th>
                <th className="text-left py-1.5 px-2 font-semibold">Player</th>
                <th className="text-right py-1.5 px-2 font-semibold">OBP</th>
                <th className="text-right py-1.5 px-2 font-semibold">R</th>
                <th className="text-right py-1.5 px-2 font-semibold">TB</th>
                <th className="text-right py-1.5 px-2 font-semibold">RBI</th>
                <th className="text-right py-1.5 px-2 font-semibold">SB</th>
              </tr>
            </thead>
            <tbody>
              {hitters.map((p, i) => (
                <tr key={p.name} className={`border-t border-border ${i % 2 === 0 ? "" : "bg-surface/50"} ${p.position === "BN" || p.position === "DL" ? "opacity-60" : ""}`}>
                  <td className="py-1.5 px-2 text-muted font-medium">{p.position}</td>
                  <td className="py-1.5 px-2 font-medium">
                    {p.name} <StatusBadge status={p.status ?? ""} />
                  </td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.OBP?.toFixed(3) ?? "—"}</td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.R ?? "—"}</td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.TB ?? "—"}</td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.RBI ?? "—"}</td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.SB ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pitchers Table */}
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <div className="bg-navy-dark px-3 py-2 flex items-center justify-between">
          <span className="text-white text-xs font-bold uppercase tracking-wider">Pitchers</span>
          <span className="text-white/50 text-[10px]">Week Stats</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-surface text-subtle">
                <th className="text-left py-1.5 px-2 font-semibold">Pos</th>
                <th className="text-left py-1.5 px-2 font-semibold">Player</th>
                <th className="text-right py-1.5 px-2 font-semibold">QS</th>
                <th className="text-right py-1.5 px-2 font-semibold">S+H</th>
                <th className="text-right py-1.5 px-2 font-semibold">K</th>
                <th className="text-right py-1.5 px-2 font-semibold">ERA</th>
                <th className="text-right py-1.5 px-2 font-semibold">WHIP</th>
              </tr>
            </thead>
            <tbody>
              {pitchers.map((p, i) => (
                <tr key={p.name} className={`border-t border-border ${i % 2 === 0 ? "" : "bg-surface/50"} ${p.position === "BN" || p.position === "DL" ? "opacity-60" : ""}`}>
                  <td className="py-1.5 px-2 text-muted font-medium">{p.position}</td>
                  <td className="py-1.5 px-2 font-medium">
                    {p.name} <StatusBadge status={p.status ?? ""} />
                  </td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.QS ?? "—"}</td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.SH ?? "—"}</td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.K ?? "—"}</td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.ERA?.toFixed(2) ?? "—"}</td>
                  <td className="text-right py-1.5 px-2 tabular-nums">{p.stats?.WHIP?.toFixed(2) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
