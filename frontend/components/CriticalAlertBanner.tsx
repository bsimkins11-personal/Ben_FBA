"use client";

import { useEffect, useState } from "react";
import { api, type CriticalAlert } from "@/lib/api";

function AlertRow({
  alert,
  onDismiss,
}: {
  alert: CriticalAlert;
  onDismiss: () => void;
}) {
  const isCritical = alert.severity === "critical";
  const dotColor = isCritical ? "bg-red-400" : "bg-amber-400";
  const labelColor = isCritical ? "text-red-300" : "text-amber-300";
  const actionColor = isCritical
    ? "text-red-300 border-red-400/30 hover:bg-red-400/10"
    : "text-amber-300 border-amber-400/30 hover:bg-amber-400/10";

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-1.5 flex items-center gap-2.5 text-white/80">
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} flex-shrink-0`} />

      <span className={`text-[10px] font-semibold uppercase tracking-wider ${labelColor} flex-shrink-0`}>
        {alert.type === "injury"
          ? "Injury"
          : alert.type === "transaction"
          ? "Transaction"
          : "Pickup"}
      </span>

      <span className="text-[11px] font-medium truncate flex-1">
        {alert.headline}
      </span>

      <span className="text-[10px] text-white/40 hidden sm:inline truncate max-w-[40%]">
        {alert.detail}
      </span>

      <span
        className={`text-[9px] font-semibold px-1.5 py-0.5 rounded border ${actionColor} cursor-default flex-shrink-0`}
      >
        {alert.action}
      </span>

      <button
        onClick={onDismiss}
        className="text-white/30 hover:text-white/60 text-xs w-4 h-4 flex items-center justify-center rounded transition-colors flex-shrink-0"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

export default function CriticalAlertBanner() {
  const [alerts, setAlerts] = useState<CriticalAlert[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  useEffect(() => {
    api
      .alerts()
      .then((data) => setAlerts(data.alerts))
      .catch(() => {});

    const interval = setInterval(() => {
      api
        .alerts()
        .then((data) => setAlerts(data.alerts))
        .catch(() => {});
    }, 120_000);

    return () => clearInterval(interval);
  }, []);

  const visible = alerts.filter(
    (a) => !dismissed.has(`${a.type}:${a.player}`)
  );

  if (visible.length === 0) return null;

  return (
    <div className="bg-navy-dark/95 border-b border-white/5 divide-y divide-white/5">
      {visible.map((alert) => {
        const key = `${alert.type}:${alert.player}`;
        return (
          <AlertRow
            key={key}
            alert={alert}
            onDismiss={() =>
              setDismissed((prev) => new Set([...prev, key]))
            }
          />
        );
      })}
    </div>
  );
}
