"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { KanbanBoard } from "@/components/KanbanBoard";

export default function Home() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const auth = localStorage.getItem("pm_auth");
    if (!auth) {
      router.push("/login");
    } else {
      setIsAuthenticated(true);
    }
  }, [router]);

  if (!isAuthenticated) {
    return null; // or a loading spinner
  }

  return (
    <div className="relative min-h-screen">
      <header className="bg-[#032147] text-white p-4 flex justify-between items-center z-10 relative">
        <h1 className="text-xl font-display font-bold">Kanban Studio MVP</h1>
        <button
          onClick={() => {
            localStorage.removeItem("pm_auth");
            router.push("/login");
          }}
          className="bg-white/10 hover:bg-white/20 px-4 py-2 rounded transition-colors text-sm"
        >
          Logout
        </button>
      </header>
      <main className="h-[calc(100vh-60px)]">
        <KanbanBoard />
      </main>
    </div>
  );
}
