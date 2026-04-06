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

const RELATION_LABELS: Record<string, string> = {
  "blocks": "Blocks",
  "blocked-by": "Blocked by",
  "relates-to": "Relates to",
  "duplicate-of": "Duplicate of",
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
  onArchive?: (cardId: string) => void;
  onCopy?: (cardId: string) => void;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (cardId: string, selected: boolean) => void;
};

export const KanbanCard = ({ card, boardId, onDelete, onUpdate, onArchive, onCopy, selectable, selected, onSelect }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });
  const [editing, setEditing] = useState(false);
  const [checklistCounts, setChecklistCounts] = useState({
    done: card.checklist_done ?? 0,
    total: card.checklist_total ?? 0,
  });

  // Keep in sync if the board re-fetches and card prop updates
  useEffect(() => {
    setChecklistCounts({ done: card.checklist_done ?? 0, total: card.checklist_total ?? 0 });
  }, [card.checklist_done, card.checklist_total]);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const labelList = card.labels ? card.labels.split(",").map((l) => l.trim()).filter(Boolean) : [];
  const priority = card.priority || "medium";
  const dateStatus = dueDateStatus(card.due_date);
  const hasChecklist = checklistCounts.total > 0;
  const hasTimeTracking = card.estimated_hours != null || card.actual_hours != null;

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
          dateStatus !== "overdue" && dateStatus !== "due-soon" && "border-[var(--stroke)]",
          isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
        )}
        {...attributes}
        {...listeners}
        data-testid={`card-${card.id}`}
      >
        {selectable && (
          <div
            className="mb-2 -mt-1 flex items-center gap-2"
            onPointerDown={(e) => e.stopPropagation()}
          >
            <input
              type="checkbox"
              checked={!!selected}
              onChange={(e) => onSelect?.(card.id, e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 cursor-pointer accent-[var(--primary-blue)]"
              aria-label={`Select ${card.title}`}
            />
            <span className="text-[10px] text-[var(--gray-text)]">Select</span>
          </div>
        )}
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
              <div className="mt-2 flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--gray-text)] flex-shrink-0">
                  <polyline points="9 11 12 14 22 4"></polyline>
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                </svg>
                <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={clsx(
                      "h-full rounded-full transition-all",
                      checklistCounts.done === checklistCounts.total ? "bg-green-500" : "bg-[var(--primary-blue)]"
                    )}
                    style={{ width: `${Math.round((checklistCounts.done / (checklistCounts.total || 1)) * 100)}%` }}
                  />
                </div>
                <span className={clsx(
                  "text-[10px] font-semibold tabular-nums",
                  checklistCounts.done === checklistCounts.total ? "text-green-600" : "text-[var(--gray-text)]"
                )}>
                  {checklistCounts.done}/{checklistCounts.total}
                </span>
              </div>
            )}

            {/* Time tracking badge */}
            {hasTimeTracking && (
              <div className="mt-1.5 flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--gray-text)]">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <span className="text-[10px] text-[var(--gray-text)] tabular-nums">
                  {card.actual_hours != null ? `${card.actual_hours}h` : "0h"}
                  {card.estimated_hours != null ? ` / ${card.estimated_hours}h` : ""}
                </span>
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
            {onCopy && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onCopy(card.id); }}
                className="rounded-lg px-1.5 py-1 text-[10px] font-semibold text-[var(--gray-text)] hover:text-[var(--navy-dark)] hover:bg-gray-100 transition-colors"
                aria-label={`Copy ${card.title}`}
                title="Duplicate card"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            )}
            {onArchive && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onArchive(card.id); }}
                className="rounded-lg px-1.5 py-1 text-[10px] font-semibold text-[var(--gray-text)] hover:text-amber-600 hover:bg-amber-50 transition-colors"
                aria-label={`Archive ${card.title}`}
                title="Archive card"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="21 8 21 21 3 21 3 8"></polyline>
                  <rect x="1" y="3" width="22" height="5"></rect>
                  <line x1="10" y1="12" x2="14" y2="12"></line>
                </svg>
              </button>
            )}
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
          onChecklistChange={(done, total) => setChecklistCounts({ done, total })}
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
  onChecklistChange: (done: number, total: number) => void;
};

type ModalTab = "details" | "checklist" | "comments" | "relations" | "activity";

const CardEditModal = ({ card, boardId, onSave, onClose, onChecklistChange }: CardEditModalProps) => {
  const [tab, setTab] = useState<ModalTab>("details");
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details || "");
  const [priority, setPriority] = useState<"low" | "medium" | "high">(
    (card.priority as "low" | "medium" | "high") || "medium"
  );
  const [dueDate, setDueDate] = useState(card.due_date || "");
  const [labels, setLabels] = useState(card.labels || "");
  const [assigneeId, setAssigneeId] = useState(card.assignee_id || "");
  const [estimatedHours, setEstimatedHours] = useState(card.estimated_hours != null ? String(card.estimated_hours) : "");
  const [actualHours, setActualHours] = useState(card.actual_hours != null ? String(card.actual_hours) : "");
  const [sprintId, setSprintId] = useState(card.sprint_id || "");
  const [members, setMembers] = useState<api.BoardMember[]>([]);
  const [sprints, setSprints] = useState<api.Sprint[]>([]);
  const [saving, setSaving] = useState(false);
  const [checklistCount, setChecklistCount] = useState({ total: card.checklist_total ?? 0, done: card.checklist_done ?? 0 });
  const [commentCount, setCommentCount] = useState(0);
  const [relationCount, setRelationCount] = useState(0);
  const [activityEntries, setActivityEntries] = useState<api.CardActivityEntry[]>([]);
  const [activityCount, setActivityCount] = useState(0);

  useEffect(() => {
    api.listMembers(boardId).then(setMembers).catch(() => {});
    api.listSprints(boardId).then(setSprints).catch(() => {});
    api.listChecklist(card.id).then((items) => setChecklistCount({ total: items.length, done: items.filter(i => i.checked).length })).catch(() => {});
    api.listComments(card.id).then((items) => setCommentCount(items.length)).catch(() => {});
    api.listRelations(card.id).then((rels) => setRelationCount(rels.length)).catch(() => {});
    api.getCardActivity(card.id).then((entries) => { setActivityEntries(entries); setActivityCount(entries.length); }).catch(() => {});
  }, [boardId, card.id]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    await onSave({
      title: title.trim(),
      details,
      priority,
      due_date: dueDate || null,
      labels,
      assignee_id: assigneeId || null,
      estimated_hours: estimatedHours !== "" ? parseFloat(estimatedHours) : null,
      actual_hours: actualHours !== "" ? parseFloat(actualHours) : null,
      sprint_id: sprintId || null,
    });
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
        <div className="flex border-b border-[var(--stroke)] px-6 pt-5 overflow-x-auto">
          {([
            { id: "details", label: "Details" },
            { id: "checklist", label: "Checklist", badge: checklistCount.total > 0 ? `${checklistCount.done}/${checklistCount.total}` : undefined },
            { id: "comments", label: "Comments", badge: commentCount > 0 ? String(commentCount) : undefined },
            { id: "relations", label: "Relations", badge: relationCount > 0 ? String(relationCount) : undefined },
          { id: "activity", label: "History", badge: activityCount > 0 ? String(activityCount) : undefined },
          ] as { id: ModalTab; label: string; badge?: string }[]).map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={clsx(
                "mr-5 pb-3 text-sm font-semibold transition-colors border-b-2 -mb-px flex items-center gap-1.5 whitespace-nowrap",
                tab === t.id
                  ? "border-[var(--primary-blue)] text-[var(--primary-blue)]"
                  : "border-transparent text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
              )}
            >
              {t.label}
              {t.badge && (
                <span className={clsx(
                  "rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none",
                  tab === t.id ? "bg-[var(--primary-blue)] text-white" : "bg-gray-100 text-[var(--gray-text)]"
                )}>
                  {t.badge}
                </span>
              )}
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
              {/* Time Tracking */}
              <div>
                <label className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Time Tracking (hours)</label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] text-[var(--gray-text)] block mb-1">Estimated</label>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={estimatedHours}
                      onChange={(e) => setEstimatedHours(e.target.value)}
                      placeholder="e.g. 8"
                      className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-[var(--gray-text)] block mb-1">Actual</label>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={actualHours}
                      onChange={(e) => setActualHours(e.target.value)}
                      placeholder="e.g. 6"
                      className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                    />
                  </div>
                </div>
                {estimatedHours && actualHours && parseFloat(estimatedHours) > 0 && (
                  <div className="mt-2">
                    <div className="flex justify-between text-[10px] text-[var(--gray-text)] mb-1">
                      <span>{actualHours}h logged</span>
                      <span>{Math.round((parseFloat(actualHours) / parseFloat(estimatedHours)) * 100)}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={clsx(
                          "h-full rounded-full transition-all",
                          parseFloat(actualHours) > parseFloat(estimatedHours) ? "bg-red-500" : "bg-[var(--primary-blue)]"
                        )}
                        style={{ width: `${Math.min(100, Math.round((parseFloat(actualHours) / parseFloat(estimatedHours)) * 100))}%` }}
                      />
                    </div>
                  </div>
                )}
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
              <div className="grid grid-cols-2 gap-3">
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
                <div>
                  <label className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Sprint</label>
                  <select
                    value={sprintId}
                    onChange={(e) => setSprintId(e.target.value)}
                    className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                  >
                    <option value="">No sprint</option>
                    {sprints.map((s) => (
                      <option key={s.id} value={s.id}>{s.title} ({s.status})</option>
                    ))}
                  </select>
                </div>
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
            <ChecklistTab
              cardId={card.id}
              onClose={onClose}
              onCountChange={(counts) => {
                setChecklistCount(counts);
                onChecklistChange(counts.done, counts.total);
              }}
            />
          )}

          {tab === "comments" && (
            <CommentsTab cardId={card.id} onCountChange={setCommentCount} />
          )}

          {tab === "relations" && (
            <RelationsTab
              cardId={card.id}
              boardId={boardId}
              onCountChange={setRelationCount}
            />
          )}

          {tab === "activity" && (
            <ActivityTab entries={activityEntries} />
          )}
        </div>
      </div>
    </div>
  );
};


// ── Checklist Tab ──────────────────────────────────────────────────────────────

const ChecklistTab = ({
  cardId,
  onClose,
  onCountChange,
}: {
  cardId: string;
  onClose: () => void;
  onCountChange: (counts: { total: number; done: number }) => void;
}) => {
  const [items, setItems] = useState<api.ChecklistItem[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listChecklist(cardId).then((data) => { setItems(data); onCountChange({ total: data.length, done: data.filter(i => i.checked).length }); }).finally(() => setLoading(false));
  }, [cardId]);

  const syncCounts = (updated: api.ChecklistItem[]) => {
    onCountChange({ total: updated.length, done: updated.filter(i => i.checked).length });
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    const item = await api.createChecklistItem(cardId, newTitle.trim());
    const next = [...items, item];
    setItems(next);
    syncCounts(next);
    setNewTitle("");
  };

  const handleToggle = async (item: api.ChecklistItem) => {
    const updated = await api.updateChecklistItem(cardId, item.id, { checked: !item.checked });
    const next = items.map((i) => (i.id === item.id ? updated : i));
    setItems(next);
    syncCounts(next);
  };

  const handleDelete = async (itemId: string) => {
    await api.deleteChecklistItem(cardId, itemId);
    const next = items.filter((i) => i.id !== itemId);
    setItems(next);
    syncCounts(next);
  };

  const done = items.filter((i) => i.checked).length;
  const pct = items.length > 0 ? Math.round((done / items.length) * 100) : 0;
  const allDone = items.length > 0 && done === items.length;

  if (loading) return <div className="py-6 text-center text-sm text-[var(--gray-text)]">Loading...</div>;

  return (
    <div className="space-y-4">
      {/* Progress header */}
      {items.length > 0 && (
        <div className="rounded-xl bg-gray-50 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className={clsx("text-sm font-semibold", allDone ? "text-green-600" : "text-[var(--navy-dark)]")}>
              {allDone ? "All done!" : `${done} of ${items.length} completed`}
            </span>
            <span className={clsx("text-sm font-bold tabular-nums", allDone ? "text-green-600" : "text-[var(--primary-blue)]")}>
              {pct}%
            </span>
          </div>
          <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={clsx("h-full rounded-full transition-all duration-300", allDone ? "bg-green-500" : "bg-[var(--primary-blue)]")}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Items */}
      {items.length === 0 ? (
        <p className="py-4 text-center text-sm text-[var(--gray-text)] italic">No items yet. Add one below.</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((item) => (
            <li
              key={item.id}
              className={clsx(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 group transition-colors",
                item.checked ? "bg-green-50" : "bg-gray-50 hover:bg-gray-100"
              )}
            >
              <input
                type="checkbox"
                checked={item.checked}
                onChange={() => handleToggle(item)}
                className="h-4 w-4 rounded border-gray-300 cursor-pointer accent-[var(--primary-blue)] flex-shrink-0"
              />
              <span className={clsx(
                "flex-1 text-sm leading-snug",
                item.checked ? "line-through text-[var(--gray-text)]" : "text-[var(--navy-dark)]"
              )}>
                {item.title}
              </span>
              <button
                type="button"
                onClick={() => handleDelete(item.id)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-[var(--gray-text)] hover:text-red-500 hover:bg-red-50 transition"
                aria-label="Delete item"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Add form */}
      <form onSubmit={handleAdd} className="flex gap-2">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Add item..."
          className="flex-1 border border-[var(--stroke)] rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] bg-[var(--surface-strong)] outline-none focus:border-[var(--primary-blue)]"
          autoFocus
        />
        <button
          type="submit"
          disabled={!newTitle.trim()}
          className="rounded-xl bg-[var(--primary-blue)] px-4 py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-40 transition"
        >
          Add
        </button>
      </form>

      <button
        type="button"
        onClick={onClose}
        className="w-full rounded-xl border border-[var(--stroke)] py-2 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition"
      >
        Close
      </button>
    </div>
  );
};


// ── Comments Tab ───────────────────────────────────────────────────────────────

const CommentsTab = ({ cardId, onCountChange }: { cardId: string; onCountChange: (n: number) => void }) => {
  const [comments, setComments] = useState<api.Comment[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [posting, setPosting] = useState(false);
  const currentUser = api.getUser();

  useEffect(() => {
    api.listComments(cardId).then((data) => { setComments(data); onCountChange(data.length); }).finally(() => setLoading(false));
  }, [cardId]);

  const handlePost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    setPosting(true);
    const comment = await api.createComment(cardId, content.trim());
    const next = [...comments, comment];
    setComments(next);
    onCountChange(next.length);
    setContent("");
    setPosting(false);
  };

  const handleDelete = async (commentId: string) => {
    await api.deleteComment(cardId, commentId);
    const next = comments.filter((c) => c.id !== commentId);
    setComments(next);
    onCountChange(next.length);
  };

  if (loading) return <div className="py-6 text-center text-sm text-[var(--gray-text)]">Loading...</div>;

  return (
    <div className="flex flex-col gap-4">
      {/* Comment list */}
      <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
        {comments.length === 0 ? (
          <p className="py-4 text-center text-sm text-[var(--gray-text)] italic">No comments yet. Be the first.</p>
        ) : (
          comments.map((c) => (
            <div key={c.id} className="flex gap-3 group">
              {/* Avatar */}
              <div className="h-8 w-8 rounded-full bg-[var(--purple-sec)] flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-0.5">
                {c.username.slice(0, 1).toUpperCase()}
              </div>
              {/* Bubble */}
              <div className="flex-1 min-w-0">
                <div className="rounded-2xl rounded-tl-sm bg-gray-50 px-4 py-3 relative">
                  <div className="flex items-baseline justify-between gap-2 mb-1.5">
                    <span className="text-xs font-bold text-[var(--navy-dark)]">{c.username}</span>
                    <span className="text-[10px] text-[var(--gray-text)] flex-shrink-0">
                      {new Date(c.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                      {" · "}
                      {new Date(c.created_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--navy-dark)] whitespace-pre-wrap leading-relaxed">{c.content}</p>
                  {currentUser?.id === c.user_id && (
                    <button
                      type="button"
                      onClick={() => handleDelete(c.id)}
                      className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 p-1 rounded text-[var(--gray-text)] hover:text-red-500 hover:bg-red-50 transition"
                      aria-label="Delete comment"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Post form */}
      <form onSubmit={handlePost} className="flex gap-3 items-end border-t border-[var(--stroke)] pt-4">
        <div className="h-8 w-8 rounded-full bg-[var(--primary-blue)] flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
          {currentUser?.username?.slice(0, 1).toUpperCase() ?? "?"}
        </div>
        <div className="flex-1 space-y-2">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); handlePost(e as unknown as React.FormEvent); } }}
            placeholder="Write a comment... (Ctrl+Enter to post)"
            rows={2}
            className="w-full border border-[var(--stroke)] rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] bg-[var(--surface-strong)] outline-none focus:border-[var(--primary-blue)] resize-none"
          />
          <button
            type="submit"
            disabled={!content.trim() || posting}
            className="rounded-xl bg-[var(--primary-blue)] px-4 py-1.5 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-40 transition"
          >
            {posting ? "Posting..." : "Post Comment"}
          </button>
        </div>
      </form>
    </div>
  );
};


// ── Relations Tab ──────────────────────────────────────────────────────────────

const RelationsTab = ({
  cardId,
  boardId,
  onCountChange,
}: {
  cardId: string;
  boardId: string;
  onCountChange: (n: number) => void;
}) => {
  const [relations, setRelations] = useState<api.CardRelation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<api.SearchResultCard[]>([]);
  const [relationType, setRelationType] = useState("relates-to");
  const [searching, setSearching] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listRelations(cardId)
      .then((data) => { setRelations(data); onCountChange(data.length); })
      .finally(() => setLoading(false));
  }, [cardId]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQ.trim()) return;
    setSearching(true);
    setError("");
    try {
      const results = await api.searchCards(searchQ.trim());
      // Exclude self and already-related cards
      const relatedIds = new Set(relations.map(r => r.related_card_id));
      setSearchResults(results.filter(r => r.id !== cardId && !relatedIds.has(r.id)));
    } catch {
      setError("Search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleAdd = async (relatedCardId: string) => {
    setAdding(true);
    setError("");
    try {
      const rel = await api.addRelation(cardId, relatedCardId, relationType);
      const next = [...relations, rel];
      setRelations(next);
      onCountChange(next.length);
      setSearchResults(prev => prev.filter(r => r.id !== relatedCardId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add relation");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (relationId: number) => {
    await api.deleteRelation(cardId, relationId);
    const next = relations.filter(r => r.id !== relationId);
    setRelations(next);
    onCountChange(next.length);
  };

  if (loading) return <div className="py-6 text-center text-sm text-[var(--gray-text)]">Loading...</div>;

  return (
    <div className="space-y-4">
      {/* Existing relations */}
      {relations.length === 0 ? (
        <p className="py-2 text-sm text-[var(--gray-text)] italic">No relations yet.</p>
      ) : (
        <ul className="space-y-1.5">
          {relations.map((rel) => (
            <li key={rel.id} className="flex items-center gap-3 rounded-xl px-3 py-2.5 bg-gray-50 group">
              <span className="text-[10px] font-semibold text-[var(--purple-sec)] uppercase bg-purple-50 rounded-full px-2 py-0.5 whitespace-nowrap">
                {RELATION_LABELS[rel.relation_type] ?? rel.relation_type}
              </span>
              <span className="flex-1 text-sm text-[var(--navy-dark)] truncate">{rel.related_card_title}</span>
              <button
                type="button"
                onClick={() => handleDelete(rel.id)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-[var(--gray-text)] hover:text-red-500 hover:bg-red-50 transition flex-shrink-0"
                aria-label="Remove relation"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Add relation */}
      <div className="border-t border-[var(--stroke)] pt-4 space-y-3">
        <p className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide">Link a card</p>
        <select
          value={relationType}
          onChange={(e) => setRelationType(e.target.value)}
          className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        >
          <option value="relates-to">Relates to</option>
          <option value="blocks">Blocks</option>
          <option value="blocked-by">Blocked by</option>
          <option value="duplicate-of">Duplicate of</option>
        </select>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder="Search cards..."
            className="flex-1 border border-[var(--stroke)] rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] bg-[var(--surface-strong)] outline-none focus:border-[var(--primary-blue)]"
          />
          <button
            type="submit"
            disabled={!searchQ.trim() || searching}
            className="rounded-xl bg-[var(--primary-blue)] px-4 py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-40 transition whitespace-nowrap"
          >
            {searching ? "..." : "Search"}
          </button>
        </form>
        {error && <p className="text-xs text-red-600">{error}</p>}
        {searchResults.length > 0 && (
          <ul className="space-y-1 max-h-40 overflow-y-auto">
            {searchResults.map((r) => (
              <li key={r.id} className="flex items-center gap-2 rounded-xl px-3 py-2 bg-gray-50 hover:bg-gray-100 transition">
                <span className="flex-1 text-sm text-[var(--navy-dark)] truncate">
                  {r.title}
                  <span className="ml-1.5 text-[10px] text-[var(--gray-text)]">{r.board_title} · {r.column_title}</span>
                </span>
                <button
                  type="button"
                  disabled={adding}
                  onClick={() => handleAdd(r.id)}
                  className="text-[10px] font-semibold text-[var(--primary-blue)] hover:underline flex-shrink-0"
                >
                  Link
                </button>
              </li>
            ))}
          </ul>
        )}
        {searchResults.length === 0 && searchQ && !searching && (
          <p className="text-xs text-[var(--gray-text)] italic">No cards found.</p>
        )}
      </div>
    </div>
  );
};


// ── Activity Tab ───────────────────────────────────────────────────────────────

const FIELD_LABELS: Record<string, string> = {
  title: "title",
  priority: "priority",
  due_date: "due date",
  labels: "labels",
  assignee_id: "assignee",
  estimated_hours: "estimated hours",
  actual_hours: "actual hours",
  sprint_id: "sprint",
  column: "column",
};

const ActivityTab = ({ entries }: { entries: api.CardActivityEntry[] }) => {
  if (entries.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-[var(--gray-text)] italic">
        No changes recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map((entry) => (
        <div key={entry.id} className="flex gap-3 items-start rounded-xl bg-gray-50 px-3 py-2.5">
          <div className="h-6 w-6 rounded-full bg-[var(--primary-blue)] flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0 mt-0.5">
            {entry.username.slice(0, 1).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-[var(--navy-dark)] leading-5">
              <span className="font-semibold">{entry.username}</span>
              {" changed "}
              <span className="font-semibold">{FIELD_LABELS[entry.field] ?? entry.field}</span>
              {entry.old_value && (
                <>
                  {" from "}
                  <span className="font-mono text-[10px] bg-red-50 text-red-700 px-1 rounded">
                    {entry.old_value}
                  </span>
                </>
              )}
              {entry.new_value && (
                <>
                  {" to "}
                  <span className="font-mono text-[10px] bg-green-50 text-green-700 px-1 rounded">
                    {entry.new_value}
                  </span>
                </>
              )}
            </p>
            <p className="text-[10px] text-[var(--gray-text)] mt-0.5">
              {new Date(entry.created_at).toLocaleDateString(undefined, {
                month: "short", day: "numeric",
                hour: "2-digit", minute: "2-digit",
              })}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};

