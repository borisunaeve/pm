"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  listBoards,
  createBoard,
  updateBoard,
  deleteBoard,
  archiveBoard,
  restoreBoard,
  favoriteBoard,
  unfavoriteBoard,
  clearAuth,
  getUser,
  isLoggedIn,
  getTemplates,
  searchCards,
  getNotifications,
  getUnreadCount,
  getPersistentNotifications,
  markAllNotificationsRead,
  type BoardSummary,
  type BoardTemplate,
  type SearchResultCard,
  type NotificationItem,
} from "@/lib/api";

const BOARD_COLORS = [
  { value: "#209dd7", label: "Blue" },
  { value: "#753991", label: "Purple" },
  { value: "#ecad0a", label: "Yellow" },
  { value: "#e05c3a", label: "Orange" },
  { value: "#2ecc71", label: "Green" },
  { value: "#e74c3c", label: "Red" },
];

// ── Global Search Overlay ─────────────────────────────────────────────────────

function SearchOverlay({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResultCard[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  useEffect(() => {
    if (!q.trim()) { setResults([]); return; }
    const t = setTimeout(async () => {
      setSearching(true);
      try { setResults(await searchCards(q.trim())); }
      finally { setSearching(false); }
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-[#032147] border border-white/20 rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white/40 flex-shrink-0">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search cards across all boards..."
            className="flex-1 bg-transparent text-white placeholder:text-white/30 text-sm outline-none"
          />
          <kbd className="text-white/20 text-xs">Esc</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {searching && <p className="px-4 py-6 text-white/40 text-sm text-center">Searching...</p>}
          {!searching && results.length === 0 && q.trim() && (
            <p className="px-4 py-6 text-white/40 text-sm text-center italic">No results for &ldquo;{q}&rdquo;</p>
          )}
          {!searching && results.length === 0 && !q.trim() && (
            <p className="px-4 py-6 text-white/40 text-sm text-center">Type to search cards...</p>
          )}
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => { router.push(`/board?id=${r.board_id}`); onClose(); }}
              className="w-full text-left px-4 py-3 hover:bg-white/5 border-b border-white/5 last:border-0 transition-colors"
            >
              <p className="text-white text-sm font-medium">{r.title}</p>
              <p className="text-white/40 text-xs mt-0.5">{r.board_title} &bull; {r.column_title}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function BoardsPage() {
  const router = useRouter();
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showArchived, setShowArchived] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newTemplate, setNewTemplate] = useState("");
  const [templates, setTemplates] = useState<BoardTemplate[]>([]);
  const [newColor, setNewColor] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editColor, setEditColor] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [dueSoon, setDueSoon] = useState<NotificationItem[]>([]);
  const user = getUser();

  const loadBoards = useCallback(async (includeArchived = false) => {
    try {
      const data = await listBoards(includeArchived);
      setBoards(data);
    } catch { /* handled by api.ts */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    loadBoards(false);
    getTemplates().then(setTemplates).catch(() => {});
    getNotifications().then(setDueSoon).catch(() => {});
    getUnreadCount().then((d) => setUnreadCount(d.count)).catch(() => {});
  }, [router, loadBoards]);

  // Ctrl+K global search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || e.key === "/") {
        const tag = (e.target as HTMLElement).tagName;
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        e.preventDefault();
        setShowSearch(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const board = await createBoard(newTitle.trim(), newTemplate || undefined, "", newColor || undefined);
      setBoards((prev) => [...prev, board]);
      setNewTitle(""); setNewTemplate(""); setNewColor("");
    } finally { setCreating(false); }
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
    setBoards((prev) => prev.map((b) =>
      b.id === boardId ? { ...b, title: editTitle.trim(), description: editDescription, color: editColor || null } : b
    ));
    setEditingId(null);
  };

  const handleDelete = async (boardId: string) => {
    if (!confirm("Delete this board and all its cards?")) return;
    await deleteBoard(boardId);
    setBoards((prev) => prev.filter((b) => b.id !== boardId));
  };

  const handleArchive = async (boardId: string) => {
    await archiveBoard(boardId);
    if (!showArchived) {
      setBoards((prev) => prev.filter((b) => b.id !== boardId));
    } else {
      setBoards((prev) => prev.map((b) => b.id === boardId ? { ...b, archived: true } : b));
    }
  };

  const handleRestore = async (boardId: string) => {
    await restoreBoard(boardId);
    setBoards((prev) => prev.map((b) => b.id === boardId ? { ...b, archived: false } : b));
  };

  const handleToggleFavorite = async (board: BoardSummary) => {
    if (board.is_favorite) {
      await unfavoriteBoard(board.id);
    } else {
      await favoriteBoard(board.id);
    }
    setBoards((prev) => prev.map((b) => b.id === board.id ? { ...b, is_favorite: !b.is_favorite } : b));
  };

  const handleToggleArchived = async () => {
    const next = !showArchived;
    setShowArchived(next);
    setLoading(true);
    await loadBoards(next);
  };

  const openNotifs = async () => {
    setShowNotifs(true);
    const pn = await getPersistentNotifications().catch(() => []);
    setNotifications(pn as unknown as NotificationItem[]);
    if (unreadCount > 0) {
      await markAllNotificationsRead().catch(() => {});
      setUnreadCount(0);
    }
  };

  const activeBoards = boards.filter((b) => !b.archived);
  const archivedBoards = boards.filter((b) => b.archived);
  const favoriteBoards = activeBoards.filter((b) => b.is_favorite);
  const regularBoards = activeBoards.filter((b) => !b.is_favorite);

  if (loading) {
    return <div className="min-h-screen bg-[#032147] flex items-center justify-center text-white">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-[#032147] font-body">
      {showSearch && <SearchOverlay onClose={() => setShowSearch(false)} />}

      {/* Notifications panel */}
      {showNotifs && (
        <div className="fixed inset-0 z-40 flex items-start justify-end pt-16 pr-4" onClick={() => setShowNotifs(false)}>
          <div className="bg-[#032147] border border-white/20 rounded-2xl shadow-2xl w-80 max-h-[70vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <span className="text-white font-semibold text-sm">Notifications</span>
              <button onClick={() => setShowNotifs(false)} className="text-white/40 hover:text-white transition-colors text-xs">Close</button>
            </div>
            <div className="overflow-y-auto flex-1">
              {dueSoon.length === 0 && notifications.length === 0 ? (
                <p className="px-4 py-6 text-white/40 text-sm text-center italic">All caught up.</p>
              ) : (
                <>
                  {dueSoon.map((n) => (
                    <button
                      key={n.card_id}
                      onClick={() => { router.push(`/board?id=${n.board_id}`); setShowNotifs(false); }}
                      className="w-full text-left px-4 py-3 hover:bg-white/5 border-b border-white/5 last:border-0 transition-colors"
                    >
                      <p className={`text-xs font-semibold ${n.type === "overdue" ? "text-red-400" : "text-amber-400"}`}>
                        {n.type === "overdue" ? "Overdue" : "Due soon"} &mdash; {n.due_date}
                      </p>
                      <p className="text-white text-sm mt-0.5">{n.card_title}</p>
                      <p className="text-white/40 text-xs">{n.board_title}</p>
                    </button>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="bg-[#032147] border-b border-white/10 px-8 py-4 flex items-center justify-between sticky top-0 z-10">
        <div>
          <h1 className="text-white font-display text-xl font-bold">Project Studio</h1>
          {user && <p className="text-white/50 text-xs mt-0.5">Signed in as {user.username}</p>}
        </div>
        <div className="flex items-center gap-3">
          {/* Search */}
          <button
            onClick={() => setShowSearch(true)}
            title="Search cards (Ctrl+K)"
            className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-3 py-2 text-white/50 hover:text-white text-xs transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <span>Search</span>
            <kbd className="text-white/20">Ctrl+K</kbd>
          </button>

          {/* Notifications bell */}
          <button
            onClick={openNotifs}
            title="Notifications"
            className="relative text-white/60 hover:text-white transition-colors p-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
            {(unreadCount + dueSoon.length) > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center px-0.5">
                {unreadCount + dueSoon.length}
              </span>
            )}
          </button>

          <button onClick={() => router.push("/dashboard")} className="text-white/60 hover:text-white text-sm transition-colors">My Tasks</button>
          <button onClick={() => router.push("/activity")} className="text-white/60 hover:text-white text-sm transition-colors">Activity</button>
          <button onClick={() => router.push("/profile")} className="text-white/60 hover:text-white text-sm transition-colors">Profile</button>
          <button onClick={() => { clearAuth(); router.push("/login"); }} className="text-white/60 hover:text-white text-sm transition-colors">Sign Out</button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        {/* Due-soon alert */}
        {dueSoon.length > 0 && (
          <div className="mb-6 bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-400 flex-shrink-0">
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span className="text-amber-400 text-sm font-medium">
                {dueSoon.filter((n) => n.type === "overdue").length > 0 && (
                  <>{dueSoon.filter((n) => n.type === "overdue").length} overdue</>
                )}
                {dueSoon.filter((n) => n.type === "overdue").length > 0 && dueSoon.filter((n) => n.type === "due_soon").length > 0 && ", "}
                {dueSoon.filter((n) => n.type === "due_soon").length > 0 && (
                  <>{dueSoon.filter((n) => n.type === "due_soon").length} due soon</>
                )}
              </span>
            </div>
            <button onClick={openNotifs} className="text-amber-400 hover:text-amber-300 text-xs underline transition-colors">View</button>
          </div>
        )}

        <div className="flex items-center justify-between mb-8">
          <h2 className="text-white font-display text-3xl font-semibold">My Boards</h2>
          <div className="flex items-center gap-3">
            <span className="text-white/40 text-sm">{activeBoards.length} board{activeBoards.length !== 1 ? "s" : ""}</span>
            <button
              onClick={handleToggleArchived}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${showArchived ? "border-white/30 text-white/70 bg-white/5" : "border-white/10 text-white/40 hover:text-white/60"}`}
            >
              {showArchived ? "Hide archived" : "Show archived"}
            </button>
          </div>
        </div>

        {/* Create board form */}
        <form onSubmit={handleCreate} className="flex flex-wrap gap-3 mb-8">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="New board name..."
            className="flex-1 min-w-48 rounded-xl bg-white/10 border border-white/20 text-white placeholder:text-white/30 px-4 py-3 text-sm focus:outline-none focus:border-[#209dd7]"
          />
          <select
            value={newTemplate}
            onChange={(e) => setNewTemplate(e.target.value)}
            className="rounded-xl bg-white/10 border border-white/20 text-white/80 px-3 py-3 text-sm focus:outline-none focus:border-[#209dd7] cursor-pointer"
          >
            <option value="">Blank board</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>{t.name} ({t.columns.length} cols)</option>
            ))}
          </select>
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

        {/* Favorites section */}
        {favoriteBoards.length > 0 && (
          <div className="mb-6">
            <h3 className="text-white/50 text-xs uppercase tracking-widest font-semibold mb-3 flex items-center gap-1.5">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="#ecad0a" stroke="#ecad0a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
              Favorites
            </h3>
            <BoardGrid
              boards={favoriteBoards}
              editingId={editingId}
              editTitle={editTitle}
              editDescription={editDescription}
              editColor={editColor}
              setEditTitle={setEditTitle}
              setEditDescription={setEditDescription}
              setEditColor={setEditColor}
              onOpen={(id) => router.push(`/board?id=${id}`)}
              onEdit={startEdit}
              onSave={handleSaveEdit}
              onCancelEdit={() => setEditingId(null)}
              onDelete={handleDelete}
              onArchive={handleArchive}
              onToggleFavorite={handleToggleFavorite}
            />
          </div>
        )}

        {/* All active boards */}
        {regularBoards.length === 0 && favoriteBoards.length === 0 ? (
          <div className="text-center py-20 text-white/40">
            <p className="text-lg">No boards yet</p>
            <p className="text-sm mt-2">Create your first board above</p>
          </div>
        ) : regularBoards.length > 0 && (
          <div className={favoriteBoards.length > 0 ? "" : ""}>
            {favoriteBoards.length > 0 && (
              <h3 className="text-white/50 text-xs uppercase tracking-widest font-semibold mb-3">All Boards</h3>
            )}
            <BoardGrid
              boards={regularBoards}
              editingId={editingId}
              editTitle={editTitle}
              editDescription={editDescription}
              editColor={editColor}
              setEditTitle={setEditTitle}
              setEditDescription={setEditDescription}
              setEditColor={setEditColor}
              onOpen={(id) => router.push(`/board?id=${id}`)}
              onEdit={startEdit}
              onSave={handleSaveEdit}
              onCancelEdit={() => setEditingId(null)}
              onDelete={handleDelete}
              onArchive={handleArchive}
              onToggleFavorite={handleToggleFavorite}
            />
          </div>
        )}

        {/* Archived boards */}
        {showArchived && archivedBoards.length > 0 && (
          <div className="mt-10">
            <h3 className="text-white/40 text-xs uppercase tracking-widest font-semibold mb-3">Archived</h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {archivedBoards.map((board) => (
                <div key={board.id} className="bg-white/3 border border-white/10 rounded-2xl overflow-hidden opacity-60">
                  {board.color && <div className="h-1.5 w-full" style={{ backgroundColor: board.color }} />}
                  <div className="p-5">
                    <h3 className="text-white/70 font-display font-semibold text-lg">{board.title}</h3>
                    {board.description && <p className="text-white/30 text-xs mt-1 line-clamp-1">{board.description}</p>}
                    <div className="flex gap-3 mt-4 pt-3 border-t border-white/10">
                      <button
                        onClick={() => handleRestore(board.id)}
                        className="text-xs text-[#209dd7] hover:text-white transition-colors font-medium"
                      >
                        Restore
                      </button>
                      <button
                        onClick={() => handleDelete(board.id)}
                        className="text-xs text-white/30 hover:text-red-400 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {showArchived && archivedBoards.length === 0 && (
          <div className="mt-6 text-center text-white/30 text-sm italic">No archived boards.</div>
        )}
      </main>
    </div>
  );
}

// ── Board Grid Component ───────────────────────────────────────────────────────

type BoardGridProps = {
  boards: BoardSummary[];
  editingId: string | null;
  editTitle: string;
  editDescription: string;
  editColor: string;
  setEditTitle: (v: string) => void;
  setEditDescription: (v: string) => void;
  setEditColor: (v: string) => void;
  onOpen: (id: string) => void;
  onEdit: (board: BoardSummary) => void;
  onSave: (id: string) => void;
  onCancelEdit: () => void;
  onDelete: (id: string) => void;
  onArchive: (id: string) => void;
  onToggleFavorite: (board: BoardSummary) => void;
};

function BoardGrid({
  boards, editingId, editTitle, editDescription, editColor,
  setEditTitle, setEditDescription, setEditColor,
  onOpen, onEdit, onSave, onCancelEdit, onDelete, onArchive, onToggleFavorite,
}: BoardGridProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {boards.map((board) => (
        <div
          key={board.id}
          className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden hover:bg-white/8 transition-colors group relative"
        >
          {board.color && <div className="h-1.5 w-full" style={{ backgroundColor: board.color }} />}

          {/* Favorite star */}
          <button
            onClick={() => onToggleFavorite(board)}
            title={board.is_favorite ? "Remove from favorites" : "Add to favorites"}
            className={`absolute top-3 right-3 transition-colors z-10 ${board.is_favorite ? "text-[#ecad0a]" : "text-white/20 hover:text-[#ecad0a] opacity-0 group-hover:opacity-100"}`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill={board.is_favorite ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
          </button>

          <div className="p-5">
            {editingId === board.id ? (
              <div className="space-y-2">
                <input
                  autoFocus
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onSave(board.id);
                    if (e.key === "Escape") onCancelEdit();
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
                  <button onClick={() => onSave(board.id)} className="text-xs text-[#209dd7] hover:text-white transition-colors">Save</button>
                  <button onClick={onCancelEdit} className="text-xs text-white/40 hover:text-white transition-colors">Cancel</button>
                </div>
              </div>
            ) : (
              <button onClick={() => onOpen(board.id)} className="block w-full text-left pr-6">
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
                <button onClick={() => onOpen(board.id)} className="flex-1 text-xs text-[#209dd7] hover:text-white transition-colors text-left font-medium">Open</button>
                <button onClick={() => onEdit(board)} className="text-xs text-white/40 hover:text-white transition-colors">Edit</button>
                <button onClick={() => onArchive(board.id)} className="text-xs text-white/40 hover:text-amber-400 transition-colors">Archive</button>
                <button onClick={() => onDelete(board.id)} className="text-xs text-white/40 hover:text-red-400 transition-colors">Delete</button>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
