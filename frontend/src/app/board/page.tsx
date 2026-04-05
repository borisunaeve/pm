"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { KanbanBoard } from "@/components/KanbanBoard";
import { clearAuth, getUser, isLoggedIn } from "@/lib/api";

function BoardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const boardId = searchParams?.get("id");
  const user = getUser();

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
    } else if (!boardId) {
      router.replace("/boards");
    }
  }, [router, boardId]);

  if (!boardId) return null;

  return (
    <div className="min-h-screen">
      <header className="bg-[#032147] text-white px-6 py-3 flex justify-between items-center z-10 relative">
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
          <span className="text-white/30">|</span>
          <h1 className="text-sm font-display font-semibold">Project Studio</h1>
        </div>
        <div className="flex items-center gap-4">
          {user && <span className="text-white/50 text-xs">{user.username}</span>}
          <button
            onClick={() => { clearAuth(); router.push("/login"); }}
            className="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded transition-colors text-xs"
          >
            Sign Out
          </button>
        </div>
      </header>
      <main className="h-[calc(100vh-52px)]">
        <KanbanBoard boardId={boardId} />
      </main>
    </div>
  );
}

export default function BoardPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <BoardContent />
    </Suspense>
  );
}
