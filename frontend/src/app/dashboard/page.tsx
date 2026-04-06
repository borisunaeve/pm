"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getMyCards,
  getDashboardSummary,
  clearAuth,
  getUser,
  isLoggedIn,
  type DashboardCard,
  type DashboardSummary,
} from "@/lib/api";

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-500/15 text-red-400 border-red-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low: "bg-green-500/15 text-green-400 border-green-500/30",
};

function isOverdue(due: string | null): boolean {
  if (!due) return false;
  return due < new Date().toISOString().split("T")[0];
}

function isDueSoon(due: string | null): boolean {
  if (!due) return false;
  const today = new Date().toISOString().split("T")[0];
  const soon = new Date(Date.now() + 3 * 86400000).toISOString().split("T")[0];
  return due >= today && due <= soon;
}

function CardRow({ card, onClick }: { card: DashboardCard; onClick: () => void }) {
  const overdue = isOverdue(card.due_date);
  const soon = !overdue && isDueSoon(card.due_date);

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-xl px-4 py-3 transition-colors group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm font-medium truncate">{card.title}</p>
          <p className="text-white/40 text-xs mt-0.5 truncate">
            {card.board_title} &bull; {card.column_title}
          </p>
          {card.labels && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {card.labels.split(",").filter(Boolean).map((l) => (
                <span key={l} className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#209dd7]/15 text-[#209dd7] border border-[#209dd7]/30">
                  {l.trim()}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${PRIORITY_COLORS[card.priority] ?? PRIORITY_COLORS.medium}`}>
            {card.priority}
          </span>
          {card.due_date && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
              overdue ? "bg-red-500/15 text-red-400" :
              soon ? "bg-amber-500/15 text-amber-400" :
              "bg-white/10 text-white/50"
            }`}>
              {overdue ? "Overdue" : soon ? "Due soon" : card.due_date}
            </span>
          )}
          {card.checklist_total > 0 && (
            <span className="text-[10px] text-white/40">
              {card.checklist_done}/{card.checklist_total}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

function StatCard({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl px-5 py-4">
      <p className="text-white/40 text-xs uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-display font-bold mt-1 ${accent ?? "text-white"}`}>{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const user = getUser();
  const [cards, setCards] = useState<DashboardCard[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "overdue" | "soon" | "no-date">("all");

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    Promise.all([getMyCards(), getDashboardSummary()])
      .then(([c, s]) => { setCards(c); setSummary(s); })
      .finally(() => setLoading(false));
  }, [router]);

  const filtered = cards.filter((c) => {
    if (filter === "overdue") return isOverdue(c.due_date);
    if (filter === "soon") return isDueSoon(c.due_date) && !isOverdue(c.due_date);
    if (filter === "no-date") return !c.due_date;
    return true;
  });

  // Group by board
  const byBoard = filtered.reduce<Record<string, { title: string; cards: DashboardCard[] }>>(
    (acc, c) => {
      if (!acc[c.board_id]) acc[c.board_id] = { title: c.board_title, cards: [] };
      acc[c.board_id].cards.push(c);
      return acc;
    },
    {}
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-[#032147] flex items-center justify-center text-white">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#032147] font-body">
      <header className="bg-[#032147] border-b border-white/10 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/boards")}
            className="text-white/60 hover:text-white text-sm transition-colors flex items-center gap-1"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m15 18-6-6 6-6" />
            </svg>
            Boards
          </button>
          <h1 className="text-white font-display text-lg font-bold">Project Studio</h1>
        </div>
        <div className="flex items-center gap-4">
          <button onClick={() => router.push("/profile")} className="text-white/60 hover:text-white text-sm transition-colors">Profile</button>
          <button onClick={() => { clearAuth(); router.push("/login"); }} className="text-white/60 hover:text-white text-sm transition-colors">Sign Out</button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        <div className="mb-8">
          <h2 className="text-white font-display text-3xl font-semibold">
            {user ? `${user.username}'s Dashboard` : "My Dashboard"}
          </h2>
          <p className="text-white/40 text-sm mt-1">Cards assigned to you across all boards</p>
        </div>

        {/* Summary stats */}
        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            <StatCard label="Boards" value={summary.board_count} accent="text-[#209dd7]" />
            <StatCard label="Assigned" value={summary.assigned_cards} />
            <StatCard label="Overdue" value={summary.overdue_cards} accent={summary.overdue_cards > 0 ? "text-red-400" : "text-white"} />
            <StatCard label="Due This Week" value={summary.due_this_week} accent={summary.due_this_week > 0 ? "text-amber-400" : "text-white"} />
          </div>
        )}

        {/* Filter tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {(["all", "overdue", "soon", "no-date"] as const).map((f) => {
            const labels = { all: "All", overdue: "Overdue", soon: "Due Soon", "no-date": "No Date" };
            const counts = {
              all: cards.length,
              overdue: cards.filter((c) => isOverdue(c.due_date)).length,
              soon: cards.filter((c) => isDueSoon(c.due_date) && !isOverdue(c.due_date)).length,
              "no-date": cards.filter((c) => !c.due_date).length,
            };
            return (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  filter === f
                    ? "bg-[#209dd7] text-white"
                    : "bg-white/5 text-white/50 hover:bg-white/10 hover:text-white"
                }`}
              >
                {labels[f]}
                {counts[f] > 0 && (
                  <span className={`ml-1.5 text-xs ${filter === f ? "text-white/70" : "text-white/30"}`}>
                    {counts[f]}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Cards grouped by board */}
        {Object.keys(byBoard).length === 0 ? (
          <div className="text-center py-20 text-white/30">
            <p className="text-lg">No assigned cards</p>
            <p className="text-sm mt-2">Cards assigned to you will appear here</p>
          </div>
        ) : (
          <div className="space-y-8">
            {Object.entries(byBoard).map(([boardId, group]) => (
              <div key={boardId}>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-white/60 text-xs font-semibold uppercase tracking-widest">{group.title}</h3>
                  <button
                    onClick={() => router.push(`/board?id=${boardId}`)}
                    className="text-[#209dd7] text-xs hover:text-white transition-colors"
                  >
                    Open board
                  </button>
                </div>
                <div className="space-y-2">
                  {group.cards.map((card) => (
                    <CardRow
                      key={card.id}
                      card={card}
                      onClick={() => router.push(`/board?id=${boardId}`)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
