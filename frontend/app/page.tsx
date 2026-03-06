"use client";

import { useState } from "react";
import Image from "next/image";
import ChatPanel from "@/components/ChatPanel";
import RosterPanel from "@/components/RosterPanel";
import StandingsPanel from "@/components/StandingsPanel";
import WaiverPanel from "@/components/WaiverPanel";
import KeeperPanel from "@/components/KeeperPanel";
import MatchupAdvisorPanel from "@/components/MatchupAdvisorPanel";
import MatchupBar from "@/components/MatchupBar";

const TABS = [
  { id: "matchup", label: "Command Center" },
  { id: "roster", label: "Roster" },
  { id: "standings", label: "Standings" },
  { id: "waivers", label: "Waivers" },
  { id: "keepers", label: "Keepers" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>("matchup");

  return (
    <div className="min-h-[calc(100vh-48px)]">
      {/* Hero Banner */}
      <div className="relative h-36 md:h-44 overflow-hidden bg-navy-dark">
        <Image
          src="/images/hero-banner.png"
          alt="Bush League Co-Pilot"
          fill
          className="object-cover object-center opacity-40"
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-r from-navy-dark/90 via-navy-dark/60 to-transparent" />
        <div className="relative max-w-[1440px] mx-auto px-4 h-full flex items-center">
          <div>
            <h1 className="text-white text-2xl md:text-3xl font-black tracking-tight">
              Bush League
              <span className="text-mlb-red ml-2">Co-Pilot</span>
            </h1>
            <p className="text-white/60 text-xs md:text-sm mt-1">
              Your AI-powered fantasy baseball advisor — 5×5 Rotisserie
            </p>
          </div>
        </div>
      </div>

      {/* Main Layout */}
      <div className="max-w-[1440px] mx-auto px-4 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-4">
          {/* Left: Data Panels */}
          <div className="space-y-4">
            {/* Matchup Bar */}
            <MatchupBar />

            {/* Tab Navigation */}
            <div className="flex gap-0.5 bg-surface rounded-lg p-0.5 border border-border">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 text-xs font-bold uppercase tracking-wider py-2 rounded-md transition-all ${
                    activeTab === tab.id
                      ? "bg-navy text-white shadow-sm"
                      : "text-subtle hover:bg-white hover:shadow-sm"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Active Panel */}
            <div>
              {activeTab === "matchup" && <MatchupAdvisorPanel />}
              {activeTab === "roster" && <RosterPanel />}
              {activeTab === "standings" && <StandingsPanel />}
              {activeTab === "waivers" && <WaiverPanel />}
              {activeTab === "keepers" && <KeeperPanel />}
            </div>
          </div>

          {/* Right: Chat Panel */}
          <div className="lg:sticky lg:top-4 h-[calc(100vh-220px)] min-h-[500px] bg-white rounded-lg border border-border overflow-hidden shadow-sm">
            <ChatPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
