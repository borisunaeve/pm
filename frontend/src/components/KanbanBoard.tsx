"use client";

import { useMemo, useState, useEffect } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
  type DragOverEvent,
} from "@dnd-kit/core";
import { SortableContext, horizontalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AIChatSidebar } from "@/components/AIChatSidebar";
import { moveCard, type BoardData, type Column } from "@/lib/kanban";
import * as api from "@/lib/api";
import { FilterBar, type FilterState } from "@/components/FilterBar";

type KanbanBoardProps = {
  boardId: string;
};

export const KanbanBoard = ({ boardId }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [boardTitle, setBoardTitle] = useState("");
  const [fetchError, setFetchError] = useState(false);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [activeColumnId, setActiveColumnId] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterState>({ search: "", priority: "", label: "" });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const fetchBoard = async () => {
    try {
      const data = await api.getBoard(boardId);
      setBoard(data);
      setFetchError(false);
    } catch {
      setFetchError(true);
    }
  };

  // Fetch board title separately from the boards list
  const fetchBoardTitle = async () => {
    try {
      const boards = await api.listBoards();
      const found = boards.find((b) => b.id === boardId);
      if (found) setBoardTitle(found.title);
    } catch {
      // silent
    }
  };

  useEffect(() => {
    fetchBoard();
    fetchBoardTitle();
  }, [boardId]);

  const cardsById = useMemo(() => board?.cards || {}, [board?.cards]);

  // Collect all unique labels across all cards for the filter dropdown
  const allLabels = useMemo(() => {
    if (!board) return [];
    const labels = new Set<string>();
    Object.values(board.cards).forEach((card) => {
      if (card.labels) card.labels.split(",").map((l) => l.trim()).filter(Boolean).forEach((l) => labels.add(l));
    });
    return Array.from(labels).sort();
  }, [board?.cards]);

  // Apply filter: returns set of card IDs that pass
  const visibleCardIds = useMemo(() => {
    if (!board || (!filter.search && !filter.priority && !filter.label)) return null; // null = show all
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

    // Column reorder
    if (board.columns.some((c) => c.id === activeId)) {
      const oldIdx = board.columns.findIndex((c) => c.id === activeId);
      const newIdx = board.columns.findIndex((c) => c.id === overId);
      if (oldIdx === -1 || newIdx === -1) return;
      const newColumns = arrayMove(board.columns, oldIdx, newIdx);
      setBoard((prev) => prev ? { ...prev, columns: newColumns } : prev);
      // Persist new order for each column
      newColumns.forEach((col, idx) => {
        api.updateColumn(col.id, col.title).catch(() => {});
        // We rely on order from the array index; backend doesn't have a reorder endpoint yet
        // so we just optimistically update client-side — a future iteration can add /api/columns/reorder
      });
      return;
    }

    // Card move
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
    await api.updateColumn(columnId, title);
  };

  const handleAddColumn = async (title: string) => {
    const newCol = await api.createColumn(boardId, title);
    setBoard((prev) =>
      prev
        ? {
            ...prev,
            columns: [...prev.columns, { id: newCol.id, title: newCol.title, cardIds: [] }],
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

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    const newCard = await api.createCard({
      title,
      details: details || "",
      column_id: columnId,
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
              <h1 className="font-display text-3xl font-semibold text-[var(--navy-dark)]">
                {boardTitle || "Board"}
              </h1>
              <p className="mt-1 text-sm text-[var(--gray-text)]">
                {board.columns.length} columns · {Object.keys(board.cards).length} cards
              </p>
            </div>
          </div>
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
                  onRename={handleRenameColumn}
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
