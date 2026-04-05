import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-green-100 text-green-700",
};

function dueDateStatus(due_date: string | null | undefined): "overdue" | "due-soon" | "ok" | "none" {
  if (!due_date) return "none";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(due_date + "T00:00:00");
  const diffDays = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return "overdue";
  if (diffDays <= 3) return "due-soon";
  return "ok";
}

function formatDate(due_date: string): string {
  const d = new Date(due_date + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onUpdate: (updates: Partial<Card>) => Promise<void>;
};

export const KanbanCard = ({ card, onDelete, onUpdate }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });
  const [editing, setEditing] = useState(false);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const labelList = card.labels ? card.labels.split(",").map((l) => l.trim()).filter(Boolean) : [];
  const priority = card.priority || "medium";
  const dateStatus = dueDateStatus(card.due_date);

  return (
    <>
      <article
        ref={setNodeRef}
        style={style}
        className={clsx(
          "rounded-2xl border bg-white px-4 py-3 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
          "transition-all duration-150",
          dateStatus === "overdue" && "border-red-300 bg-red-50/40",
          dateStatus === "due-soon" && "border-amber-300",
          dateStatus !== "overdue" && dateStatus !== "due-soon" && "border-transparent",
          isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
        )}
        {...attributes}
        {...listeners}
        data-testid={`card-${card.id}`}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h4 className="font-display text-sm font-semibold text-[var(--navy-dark)] leading-snug">
              {card.title}
            </h4>
            {card.details && (
              <p className="mt-1 text-xs leading-5 text-[var(--gray-text)] line-clamp-2">
                {card.details}
              </p>
            )}

            {/* Meta: priority + due date + labels */}
            <div className="mt-2 flex flex-wrap gap-1.5 items-center">
              <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase", PRIORITY_COLORS[priority])}>
                {priority}
              </span>
              {card.due_date && (
                <span className={clsx(
                  "rounded-full px-2 py-0.5 text-[10px] font-semibold flex items-center gap-1",
                  dateStatus === "overdue" && "bg-red-100 text-red-700",
                  dateStatus === "due-soon" && "bg-amber-100 text-amber-700",
                  dateStatus === "ok" && "bg-blue-50 text-blue-700",
                )}>
                  {dateStatus === "overdue" && "Overdue · "}
                  {formatDate(card.due_date)}
                </span>
              )}
              {labelList.map((label) => (
                <span key={label} className="rounded-full bg-purple-50 text-purple-700 px-2 py-0.5 text-[10px] font-semibold">
                  {label}
                </span>
              ))}
            </div>
          </div>

          {/* Actions — prevent drag */}
          <div
            className="flex flex-col gap-1 flex-shrink-0"
            onPointerDown={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setEditing(true); }}
              className="rounded-lg px-1.5 py-1 text-[10px] font-semibold text-[var(--gray-text)] hover:text-[var(--navy-dark)] hover:bg-gray-100 transition-colors"
              aria-label={`Edit ${card.title}`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onDelete(card.id); }}
              className="rounded-lg px-1.5 py-1 text-[10px] font-semibold text-[var(--gray-text)] hover:text-red-500 hover:bg-red-50 transition-colors"
              aria-label={`Delete ${card.title}`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>
      </article>

      {editing && (
        <CardEditModal
          card={card}
          onSave={async (updates) => {
            await onUpdate(updates);
            setEditing(false);
          }}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
};


// ── Card Edit Modal ────────────────────────────────────────────────────────────

type CardEditModalProps = {
  card: Card;
  onSave: (updates: Partial<Card>) => Promise<void>;
  onClose: () => void;
};

const CardEditModal = ({ card, onSave, onClose }: CardEditModalProps) => {
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details || "");
  const [priority, setPriority] = useState<"low" | "medium" | "high">(
    (card.priority as "low" | "medium" | "high") || "medium"
  );
  const [dueDate, setDueDate] = useState(card.due_date || "");
  const [labels, setLabels] = useState(card.labels || "");
  const [saving, setSaving] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    await onSave({ title: title.trim(), details, priority, due_date: dueDate || null, labels });
    setSaving(false);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-display font-semibold text-[var(--navy-dark)] text-lg mb-4">Edit Card</h3>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Title</label>
            <input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Details</label>
            <textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              rows={3}
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)] resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as "low" | "medium" | "high")}
                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Due Date</label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Labels (comma-separated)</label>
            <input
              value={labels}
              onChange={(e) => setLabels(e.target.value)}
              placeholder="e.g. frontend, bug, urgent"
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving || !title.trim()}
              className="flex-1 bg-[var(--primary-blue)] text-white rounded-xl py-2.5 text-sm font-semibold hover:brightness-110 transition disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
