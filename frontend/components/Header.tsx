"use client";

import { useEffect, useState } from "react";
import { api, type AuthStatus } from "@/lib/api";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).trim();

export default function Header() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);

  const checkAuth = () => {
    api.authStatus().then(setAuth).catch(() => {});
  };

  useEffect(() => {
    checkAuth();

    const params = new URLSearchParams(window.location.search);
    if (params.get("auth") === "success") {
      checkAuth();
      window.history.replaceState({}, "", "/");
    }
  }, []);

  const handleLogin = () => {
    window.location.href = `${API_URL}/auth/yahoo`;
  };

  const handleLogout = () => {
    api.logout().then(() => {
      setAuth({ authenticated: false, mode: "synthetic", league_key: "", team_key: "" });
    });
  };

  const isLive = auth?.authenticated;

  return (
    <header className="bg-navy-dark text-white">
      <div className="max-w-[1440px] mx-auto flex items-center justify-between px-4 h-12">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-mlb-red flex items-center justify-center text-[10px] font-black tracking-tight">
            BL
          </div>
          <span className="text-sm font-bold tracking-wide uppercase">
            Bush League Co-Pilot
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <span className="text-white/60">2026 Season</span>

          {isLive ? (
            <>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-mlb-green inline-block animate-pulse" />
                <span className="text-mlb-green font-bold">Live</span>
              </div>
              <button
                onClick={handleLogout}
                className="text-white/40 hover:text-white/80 text-[10px] uppercase tracking-wider transition-colors"
              >
                Disconnect
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
                <span className="text-white/80">Synthetic</span>
              </div>
              <button
                onClick={handleLogin}
                className="bg-[#720e9e] hover:bg-[#5c0b80] text-white text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded transition-colors"
              >
                Connect Yahoo
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
