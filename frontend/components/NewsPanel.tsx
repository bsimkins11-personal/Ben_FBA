"use client";

import { useEffect, useState } from "react";
import { api, type NewsData, type NewsItem } from "@/lib/api";

const ICON_MAP: Record<string, string> = {
  injury: "🏥",
  transaction: "📋",
  pitching: "⚾",
  schedule: "📅",
  callup: "🔼",
  return: "✅",
  dfa: "🔻",
  news: "📰",
};

const PRIORITY_STYLES: Record<string, string> = {
  high: "border-l-4 border-l-mlb-red bg-red-50/60",
  medium: "border-l-4 border-l-yellow-500 bg-yellow-50/40",
  low: "border-l-2 border-l-gray-200",
};

function NewsCard({ item }: { item: NewsItem }) {
  const icon = ICON_MAP[item.icon] || "📰";
  const style = PRIORITY_STYLES[item.priority] || "";

  const isMyRoster = item.roster_tag === "my_roster";
  const isOpponent = item.roster_tag === "opponent";

  return (
    <div className={`p-3 rounded-md ${style} transition-all hover:shadow-sm`}>
      <div className="flex items-start gap-2">
        <span className="text-lg flex-shrink-0 mt-0.5">{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {isMyRoster && (
              <span className="text-[9px] font-bold uppercase tracking-wider bg-mlb-red text-white px-1.5 py-0.5 rounded">
                Your Roster
              </span>
            )}
            {isOpponent && (
              <span className="text-[9px] font-bold uppercase tracking-wider bg-gray-700 text-white px-1.5 py-0.5 rounded">
                Opponent
              </span>
            )}
            {item.type === "start_today" && (
              <span className="text-[9px] font-bold uppercase tracking-wider bg-navy text-white px-1.5 py-0.5 rounded">
                Starting Today
              </span>
            )}
            {item.type === "waiver_intel" && (
              <span className="text-[9px] font-bold uppercase tracking-wider bg-green-700 text-white px-1.5 py-0.5 rounded">
                Waiver Wire
              </span>
            )}
          </div>
          <p className="text-[13px] font-semibold text-foreground mt-1 leading-tight">
            {item.headline}
          </p>
          {item.detail && item.type !== "start_today" && (
            <p className="text-[11px] text-muted mt-1 leading-snug line-clamp-2">
              {item.detail}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1.5">
            {item.source && (
              <span className="text-[10px] text-subtle">{item.source}</span>
            )}
            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[10px] text-navy hover:underline"
              >
                Read →
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NewsPanel() {
  const [data, setData] = useState<NewsData | null>(null);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState<
    "all" | "roster" | "opponent" | "waiver" | "news"
  >("all");

  useEffect(() => {
    api
      .news()
      .then(setData)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted">
        Unable to load news — MLB data sources may be unavailable
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted">
        Loading MLB intel...
      </div>
    );
  }

  const filters = [
    { id: "all" as const, label: "All" },
    { id: "roster" as const, label: "My Roster" },
    { id: "opponent" as const, label: "Opponent" },
    { id: "waiver" as const, label: "Waiver Intel" },
    { id: "news" as const, label: "Headlines" },
  ];

  const filtered = data.items.filter((item) => {
    if (filter === "all") return true;
    if (filter === "roster")
      return item.roster_tag === "my_roster";
    if (filter === "opponent")
      return item.roster_tag === "opponent";
    if (filter === "waiver") return item.type === "waiver_intel";
    if (filter === "news") return item.type === "news";
    return true;
  });

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="bg-white rounded-lg border border-border overflow-hidden">
        <div className="bg-navy px-3 py-2 flex items-center justify-between">
          <span className="text-white text-xs font-bold uppercase tracking-wider">
            MLB Intel Feed
          </span>
          <span className="text-white/50 text-[10px]">
            {data.games_today} games today · {data.total_items} updates
          </span>
        </div>

        {/* Filters */}
        <div className="flex gap-1 p-2 border-b border-border bg-surface/50">
          {filters.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`text-[11px] font-semibold px-2.5 py-1 rounded transition-all ${
                filter === f.id
                  ? "bg-navy text-white"
                  : "text-subtle hover:bg-white hover:shadow-sm"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* News Items */}
        <div className="divide-y divide-border max-h-[600px] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted">
              No items match this filter
            </div>
          ) : (
            filtered.map((item, i) => <NewsCard key={i} item={item} />)
          )}
        </div>
      </div>
    </div>
  );
}
