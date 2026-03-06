const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).trim();

async function fetchJSON<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json();
}

export interface PlayerStats {
  OBP?: number;
  R?: number;
  TB?: number;
  RBI?: number;
  SB?: number;
  QS?: number;
  SH?: number;
  K?: number;
  ERA?: number;
  WHIP?: number;
}

export interface RosterPlayer {
  name: string;
  position: string;
  eligible_positions: string[];
  status: string;
  stats: PlayerStats;
}

export interface RosterData {
  team_key: string;
  team_name: string;
  week_stats: PlayerStats;
  category_ranks: Record<string, number>;
  roster: RosterPlayer[];
}

export interface TeamStanding {
  rank: number;
  team_key: string;
  team_name: string;
  record: { wins: number; losses: number; ties: number };
  points: number;
  category_ranks: Record<string, number>;
  category_totals: Record<string, number>;
}

export interface GapAnalysis {
  category: string;
  my_rank: number;
  my_value: number;
  league_avg: number;
  gap_to_next: number;
  direction: string;
  priority: string;
}

export interface StandingsData {
  my_team_key: string;
  standings: TeamStanding[];
  gap_analysis: GapAnalysis[];
  weak_categories: string[];
}

export interface FreeAgentRec {
  name: string;
  position: string;
  eligible_positions: string[];
  status: string;
  projected_stats: PlayerStats;
  waiver_score: number;
  helps_categories: string[];
  recommendation: string;
}

export interface WaiverData {
  recommendations: FreeAgentRec[];
  targeting: string[];
}

export interface MatchupTeam {
  team_key: string;
  team_name: string;
  stats: PlayerStats;
}

export interface MatchupData {
  week: number;
  my_team: MatchupTeam;
  opponent: MatchupTeam;
  category_results: Record<string, string>;
}

export interface KeeperEntry {
  player: string;
  round_cost: number;
  notes: string;
  value_score: number;
  collision_note?: string;
}

export interface KeeperData {
  keepers: KeeperEntry[];
}

export interface CriticalAlert {
  severity: "critical" | "warning";
  type: "injury" | "transaction" | "pickup";
  headline: string;
  detail: string;
  player: string;
  action: string;
}

export interface AlertsData {
  alerts: CriticalAlert[];
}

export interface MatchupPlayerAdvice {
  name: string;
  position: string;
  mlb_team: string;
  status: string;
  verdict: "confirmed" | "start" | "caution" | "monitor" | "consider" | "bench" | "out" | "no_game" | "not_starting";
  rationale: string;
  impact: string[];
}

export interface MatchupGameGroup {
  game_label: string;
  venue: string;
  status: string;
  away_pitcher: string;
  home_pitcher: string;
  my_players: MatchupPlayerAdvice[];
  opp_players: Array<{ name: string; position: string; mlb_team: string; status: string }>;
}

export interface CategoryAnalysis {
  category: string;
  my_value: number;
  opp_value: number;
  margin: number;
  status: "winning" | "losing" | "tied";
  flippable: boolean;
}

export interface MatchupAdvisorData {
  week: number;
  my_team: string;
  opponent: string;
  score: { winning: number; losing: number; tied: number };
  summary: string;
  category_analysis: CategoryAnalysis[];
  games: MatchupGameGroup[];
  date: string;
}

export interface NewsItem {
  type: string;
  priority: "high" | "medium" | "low";
  icon: string;
  headline: string;
  player: string;
  detail: string;
  date: string;
  source: string;
  url?: string;
  roster_tag?: "my_roster" | "opponent" | "";
}

export interface NewsData {
  generated_at: string;
  total_items: number;
  items: NewsItem[];
  games_today: number;
}

export const api = {
  alerts: () => fetchJSON<AlertsData>("/api/alerts"),
  roster: () => fetchJSON<RosterData>("/api/roster"),
  standings: () => fetchJSON<StandingsData>("/api/standings"),
  matchup: () => fetchJSON<MatchupData>("/api/matchup"),
  freeAgents: (pos?: string) =>
    fetchJSON<WaiverData>(`/api/free-agents${pos ? `?position=${pos}` : ""}`),
  keepers: () => fetchJSON<KeeperData>("/api/keepers"),
  matchupAdvisor: () => fetchJSON<MatchupAdvisorData>("/api/matchup/advisor"),
  news: () => fetchJSON<NewsData>("/api/news"),
};

export interface SSEEvent {
  event: "text_delta" | "tool_use" | "done" | "error";
  data: string;
}

export async function* streamChat(
  message: string,
  history: Array<{ role: string; content: string }>
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });

  if (!res.ok) {
    yield { event: "error", data: `HTTP ${res.status}` };
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const cleaned = line.replace(/^data: /, "").trim();
      if (!cleaned) continue;
      try {
        yield JSON.parse(cleaned) as SSEEvent;
      } catch {
        // skip malformed
      }
    }
  }
}
