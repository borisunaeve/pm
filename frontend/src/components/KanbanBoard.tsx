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

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [fetchError, setFetchError] = useState(false);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const fetchBoard = async () => {
    try {
      const response = await fetch("/api/board");
      if (response.ok) {
        const data = await response.json();
        setBoard(data);
        setFetchError(false);
      } else {
        setFetchError(true);
      }
    } catch (error) {
      console.error("Failed to fetch board data:", error);
      setFetchError(true);
    }
  };

  useEffect(() => {
    fetchBoard();
  }, []);

  const cardsById = useMemo(() => board?.cards || {}, [board?.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id || !board) {
      return;
    }

    const newColumns = moveCard(board.columns, active.id as string, over.id as string);

    // Optimistic UI update
    setBoard((prev) => prev ? { ...prev, columns: newColumns } : prev);

    // Find new column and order to sync with backend
    const activeIdStr = active.id as string;
    let newColId = "";
    let newOrder = 0;

    newColumns.forEach((col) => {
      const idx = col.cardIds.indexOf(activeIdStr);
      if (idx !== -1) {
        newColId = col.id;
        newOrder = idx;
      }
    });

    try {
      await fetch(`/api/cards/${activeIdStr}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          column_id: newColId,
          order: newOrder,
        }),
      });
    } catch (e) {
      console.error("Failed to move card", e);
      // In a real app we'd revert the optimistic update here on fail
    }
  };

  const handleRenameColumn = async (columnId: string, title: string) => {
    setBoard((prev) => prev ? {
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    } : null);

    await fetch(`/api/columns/${columnId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    const response = await fetch("/api/cards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        details: details || "No details yet.",
        column_id: columnId,
      }),
    });

    if (response.ok) {
      const newCard = await response.json();
      setBoard((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          cards: {
            ...prev.cards,
            [newCard.id]: newCard,
          },
          columns: prev.columns.map((column) =>
            column.id === columnId
              ? { ...column, cardIds: [...column.cardIds, newCard.id] }
              : column
          ),
        };
      });
    }
  };

  const handleDeleteCard = async (columnId: string, cardId: string) => {
    await fetch(`/api/cards/${cardId}`, { method: "DELETE" });

    setBoard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
            : column
        ),
      };
    });
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

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column: Column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <AIChatSidebar onRefreshBoard={fetchBoard} />

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column: Column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
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
