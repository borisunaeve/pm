"use client";

import { useState, useEffect } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";
import * as api from "@/lib/api";

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
  boardId: string;
  onDelete: (cardId: string) => void;
  onUpdate: (updates: Partial<Card>) => Promise<void>;
};

export const KanbanCard = ({ card, boardId, onDelete, onUpdate }: KanbanCardProps) => {
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
  const hasChecklist = (card.checklist_total ?? 0) > 0;

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

            {/* Checklist progress bar */}
            {hasChecklist && (
              <div className="mt-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--primary-blue)] rounded-full transition-all"
                      style={{ width: `${Math.round(((card.checklist_done ?? 0) / (card.checklist_total ?? 1)) * 100)}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-[var(--gray-text)] font-medium">
                    {card.checklist_done}/{card.checklist_total}
                  </span>
                </div>
              </div>
            )}

            {/* Assignee */}
            {card.assignee_username && (
              <div className="mt-1.5 flex items-center gap-1.5">
                <div className="h-5 w-5 rounded-full bg-[var(--primary-blue)] flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0">
                  {card.assignee_username.slice(0, 1).toUpperCase()}
                </div>
                <span className="text-[10px] text-[var(--gray-text)] truncate">{card.assignee_username}</span>
              </div>
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
          boardId={boardId}
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
  boardId: string;
  onSave: (updates: Partial<Card>) => Promise<void>;
  onClose: () => void;
};

type ModalTab = "details" | "checklist" | "comments";

const CardEditModal = ({ card, boardId, onSave, onClose }: CardEditModalProps) => {
  const [tab, setTab] = useState<ModalTab>("details");
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details || "");
  const [priority, setPriority] = useState<"low" | "medium" | "high">(
    (card.priority as "low" | "medium" | "high") || "medium"
  );
  const [dueDate, setDueDate] = useState(card.due_date || "");
  const [labels, setLabels] = useState(card.labels || "");
  const [assigneeId, setAssigneeId] = useState(card.assignee_id || "");
  const [members, setMembers] = useState<api.BoardMember[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.listMembers(boardId).then(setMembers).catch(() => {});
  }, [boardId]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    await onSave({ title: title.trim(), details, priority, due_date: dueDate || null, labels, assignee_id: assigneeId || null });
    setSaving(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col"
        style={{ maxHeight: "90vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Tab bar */}
        <div className="flex border-b border-gray-100 px-6 pt-5">
          {(["details", "checklist", "comments"] as ModalTab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={clsx(
                "mr-4 pb-3 text-sm font-semibold capitalize transition-colors border-b-2 -mb-px",
                tab === t
                  ? "border-[var(--primary-blue)] text-[var(--primary-blue)]"
                  : "border-transparent text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
              )}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="overflow-y-auto flex-1 p-6">
          {tab === "details" && (
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
              <div>
                <label className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Assignee</label>
                <select
                  value={assigneeId}
                  onChange={(e) => setAssigneeId(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                >
                  <option value="">Unassigned</option>
                  {members.map((m) => (
                    <option key={m.user_id} value={m.user_id}>{m.username}</option>
                  ))}
                </select>
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
          )}

          {tab === "checklist" && (
            <ChecklistTab cardId={card.id} onClose={onClose} />
          )}

          {tab === "comments" && (
            <CommentsTab cardId={card.id} />
          )}
        </div>
      </div>
    </div>
  );
};


// ── Checklist Tab ──────────────────────────────────────────────────────────────

const ChecklistTab = ({ cardId, onClose }: { cardId: string; onClose: () => void }) => {
  const [items, setItems] = useState<api.ChecklistItem[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listChecklist(cardId).then(setItems).finally(() => setLoading(false));
  }, [cardId]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    const item = await api.createChecklistItem(cardId, newTitle.trim());
    setItems((prev) => [...prev, item]);
    setNewTitle("");
  };

  const handleToggle = async (item: api.ChecklistItem) => {
    const updated = await api.updateChecklistItem(cardId, item.id, { checked: !item.checked });
    setItems((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
  };

  const handleDelete = async (itemId: string) => {
    await api.deleteChecklistItem(cardId, itemId);
    setItems((prev) => prev.filter((i) => i.id !== itemId));
  };

  const done = items.filter((i) => i.checked).length;

  if (loading) return <div className="text-sm text-[var(--gray-text)]">Loading...</div>;

  return (
    <div className="space-y-3">
      {items.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-[var(--gray-text)]">{done}/{items.length} done</span>
            <span className="text-xs text-[var(--gray-text)]">{Math.round((done / items.length) * 100)}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--primary-blue)] rounded-full transition-all"
              style={{ width: `${Math.round((done / items.length) * 100)}%` }}
            />
          </div>
        </div>
      )}

      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.id} className="flex items-center gap-3 group">
            <input
              type="checkbox"
              checked={item.checked}
              onChange={() => handleToggle(item)}
              className="h-4 w-4 rounded border-gray-300 text-[var(--primary-blue)] cursor-pointer"
            />
            <span className={clsx("flex-1 text-sm text-[var(--navy-dark)]", item.checked && "line-through text-[var(--gray-text)]")}>
              {item.title}
            </span>
            <button
              type="button"
              onClick={() => handleDelete(item.id)}
              className="opacity-0 group-hover:opacity-100 text-xs text-[var(--gray-text)] hover:text-red-500 transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={handleAdd} className="flex gap-2 pt-2">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Add item..."
          className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
        <button
          type="submit"
          disabled={!newTitle.trim()}
          className="rounded-xl bg-[var(--primary-blue)] px-3 py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-60"
        >
          Add
        </button>
      </form>

      <button
        type="button"
        onClick={onClose}
        className="w-full mt-2 rounded-xl border border-gray-200 py-2 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition"
      >
        Close
      </button>
    </div>
  );
};


// ── Comments Tab ───────────────────────────────────────────────────────────────

const CommentsTab = ({ cardId }: { cardId: string }) => {
  const [comments, setComments] = useState<api.Comment[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const currentUser = api.getUser();

  useEffect(() => {
    api.listComments(cardId).then(setComments).finally(() => setLoading(false));
  }, [cardId]);

  const handlePost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    const comment = await api.createComment(cardId, content.trim());
    setComments((prev) => [...prev, comment]);
    setContent("");
  };

  const handleDelete = async (commentId: string) => {
    await api.deleteComment(cardId, commentId);
    setComments((prev) => prev.filter((c) => c.id !== commentId));
  };

  if (loading) return <div className="text-sm text-[var(--gray-text)]">Loading...</div>;

  return (
    <div className="space-y-3">
      <ul className="space-y-3 max-h-64 overflow-y-auto">
        {comments.length === 0 && (
          <li className="text-sm text-[var(--gray-text)] italic">No comments yet.</li>
        )}
        {comments.map((c) => (
          <li key={c.id} className="rounded-xl bg-gray-50 px-4 py-3 group relative">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-[var(--navy-dark)]">{c.username}</span>
              <span className="text-[10px] text-[var(--gray-text)]">
                {new Date(c.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
            <p className="text-sm text-[var(--navy-dark)] whitespace-pre-wrap">{c.content}</p>
            {currentUser?.id === c.user_id && (
              <button
                type="button"
                onClick={() => handleDelete(c.id)}
                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-[var(--gray-text)] hover:text-red-500 transition"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            )}
          </li>
        ))}
      </ul>

      <form onSubmit={handlePost} className="space-y-2 pt-2">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write a comment..."
          rows={3}
          className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)] resize-none"
        />
        <button
          type="submit"
          disabled={!content.trim()}
          className="w-full rounded-xl bg-[var(--primary-blue)] py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-60"
        >
          Post Comment
        </button>
      </form>
    </div>
  );
};
