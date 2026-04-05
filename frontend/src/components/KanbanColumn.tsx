"use client";

import { useState, useEffect } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  boardId: string;
  onRename: (columnId: string, title: string) => void;
  onSetWipLimit: (columnId: string, title: string, wip_limit: number | null) => void;
  onAddCard: (columnId: string, title: string, details: string, priority: string, due_date: string, labels: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  onDeleteColumn: (columnId: string) => void;
  onUpdateCard: (
    cardId: string,
    columnId: string,
    order: number,
    updates: Partial<Card>
  ) => Promise<void>;
};

export const KanbanColumn = ({
  column,
  cards,
  boardId,
  onRename,
  onSetWipLimit,
  onAddCard,
  onDeleteCard,
  onDeleteColumn,
  onUpdateCard,
}: KanbanColumnProps) => {
  const { setNodeRef: setDropRef, isOver } = useDroppable({ id: column.id });
  const {
    attributes,
    listeners,
    setNodeRef: setSortRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: column.id });
  const [localTitle, setLocalTitle] = useState(column.title);
  const [editingWip, setEditingWip] = useState(false);
  const [wipInput, setWipInput] = useState(column.wip_limit != null ? String(column.wip_limit) : "");

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const setNodeRef = (node: HTMLElement | null) => {
    setDropRef(node);
    setSortRef(node);
  };

  useEffect(() => {
    setLocalTitle(column.title);
  }, [column.title]);

  useEffect(() => {
    setWipInput(column.wip_limit != null ? String(column.wip_limit) : "");
  }, [column.wip_limit]);

  const wipExceeded = column.wip_limit != null && cards.length > column.wip_limit;

  const handleWipSave = () => {
    const parsed = wipInput.trim() === "" ? null : parseInt(wipInput, 10);
    const limit = parsed !== null && !isNaN(parsed) && parsed > 0 ? parsed : null;
    onSetWipLimit(column.id, localTitle, limit);
    setEditingWip(false);
  };

  return (
    <section
      ref={setNodeRef}
      style={style}
      className={clsx(
        "flex min-h-[520px] flex-col rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-4 shadow-[var(--shadow)] transition",
        isOver && "ring-2 ring-[var(--accent-yellow)]",
        isDragging && "opacity-50",
        wipExceeded && "ring-2 ring-red-400"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            {/* Drag handle for column */}
            <div
              {...attributes}
              {...listeners}
              className="h-2 w-8 rounded-full bg-[var(--accent-yellow)] flex-shrink-0 cursor-grab active:cursor-grabbing"
              title="Drag to reorder column"
            />
            <span className={clsx(
              "text-xs font-semibold uppercase tracking-[0.2em]",
              wipExceeded ? "text-red-500" : "text-[var(--gray-text)]"
            )}>
              {cards.length}{column.wip_limit != null ? `/${column.wip_limit}` : ""}
              {wipExceeded && " WIP"}
            </span>
          </div>
          <input
            value={localTitle}
            onChange={(e) => setLocalTitle(e.target.value)}
            onBlur={() => {
              if (localTitle.trim() && localTitle !== column.title) {
                onRename(column.id, localTitle.trim());
              } else {
                setLocalTitle(column.title);
              }
            }}
            className="mt-2 w-full bg-transparent font-display text-base font-semibold text-[var(--navy-dark)] outline-none truncate"
            aria-label="Column title"
          />
        </div>

        <div className="flex flex-col gap-1 flex-shrink-0 mt-1">
          {/* WIP limit button */}
          <button
            type="button"
            onClick={() => setEditingWip((v) => !v)}
            className="rounded-lg px-2 py-1 text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)] hover:bg-gray-100 transition-colors"
            title="Set WIP limit"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="16"></line>
              <line x1="8" y1="12" x2="16" y2="12"></line>
            </svg>
          </button>
          {/* Delete column button */}
          <button
            type="button"
            onClick={() => onDeleteColumn(column.id)}
            className="rounded-lg px-2 py-1 text-xs text-[var(--gray-text)] hover:text-red-500 hover:bg-red-50 transition-colors"
            aria-label={`Delete column ${column.title}`}
            title="Delete column"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
              <path d="M10 11v6"></path>
              <path d="M14 11v6"></path>
            </svg>
          </button>
        </div>
      </div>

      {/* WIP limit inline edit */}
      {editingWip && (
        <div className="mt-2 flex items-center gap-2">
          <input
            type="number"
            min="1"
            value={wipInput}
            onChange={(e) => setWipInput(e.target.value)}
            placeholder="No limit"
            className="w-20 border border-gray-200 rounded-lg px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            autoFocus
            onKeyDown={(e) => { if (e.key === "Enter") handleWipSave(); if (e.key === "Escape") setEditingWip(false); }}
          />
          <button
            type="button"
            onClick={handleWipSave}
            className="text-xs font-semibold text-[var(--primary-blue)] hover:underline"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setEditingWip(false)}
            className="text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
          >
            Cancel
          </button>
        </div>
      )}

      <div className="mt-4 flex flex-1 flex-col gap-3">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card, idx) => (
            <KanbanCard
              key={card.id}
              card={card}
              boardId={boardId}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              onUpdate={(updates) => onUpdateCard(card.id, column.id, idx, updates)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(data) => onAddCard(column.id, data.title, data.details, data.priority, data.due_date, data.labels)}
      />
    </section>
  );
};
