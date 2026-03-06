"use client";

import { useEffect, useState } from "react";
import { api, type CriticalAlert } from "@/lib/api";

const SEVERITY_STYLES = {
  critical: {
    bg: "bg-red-600",
    icon: "🚨",
    actionBg: "bg-white text-red-700 hover:bg-red-50",
  },
  warning: {
    bg: "bg-amber-500",
    icon: "⚠️",
    actionBg: "bg-white text-amber-700 hover:bg-amber-50",
  },
} as const;

function AlertRow({
  alert,
  onDismiss,
}: {
  alert: CriticalAlert;
  onDismiss: () => void;
}) {
  const style = SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.warning;

  return (
    <div className={`${style.bg} text-white`}>
      <div className="max-w-[1440px] mx-auto px-4 py-2 flex items-center gap-3">
        <span className="text-sm flex-shrink-0">{style.icon}</span>

        <div className="flex-1 min-w-0 flex items-center gap-3">
          <span className="text-[11px] font-black uppercase tracking-wider opacity-80">
            {alert.type === "injury"
              ? "Injury Alert"
              : alert.type === "transaction"
              ? "Transaction"
              : "Pickup Alert"}
          </span>
          <span className="text-[13px] font-bold truncate">
            {alert.headline}
          </span>
          <span className="text-[11px] opacity-80 hidden sm:inline truncate">
            {alert.detail}
          </span>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <span
            className={`text-[10px] font-bold px-2 py-1 rounded ${style.actionBg} cursor-default`}
          >
            {alert.action}
          </span>
          <button
            onClick={onDismiss}
            className="text-white/60 hover:text-white text-sm font-bold w-5 h-5 flex items-center justify-center rounded hover:bg-white/10 transition-colors"
            aria-label="Dismiss alert"
          >
            ×
          </button>
        </div>
      </div>
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
    <div className="border-b border-black/10">
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
