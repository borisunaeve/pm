"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMyActivity, isLoggedIn, clearAuth, type UserActivityItem } from "@/lib/api";

export default function ActivityPage() {
  const router = useRouter();
  const [items, setItems] = useState<UserActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    getMyActivity(100).then(setItems).finally(() => setLoading(false));
  }, [router]);

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  };

  const actionLabel = (action: string) => {
    switch (action) {
      case "card_created": return "created card";
      case "card_moved": return "moved card";
      case "card_updated": return "updated card";
      case "card_deleted": return "deleted card";
      case "column_created": return "created column";
      case "column_deleted": return "deleted column";
      case "member_added": return "added member";
      case "member_removed": return "removed member";
      default: return action.replace(/_/g, " ");
    }
  };

  const actionColor = (action: string) => {
    if (action.includes("created")) return "text-green-400";
    if (action.includes("deleted")) return "text-red-400";
    if (action.includes("moved")) return "text-blue-400";
    return "text-white/60";
  };

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
        <button
          onClick={() => { clearAuth(); router.push("/login"); }}
          className="text-white/60 hover:text-white text-sm transition-colors"
        >
          Sign Out
        </button>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-10">
        <h2 className="text-white font-display text-3xl font-semibold mb-8">Activity</h2>

        {loading ? (
          <p className="text-white/40 text-sm">Loading activity...</p>
        ) : items.length === 0 ? (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-10 text-center">
            <p className="text-white/40 text-sm">No activity yet. Start by creating cards and moving them around.</p>
          </div>
        ) : (
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-px bg-white/10" />
            <ul className="space-y-1">
              {items.map((item) => (
                <li key={item.id} className="relative flex gap-4 pl-10 py-2.5 group">
                  <div className="absolute left-3 top-4 w-2 h-2 rounded-full bg-white/20 group-hover:bg-[#209dd7] transition-colors" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <span className={`text-sm font-medium ${actionColor(item.action)}`}>
                          {actionLabel(item.action)}
                        </span>
                        {item.entity_title && (
                          <span className="text-sm text-white ml-1">
                            &ldquo;{item.entity_title}&rdquo;
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-white/30 whitespace-nowrap flex-shrink-0">{formatTime(item.created_at)}</span>
                    </div>
                    <button
                      onClick={() => router.push(`/board?id=${item.board_id}`)}
                      className="text-xs text-white/40 hover:text-[#209dd7] transition-colors mt-0.5"
                    >
                      {item.board_title}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  );
}
