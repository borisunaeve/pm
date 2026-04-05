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
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AIChatSidebar } from "@/components/AIChatSidebar";
import { moveCard, type BoardData, type Column } from "@/lib/kanban";
import * as api from "@/lib/api";

type KanbanBoardProps = {
  boardId: string;
};

export const KanbanBoard = ({ boardId }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [boardTitle, setBoardTitle] = useState("");
  const [fetchError, setFetchError] = useState(false);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

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

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id || !board) return;

    const newColumns = moveCard(board.columns, active.id as string, over.id as string);
    setBoard((prev) => prev ? { ...prev, columns: newColumns } : prev);

    const activeIdStr = active.id as string;
    let newColId = "";
    let newOrder = 0;
    newColumns.forEach((col) => {
      const idx = col.cardIds.indexOf(activeIdStr);
      if (idx !== -1) { newColId = col.id; newOrder = idx; }
    });

    try {
      await api.updateCard(activeIdStr, { column_id: newColId, order: newOrder });
    } catch {
      fetchBoard(); // revert on error
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
          <div className="flex flex-wrap items-center gap-3">
            {board.columns.map((column: Column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <AIChatSidebar boardId={boardId} onRefreshBoard={fetchBoard} />

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="flex gap-4 overflow-x-auto pb-4">
            {board.columns.map((column: Column) => (
              <div key={column.id} className="flex-shrink-0 w-72">
                <KanbanColumn
                  column={column}
                  cards={column.cardIds.map((id) => board.cards[id]).filter(Boolean)}
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
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
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
