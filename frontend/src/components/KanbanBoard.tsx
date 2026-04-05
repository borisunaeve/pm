"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { SortableContext, horizontalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AIChatSidebar } from "@/components/AIChatSidebar";
import { ShareDialog } from "@/components/ShareDialog";
import { moveCard, type BoardData, type Column } from "@/lib/kanban";
import * as api from "@/lib/api";
import { FilterBar, type FilterState } from "@/components/FilterBar";
import clsx from "clsx";

type KanbanBoardProps = {
  boardId: string;
};

// ── Activity Feed ──────────────────────────────────────────────────────────────

function ActivityFeed({ boardId, onClose }: { boardId: string; onClose: () => void }) {
  const [entries, setEntries] = useState<api.ActivityEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getBoardActivity(boardId, 30).then(setEntries).finally(() => setLoading(false));
  }, [boardId]);

  const ACTION_ICONS: Record<string, string> = {
    created: "+",
    updated: "~",
    deleted: "-",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-end p-4 pointer-events-none"
    >
      <div className="pointer-events-auto w-80 rounded-2xl border border-[var(--stroke)] bg-white shadow-2xl flex flex-col max-h-[500px]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <h3 className="font-display font-semibold text-[var(--navy-dark)] text-sm">Activity</h3>
          <button type="button" onClick={onClose} className="text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-xs">
            Close
          </button>
        </div>
        <div className="overflow-y-auto flex-1 p-3 space-y-2">
          {loading && <p className="text-xs text-[var(--gray-text)]">Loading...</p>}
          {!loading && entries.length === 0 && (
            <p className="text-xs text-[var(--gray-text)] italic">No activity yet.</p>
          )}
          {entries.map((e) => (
            <div key={e.id} className="flex gap-2 items-start">
              <span className={clsx(
                "flex-shrink-0 h-5 w-5 rounded-full text-[10px] font-bold flex items-center justify-center",
                e.action === "created" && "bg-green-100 text-green-700",
                e.action === "deleted" && "bg-red-100 text-red-700",
                e.action === "updated" && "bg-blue-100 text-blue-700",
              )}>
                {ACTION_ICONS[e.action] ?? "·"}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-[var(--navy-dark)]">
                  <span className="font-semibold">{e.username}</span>
                  {" "}{e.action} {e.entity_type}
                  {e.entity_title && <span className="italic"> "{e.entity_title}"</span>}
                </p>
                <p className="text-[10px] text-[var(--gray-text)]">
                  {new Date(e.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Dark mode hook ─────────────────────────────────────────────────────────────

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("pm_dark") === "1";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("pm_dark", dark ? "1" : "0");
  }, [dark]);

  return [dark, setDark] as const;
}

// ── Stats Panel ────────────────────────────────────────────────────────────────

function StatsPanel({ board }: { board: BoardData }) {
  const cards = Object.values(board.cards);
  const totalCards = cards.length;
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const overdueCount = cards.filter((c) => {
    if (!c.due_date) return false;
    const due = new Date(c.due_date + "T00:00:00");
    return due < today;
  }).length;

  const highPrioCount = cards.filter((c) => c.priority === "high").length;

  const doneCols = board.columns.filter((c) =>
    c.title.toLowerCase().includes("done") || c.title.toLowerCase().includes("complete")
  );
  const doneCount = doneCols.reduce((s, c) => s + c.cardIds.length, 0);

  const stats = [
    { label: "Total cards", value: totalCards, color: "text-[var(--primary-blue)]" },
    { label: "High priority", value: highPrioCount, color: "text-red-500" },
    { label: "Overdue", value: overdueCount, color: overdueCount > 0 ? "text-red-500" : "text-[var(--gray-text)]" },
    { label: "Done", value: doneCount, color: "text-green-600" },
    { label: "Columns", value: board.columns.length, color: "text-[var(--purple-sec)]" },
  ];

  return (
    <div className="flex flex-wrap gap-3">
      {stats.map((s) => (
        <div key={s.label} className="rounded-2xl bg-white/70 border border-[var(--stroke)] px-4 py-2.5 flex flex-col items-center min-w-[80px]">
          <span className={clsx("text-2xl font-display font-bold", s.color)}>{s.value}</span>
          <span className="text-[10px] uppercase tracking-wide text-[var(--gray-text)] font-semibold mt-0.5">{s.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Keyboard shortcuts help overlay ───────────────────────────────────────────

const SHORTCUTS = [
  { key: "/", desc: "Focus search" },
  { key: "n", desc: "Add card (first column)" },
  { key: "Esc", desc: "Close modal / clear focus" },
  { key: "?", desc: "Show / hide shortcuts" },
];

function ShortcutsHelp({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-display font-semibold text-[var(--navy-dark)] text-lg mb-4">Keyboard Shortcuts</h3>
        <ul className="space-y-2">
          {SHORTCUTS.map((s) => (
            <li key={s.key} className="flex items-center justify-between">
              <span className="text-sm text-[var(--navy-dark)]">{s.desc}</span>
              <kbd className="rounded-lg border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-mono text-[var(--navy-dark)]">{s.key}</kbd>
            </li>
          ))}
        </ul>
        <button type="button" onClick={onClose} className="mt-4 w-full rounded-xl border border-gray-200 py-2 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition">
          Close
        </button>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export const KanbanBoard = ({ boardId }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [boardTitle, setBoardTitle] = useState("");
  const [fetchError, setFetchError] = useState(false);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [activeColumnId, setActiveColumnId] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterState>({ search: "", priority: "", label: "" });
  const [showSharing, setShowSharing] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const [dark, setDark] = useDarkMode();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const fetchBoard = useCallback(async () => {
    try {
      const data = await api.getBoard(boardId);
      setBoard(data);
      setFetchError(false);
    } catch {
      setFetchError(true);
    }
  }, [boardId]);

  const fetchBoardTitle = useCallback(async () => {
    try {
      const boards = await api.listBoards();
      const found = boards.find((b) => b.id === boardId);
      if (found) setBoardTitle(found.title);
    } catch {
      // silent
    }
  }, [boardId]);

  useEffect(() => {
    fetchBoard();
    fetchBoardTitle();
  }, [fetchBoard, fetchBoardTitle]);

  // ── Keyboard shortcuts ───────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      const inInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

      if (e.key === "?" && !inInput) {
        setShowShortcuts((v) => !v);
        return;
      }
      if (e.key === "Escape") {
        setShowShortcuts(false);
        setShowSharing(false);
        setShowActivity(false);
        return;
      }
      if (e.key === "/" && !inInput) {
        e.preventDefault();
        document.getElementById("filter-search")?.focus();
        return;
      }
      if (e.key === "n" && !inInput && board) {
        // Open new card form in first column — trigger click on first "+ Add Card" button
        const btn = document.querySelector<HTMLButtonElement>("[data-add-card-btn]");
        btn?.click();
        return;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [board]);

  const cardsById = useMemo(() => board?.cards || {}, [board?.cards]);

  const allLabels = useMemo(() => {
    if (!board) return [];
    const labels = new Set<string>();
    Object.values(board.cards).forEach((card) => {
      if (card.labels) card.labels.split(",").map((l) => l.trim()).filter(Boolean).forEach((l) => labels.add(l));
    });
    return Array.from(labels).sort();
  }, [board?.cards]);

  const visibleCardIds = useMemo(() => {
    if (!board || (!filter.search && !filter.priority && !filter.label)) return null;
    const q = filter.search.toLowerCase();
    return new Set(
      Object.values(board.cards)
        .filter((card) => {
          if (q && !card.title.toLowerCase().includes(q) && !(card.details || "").toLowerCase().includes(q)) return false;
          if (filter.priority && card.priority !== filter.priority) return false;
          if (filter.label) {
            const cardLabels = (card.labels || "").split(",").map((l) => l.trim());
            if (!cardLabels.includes(filter.label)) return false;
          }
          return true;
        })
        .map((c) => c.id)
    );
  }, [board?.cards, filter]);

  const handleDragStart = (event: DragStartEvent) => {
    const id = event.active.id as string;
    if (board?.columns.some((c) => c.id === id)) {
      setActiveColumnId(id);
    } else {
      setActiveCardId(id);
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    setActiveColumnId(null);

    if (!over || active.id === over.id || !board) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    if (board.columns.some((c) => c.id === activeId)) {
      const oldIdx = board.columns.findIndex((c) => c.id === activeId);
      const newIdx = board.columns.findIndex((c) => c.id === overId);
      if (oldIdx === -1 || newIdx === -1) return;
      const newColumns = arrayMove(board.columns, oldIdx, newIdx);
      setBoard((prev) => prev ? { ...prev, columns: newColumns } : prev);
      api.reorderColumns(newColumns.map((c) => c.id)).catch(() => fetchBoard());
      return;
    }

    const newColumns = moveCard(board.columns, activeId, overId);
    setBoard((prev) => prev ? { ...prev, columns: newColumns } : prev);

    let newColId = "";
    let newOrder = 0;
    newColumns.forEach((col) => {
      const idx = col.cardIds.indexOf(activeId);
      if (idx !== -1) { newColId = col.id; newOrder = idx; }
    });

    try {
      await api.updateCard(activeId, { column_id: newColId, order: newOrder });
    } catch {
      fetchBoard();
    }
  };

  const handleRenameColumn = async (columnId: string, title: string) => {
    setBoard((prev) =>
      prev ? { ...prev, columns: prev.columns.map((c) => c.id === columnId ? { ...c, title } : c) } : null
    );
    const col = board?.columns.find((c) => c.id === columnId);
    await api.updateColumn(columnId, title, col?.wip_limit);
  };

  const handleSetWipLimit = async (columnId: string, title: string, wip_limit: number | null) => {
    setBoard((prev) =>
      prev ? { ...prev, columns: prev.columns.map((c) => c.id === columnId ? { ...c, wip_limit } : c) } : null
    );
    await api.updateColumn(columnId, title, wip_limit);
  };

  const handleAddColumn = async (title: string) => {
    const newCol = await api.createColumn(boardId, title);
    setBoard((prev) =>
      prev
        ? {
            ...prev,
            columns: [...prev.columns, { id: newCol.id, title: newCol.title, cardIds: [], wip_limit: null }],
          }
        : null
    );
  };

  const handleDeleteColumn = async (columnId: string) => {
    if (!confirm("Delete this column and all its cards?")) return;
    await api.deleteColumn(columnId);
    setBoard((prev) =>
      prev
        ? {
            ...prev,
            columns: prev.columns.filter((c) => c.id !== columnId),
            cards: Object.fromEntries(
              Object.entries(prev.cards).filter(([id]) => {
                const col = prev.columns.find((c) => c.id === columnId);
                return !col?.cardIds.includes(id);
              })
            ),
          }
        : null
    );
  };

  const handleAddCard = async (columnId: string, title: string, details: string, priority = "medium", due_date = "", labels = "") => {
    const newCard = await api.createCard({
      title,
      details: details || "",
      column_id: columnId,
      priority,
      due_date: due_date || undefined,
      labels: labels || "",
    });
    setBoard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: { ...prev.cards, [newCard.id]: newCard },
        columns: prev.columns.map((col) =>
          col.id === columnId ? { ...col, cardIds: [...col.cardIds, newCard.id] } : col
        ),
      };
    });
  };

  const handleDeleteCard = async (columnId: string, cardId: string) => {
    await api.deleteCard(cardId);
    setBoard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: Object.fromEntries(Object.entries(prev.cards).filter(([id]) => id !== cardId)),
        columns: prev.columns.map((col) =>
          col.id === columnId ? { ...col, cardIds: col.cardIds.filter((id) => id !== cardId) } : col
        ),
      };
    });
  };

  const handleUpdateCard = async (
    cardId: string,
    columnId: string,
    order: number,
    updates: Partial<api.Card>
  ) => {
    await api.updateCard(cardId, { column_id: columnId, order, ...updates });
    setBoard((prev) =>
      prev
        ? { ...prev, cards: { ...prev.cards, [cardId]: { ...prev.cards[cardId], ...updates } } }
        : null
    );
  };

  if (fetchError) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen gap-4 text-[var(--gray-text)]">
        <p>Could not load the board. Is the server running?</p>
        <button
          onClick={fetchBoard}
          className="rounded-full bg-[var(--primary-blue)] px-4 py-2 text-sm font-semibold text-white hover:brightness-110 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!board) {
    return (
      <div className="flex justify-center items-center min-h-screen text-[var(--gray-text)]">
        Loading Kanban Board...
      </div>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1600px] flex-col gap-8 px-6 pb-16 pt-8">
        <header className="flex flex-col gap-4 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-6 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <a href="/boards" className="text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition">
                  Boards
                </a>
                <span className="text-[var(--gray-text)]">/</span>
                <h1 className="font-display text-3xl font-semibold text-[var(--navy-dark)]">
                  {boardTitle || "Board"}
                </h1>
              </div>
            </div>

            {/* Header action buttons */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Export */}
              <div className="relative group">
                <button className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-semibold text-[var(--navy-dark)] hover:bg-gray-50 transition flex items-center gap-1.5">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  Export
                </button>
                <div className="absolute right-0 top-full mt-1 hidden group-hover:flex flex-col bg-white rounded-xl border border-[var(--stroke)] shadow-lg overflow-hidden z-10 min-w-[100px]">
                  <button
                    type="button"
                    onClick={() => api.exportBoard(boardId, "json")}
                    className="px-4 py-2 text-sm text-[var(--navy-dark)] hover:bg-gray-50 text-left transition"
                  >
                    JSON
                  </button>
                  <button
                    type="button"
                    onClick={() => api.exportBoard(boardId, "csv")}
                    className="px-4 py-2 text-sm text-[var(--navy-dark)] hover:bg-gray-50 text-left transition"
                  >
                    CSV
                  </button>
                </div>
              </div>

              {/* Activity */}
              <button
                type="button"
                onClick={() => setShowActivity((v) => !v)}
                className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-semibold text-[var(--navy-dark)] hover:bg-gray-50 transition flex items-center gap-1.5"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
                Activity
              </button>

              {/* Share */}
              <button
                type="button"
                onClick={() => setShowSharing(true)}
                className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-semibold text-[var(--navy-dark)] hover:bg-gray-50 transition flex items-center gap-1.5"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="18" cy="5" r="3"></circle>
                  <circle cx="6" cy="12" r="3"></circle>
                  <circle cx="18" cy="19" r="3"></circle>
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                </svg>
                Share
              </button>

              {/* Shortcuts */}
              <button
                type="button"
                onClick={() => setShowShortcuts(true)}
                title="Keyboard shortcuts (?)"
                className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-semibold text-[var(--navy-dark)] hover:bg-gray-50 transition"
              >
                ?
              </button>

              {/* Dark mode toggle */}
              <button
                type="button"
                onClick={() => setDark((d) => !d)}
                title={dark ? "Light mode" : "Dark mode"}
                className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] hover:bg-gray-50 transition"
              >
                {dark ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="5"></circle>
                    <line x1="12" y1="1" x2="12" y2="3"></line>
                    <line x1="12" y1="21" x2="12" y2="23"></line>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                    <line x1="1" y1="12" x2="3" y2="12"></line>
                    <line x1="21" y1="12" x2="23" y2="12"></line>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Stats */}
          <StatsPanel board={board} />

          <FilterBar filter={filter} onChange={setFilter} allLabels={allLabels} />
        </header>

        <AIChatSidebar boardId={boardId} onRefreshBoard={fetchBoard} />

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={board.columns.map((c) => c.id)} strategy={horizontalListSortingStrategy}>
          <section className="flex gap-4 overflow-x-auto pb-4">
            {board.columns.map((column: Column) => (
              <div key={column.id} className="flex-shrink-0 w-72">
                <KanbanColumn
                  column={column}
                  cards={column.cardIds.map((id) => board.cards[id]).filter(Boolean).filter((c) => !visibleCardIds || visibleCardIds.has(c.id))}
                  boardId={boardId}
                  onRename={handleRenameColumn}
                  onSetWipLimit={handleSetWipLimit}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onDeleteColumn={handleDeleteColumn}
                  onUpdateCard={handleUpdateCard}
                />
              </div>
            ))}
            <div className="flex-shrink-0 w-72">
              <AddColumnButton onAdd={handleAddColumn} />
            </div>
          </section>
          </SortableContext>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : activeColumnId && board.columns.find((c) => c.id === activeColumnId) ? (
              <div className="w-72 opacity-80 rotate-1">
                <div className="rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-4 shadow-2xl">
                  <p className="font-display font-semibold text-[var(--navy-dark)]">
                    {board.columns.find((c) => c.id === activeColumnId)?.title}
                  </p>
                </div>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>

      {showSharing && <ShareDialog boardId={boardId} onClose={() => setShowSharing(false)} />}
      {showShortcuts && <ShortcutsHelp onClose={() => setShowShortcuts(false)} />}
      {showActivity && <ActivityFeed boardId={boardId} onClose={() => setShowActivity(false)} />}
    </div>
  );
};

const AddColumnButton = ({ onAdd }: { onAdd: (title: string) => Promise<void> }) => {
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await onAdd(title.trim());
    setTitle("");
    setAdding(false);
  };

  if (adding) {
    return (
      <div className="rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Column name..."
            className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="flex-1 rounded-xl bg-[var(--primary-blue)] py-2 text-sm font-semibold text-white hover:brightness-110"
            >
              Add
            </button>
            <button
              type="button"
              onClick={() => { setAdding(false); setTitle(""); }}
              className="rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <button
      onClick={() => setAdding(true)}
      className="w-full rounded-3xl border-2 border-dashed border-[var(--stroke)] py-8 text-sm font-semibold text-[var(--gray-text)] hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)] transition-colors"
    >
      + Add Column
    </button>
  );
};
