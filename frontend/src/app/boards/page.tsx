"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  listBoards,
  createBoard,
  updateBoard,
  deleteBoard,
  clearAuth,
  getUser,
  isLoggedIn,
  type BoardSummary,
} from "@/lib/api";

const BOARD_COLORS = [
  { value: "#209dd7", label: "Blue" },
  { value: "#753991", label: "Purple" },
  { value: "#ecad0a", label: "Yellow" },
  { value: "#e05c3a", label: "Orange" },
  { value: "#2ecc71", label: "Green" },
  { value: "#e74c3c", label: "Red" },
];

export default function BoardsPage() {
  const router = useRouter();
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newTemplate, setNewTemplate] = useState("");
  const [newColor, setNewColor] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editColor, setEditColor] = useState("");
  const user = getUser();

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    loadBoards();
  }, [router]);

  const loadBoards = async () => {
    try {
      const data = await listBoards();
      setBoards(data);
    } catch {
      // handled by api.ts
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const board = await createBoard(newTitle.trim(), newTemplate || undefined, "", newColor || undefined);
      setBoards((prev) => [...prev, board]);
      setNewTitle("");
      setNewTemplate("");
      setNewColor("");
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (board: BoardSummary) => {
    setEditingId(board.id);
    setEditTitle(board.title);
    setEditDescription(board.description ?? "");
    setEditColor(board.color ?? "");
  };

  const handleSaveEdit = async (boardId: string) => {
    if (!editTitle.trim()) return;
    await updateBoard(boardId, editTitle.trim(), editDescription, editColor || undefined);
    setBoards((prev) =>
      prev.map((b) =>
        b.id === boardId
          ? { ...b, title: editTitle.trim(), description: editDescription, color: editColor || null }
          : b
      )
    );
    setEditingId(null);
  };

  const handleDelete = async (boardId: string) => {
    if (!confirm("Delete this board and all its cards?")) return;
    await deleteBoard(boardId);
    setBoards((prev) => prev.filter((b) => b.id !== boardId));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#032147] flex items-center justify-center text-white">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#032147] font-body">
      {/* Header */}
      <header className="bg-[#032147] border-b border-white/10 px-8 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-white font-display text-xl font-bold">Project Studio</h1>
          {user && <p className="text-white/50 text-xs mt-0.5">Signed in as {user.username}</p>}
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/dashboard")}
            className="text-white/60 hover:text-white text-sm transition-colors"
          >
            My Tasks
          </button>
          <button
            onClick={() => router.push("/profile")}
            className="text-white/60 hover:text-white text-sm transition-colors"
          >
            Profile
          </button>
          <button
            onClick={() => { clearAuth(); router.push("/login"); }}
            className="text-white/60 hover:text-white text-sm transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-white font-display text-3xl font-semibold">My Boards</h2>
          <span className="text-white/40 text-sm">{boards.length} board{boards.length !== 1 ? "s" : ""}</span>
        </div>

        {/* Create board form */}
        <form onSubmit={handleCreate} className="flex flex-wrap gap-3 mb-8">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="New board name..."
            className="flex-1 min-w-48 rounded-xl bg-white/10 border border-white/20 text-white placeholder:text-white/30 px-4 py-3 text-sm focus:outline-none focus:border-[#209dd7] focus:ring-1 focus:ring-[#209dd7]"
          />
          <select
            value={newTemplate}
            onChange={(e) => setNewTemplate(e.target.value)}
            className="rounded-xl bg-white/10 border border-white/20 text-white/80 px-3 py-3 text-sm focus:outline-none focus:border-[#209dd7] cursor-pointer"
          >
            <option value="">Default (3 columns)</option>
            <option value="software">Software (5 cols)</option>
            <option value="marketing">Marketing (5 cols)</option>
            <option value="personal">Personal (3 cols)</option>
          </select>
          {/* Color picker */}
          <div className="flex items-center gap-1.5 bg-white/10 border border-white/20 rounded-xl px-3">
            {BOARD_COLORS.map((c) => (
              <button
                key={c.value}
                type="button"
                title={c.label}
                onClick={() => setNewColor(newColor === c.value ? "" : c.value)}
                className={`w-4 h-4 rounded-full transition-transform ${newColor === c.value ? "scale-125 ring-2 ring-white/50" : "hover:scale-110"}`}
                style={{ backgroundColor: c.value }}
              />
            ))}
          </div>
          <button
            type="submit"
            disabled={!newTitle.trim() || creating}
            className="bg-[#209dd7] text-white rounded-xl px-6 py-3 text-sm font-semibold hover:bg-[#1a87ba] transition-colors disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create Board"}
          </button>
        </form>

        {/* Boards grid */}
        {boards.length === 0 ? (
          <div className="text-center py-20 text-white/40">
            <p className="text-lg">No boards yet</p>
            <p className="text-sm mt-2">Create your first board above</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {boards.map((board) => (
              <div
                key={board.id}
                className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden hover:bg-white/8 transition-colors group"
              >
                {/* Color stripe */}
                {board.color && (
                  <div className="h-1.5 w-full" style={{ backgroundColor: board.color }} />
                )}
                <div className="p-5">
                  {editingId === board.id ? (
                    <div className="space-y-2">
                      <input
                        autoFocus
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveEdit(board.id);
                          if (e.key === "Escape") setEditingId(null);
                        }}
                        placeholder="Board title"
                        className="w-full bg-white/10 border border-white/30 text-white rounded-lg px-3 py-1.5 text-sm focus:outline-none"
                      />
                      <input
                        value={editDescription}
                        onChange={(e) => setEditDescription(e.target.value)}
                        placeholder="Description (optional)"
                        className="w-full bg-white/10 border border-white/20 text-white/80 rounded-lg px-3 py-1.5 text-xs focus:outline-none placeholder:text-white/30"
                      />
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1.5">
                          {BOARD_COLORS.map((c) => (
                            <button
                              key={c.value}
                              type="button"
                              title={c.label}
                              onClick={() => setEditColor(editColor === c.value ? "" : c.value)}
                              className={`w-3.5 h-3.5 rounded-full transition-transform ${editColor === c.value ? "scale-125 ring-2 ring-white/50" : "hover:scale-110"}`}
                              style={{ backgroundColor: c.value }}
                            />
                          ))}
                        </div>
                        <div className="flex-1" />
                        <button onClick={() => handleSaveEdit(board.id)} className="text-xs text-[#209dd7] hover:text-white transition-colors">Save</button>
                        <button onClick={() => setEditingId(null)} className="text-xs text-white/40 hover:text-white transition-colors">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <button onClick={() => router.push(`/board?id=${board.id}`)} className="block w-full text-left">
                      <h3 className="text-white font-display font-semibold text-lg group-hover:text-[#209dd7] transition-colors">
                        {board.title}
                      </h3>
                      {board.description && (
                        <p className="text-white/40 text-xs mt-1 line-clamp-1">{board.description}</p>
                      )}
                      <p className="text-white/30 text-xs mt-1">
                        {board.card_count} card{board.card_count !== 1 ? "s" : ""}
                        {board.member_count > 0 && ` · ${board.member_count} member${board.member_count !== 1 ? "s" : ""}`}
                        {board.created_at && ` · ${new Date(board.created_at).toLocaleDateString()}`}
                      </p>
                    </button>
                  )}

                  {editingId !== board.id && (
                    <div className="flex gap-3 mt-4 pt-3 border-t border-white/10">
                      <button
                        onClick={() => router.push(`/board?id=${board.id}`)}
                        className="flex-1 text-xs text-[#209dd7] hover:text-white transition-colors text-left font-medium"
                      >
                        Open
                      </button>
                      <button
                        onClick={() => startEdit(board)}
                        className="text-xs text-white/40 hover:text-white transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(board.id)}
                        className="text-xs text-white/40 hover:text-red-400 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
