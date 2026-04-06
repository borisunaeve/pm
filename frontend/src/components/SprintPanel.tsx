"use client";

import { useState, useEffect } from "react";
import clsx from "clsx";
import * as api from "@/lib/api";

type SprintPanelProps = {
  boardId: string;
  onClose: () => void;
  onSprintsChange?: () => void;
};

const STATUS_COLORS: Record<string, string> = {
  planning: "bg-gray-100 text-gray-600",
  active: "bg-green-100 text-green-700",
  completed: "bg-blue-100 text-blue-700",
};

const STATUS_LABELS: Record<string, string> = {
  planning: "Planning",
  active: "Active",
  completed: "Completed",
};

function SprintForm({
  onSubmit,
  onCancel,
  initial,
}: {
  onSubmit: (data: { title: string; goal: string; start_date: string; end_date: string }) => Promise<void>;
  onCancel: () => void;
  initial?: { title: string; goal: string; start_date: string; end_date: string };
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [goal, setGoal] = useState(initial?.goal ?? "");
  const [startDate, setStartDate] = useState(initial?.start_date ?? "");
  const [endDate, setEndDate] = useState(initial?.end_date ?? "");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await onSubmit({ title: title.trim(), goal, start_date: startDate, end_date: endDate });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-[var(--stroke)] bg-gray-50 p-4">
      <div>
        <label className="text-[10px] font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">
          Sprint Title
        </label>
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Sprint 1"
          required
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
      </div>
      <div>
        <label className="text-[10px] font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">
          Goal (optional)
        </label>
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="What is the sprint goal?"
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">Start</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-[var(--gray-text)] uppercase tracking-wide block mb-1">End</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={saving || !title.trim()}
          className="flex-1 bg-[var(--primary-blue)] text-white rounded-lg py-2 text-sm font-semibold hover:brightness-110 transition disabled:opacity-60"
        >
          {saving ? "Saving..." : initial ? "Update Sprint" : "Create Sprint"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export const SprintPanel = ({ boardId, onClose, onSprintsChange }: SprintPanelProps) => {
  const [sprints, setSprints] = useState<api.Sprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingSprint, setEditingSprint] = useState<api.Sprint | null>(null);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const data = await api.listSprints(boardId);
      setSprints(data);
      onSprintsChange?.();
    } catch {
      setError("Failed to load sprints");
    }
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [boardId]);

  const handleCreate = async (data: { title: string; goal: string; start_date: string; end_date: string }) => {
    setError("");
    try {
      await api.createSprint(boardId, {
        title: data.title,
        goal: data.goal || undefined,
        start_date: data.start_date || undefined,
        end_date: data.end_date || undefined,
      });
      setShowForm(false);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create sprint");
    }
  };

  const handleUpdate = async (sprintId: string, data: { title: string; goal: string; start_date: string; end_date: string }) => {
    setError("");
    try {
      await api.updateSprint(sprintId, {
        title: data.title,
        goal: data.goal || undefined,
        start_date: data.start_date || null,
        end_date: data.end_date || null,
      });
      setEditingSprint(null);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update sprint");
    }
  };

  const handleStart = async (sprintId: string) => {
    setError("");
    try {
      await api.startSprint(sprintId);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start sprint");
    }
  };

  const handleComplete = async (sprintId: string) => {
    setError("");
    try {
      await api.completeSprint(sprintId);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to complete sprint");
    }
  };

  const handleDelete = async (sprintId: string, title: string) => {
    if (!confirm(`Delete sprint "${title}"? Cards will be unlinked from the sprint.`)) return;
    setError("");
    try {
      await api.deleteSprint(sprintId);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete sprint");
    }
  };

  const activeSprint = sprints.find((s) => s.status === "active");

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-end p-4 pointer-events-none"
      onClick={onClose}
    >
      <div
        className="pointer-events-auto w-96 rounded-2xl border border-[var(--stroke)] bg-white shadow-2xl flex flex-col"
        style={{ maxHeight: "80vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 flex-shrink-0">
          <div>
            <h3 className="font-display font-semibold text-[var(--navy-dark)] text-base">Sprints</h3>
            {activeSprint && (
              <p className="text-[10px] text-green-600 font-semibold mt-0.5">
                Active: {activeSprint.title}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!showForm && !editingSprint && (
              <button
                type="button"
                onClick={() => setShowForm(true)}
                className="rounded-lg bg-[var(--primary-blue)] px-3 py-1.5 text-xs font-semibold text-white hover:brightness-110 transition"
              >
                + New Sprint
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-xs px-1"
            >
              Close
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-4 mt-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-600 flex-shrink-0">
            {error}
            <button type="button" onClick={() => setError("")} className="ml-2 underline">dismiss</button>
          </div>
        )}

        {/* Content */}
        <div className="overflow-y-auto flex-1 p-4 space-y-3">
          {/* Create form */}
          {showForm && (
            <SprintForm
              onSubmit={handleCreate}
              onCancel={() => setShowForm(false)}
            />
          )}

          {loading && !sprints.length && (
            <p className="text-sm text-[var(--gray-text)] text-center py-6">Loading sprints...</p>
          )}

          {!loading && sprints.length === 0 && !showForm && (
            <div className="text-center py-8">
              <p className="text-sm text-[var(--gray-text)] italic">No sprints yet.</p>
              <p className="text-xs text-[var(--gray-text)] mt-1">Create a sprint to track focused work cycles.</p>
            </div>
          )}

          {sprints.map((sprint) => (
            <div key={sprint.id}>
              {editingSprint?.id === sprint.id ? (
                <SprintForm
                  initial={{
                    title: sprint.title,
                    goal: sprint.goal || "",
                    start_date: sprint.start_date || "",
                    end_date: sprint.end_date || "",
                  }}
                  onSubmit={(data) => handleUpdate(sprint.id, data)}
                  onCancel={() => setEditingSprint(null)}
                />
              ) : (
                <div className={clsx(
                  "rounded-xl border p-4",
                  sprint.status === "active" ? "border-green-200 bg-green-50/40" : "border-[var(--stroke)] bg-white"
                )}>
                  {/* Sprint header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-display text-sm font-semibold text-[var(--navy-dark)]">
                          {sprint.title}
                        </h4>
                        <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase", STATUS_COLORS[sprint.status])}>
                          {STATUS_LABELS[sprint.status]}
                        </span>
                      </div>
                      {sprint.goal && (
                        <p className="mt-1 text-xs text-[var(--gray-text)] leading-5">{sprint.goal}</p>
                      )}
                      {(sprint.start_date || sprint.end_date) && (
                        <p className="mt-1 text-[10px] text-[var(--gray-text)]">
                          {sprint.start_date && new Date(sprint.start_date + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                          {sprint.start_date && sprint.end_date && " — "}
                          {sprint.end_date && new Date(sprint.end_date + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                        </p>
                      )}
                      {/* Card counts */}
                      {(sprint.card_count != null && sprint.card_count > 0) && (
                        <div className="mt-2">
                          <div className="flex items-center justify-between text-[10px] text-[var(--gray-text)] mb-1">
                            <span>{sprint.done_count ?? 0} of {sprint.card_count} cards done</span>
                            <span>{sprint.card_count > 0 ? Math.round(((sprint.done_count ?? 0) / sprint.card_count) * 100) : 0}%</span>
                          </div>
                          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={clsx(
                                "h-full rounded-full transition-all",
                                (sprint.done_count ?? 0) === sprint.card_count ? "bg-green-500" : "bg-[var(--primary-blue)]"
                              )}
                              style={{ width: `${sprint.card_count > 0 ? Math.round(((sprint.done_count ?? 0) / sprint.card_count) * 100) : 0}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {sprint.status === "planning" && (
                      <button
                        type="button"
                        onClick={() => handleStart(sprint.id)}
                        className="rounded-lg bg-green-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:brightness-110 transition"
                      >
                        Start Sprint
                      </button>
                    )}
                    {sprint.status === "active" && (
                      <button
                        type="button"
                        onClick={() => handleComplete(sprint.id)}
                        className="rounded-lg bg-blue-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:brightness-110 transition"
                      >
                        Complete Sprint
                      </button>
                    )}
                    {sprint.status !== "active" && (
                      <button
                        type="button"
                        onClick={() => setEditingSprint(sprint)}
                        className="rounded-lg border border-gray-200 px-2.5 py-1 text-[10px] font-semibold text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition"
                      >
                        Edit
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDelete(sprint.id, sprint.title)}
                      className="rounded-lg border border-red-100 px-2.5 py-1 text-[10px] font-semibold text-red-500 hover:bg-red-50 transition"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
