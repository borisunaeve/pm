"use client";

import { useState, useEffect } from "react";
import clsx from "clsx";
import * as api from "@/lib/api";

type AnalyticsPanelProps = {
  boardId: string;
  onClose: () => void;
};

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-amber-400",
  low: "bg-green-500",
};

const PRIORITY_TEXT: Record<string, string> = {
  high: "text-red-700",
  medium: "text-amber-700",
  low: "text-green-700",
};

const STATUS_COLORS: Record<string, string> = {
  planning: "bg-gray-100 text-gray-600",
  active: "bg-green-100 text-green-700",
  completed: "bg-blue-100 text-blue-700",
};

function MiniBar({ value, max, className }: { value: number; max: number; className?: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
      <div
        className={clsx("h-full rounded-full transition-all duration-500", className ?? "bg-[var(--primary-blue)]")}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color?: string }) {
  return (
    <div className="rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 flex flex-col">
      <span className={clsx("text-2xl font-display font-bold", color ?? "text-[var(--navy-dark)]")}>{value}</span>
      <span className="text-[10px] uppercase tracking-wide text-[var(--gray-text)] font-semibold mt-0.5">{label}</span>
      {sub && <span className="text-[10px] text-[var(--gray-text)] mt-0.5">{sub}</span>}
    </div>
  );
}

export const AnalyticsPanel = ({ boardId, onClose }: AnalyticsPanelProps) => {
  const [data, setData] = useState<api.BoardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getBoardAnalytics(boardId)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, [boardId]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end p-4 bg-black/30 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-[520px] rounded-2xl border border-[var(--stroke)] bg-white shadow-2xl flex flex-col mt-4"
        style={{ maxHeight: "92vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <h3 className="font-display font-semibold text-[var(--navy-dark)] text-lg">Board Analytics</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-xs px-1"
          >
            Close
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-6 space-y-6">
          {loading && (
            <div className="py-12 text-center text-sm text-[var(--gray-text)]">Loading analytics...</div>
          )}

          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">{error}</div>
          )}

          {data && (
            <>
              {/* Summary stats */}
              <section>
                <h4 className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide mb-3">Overview</h4>
                <div className="grid grid-cols-2 gap-3">
                  <StatCard label="Total Cards" value={data.total_cards} color="text-[var(--primary-blue)]" />
                  <StatCard label="Archived" value={data.archived_cards} color="text-[var(--gray-text)]" />
                  <StatCard
                    label="Overdue"
                    value={data.overdue_cards}
                    color={data.overdue_cards > 0 ? "text-red-500" : "text-[var(--gray-text)]"}
                  />
                  <StatCard
                    label="Due This Week"
                    value={data.due_this_week}
                    color={data.due_this_week > 0 ? "text-amber-600" : "text-[var(--gray-text)]"}
                  />
                </div>
              </section>

              {/* Time tracking */}
              {(data.avg_estimated_hours > 0 || data.avg_actual_hours > 0) && (
                <section>
                  <h4 className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide mb-3">Time Tracking (avg per card)</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <StatCard label="Avg Estimated" value={`${data.avg_estimated_hours}h`} color="text-[var(--navy-dark)]" />
                    <StatCard label="Avg Actual" value={`${data.avg_actual_hours}h`} color="text-[var(--navy-dark)]" />
                  </div>
                </section>
              )}

              {/* Cards by column */}
              {data.by_column.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide mb-3">Cards by Column</h4>
                  <div className="space-y-2">
                    {(() => {
                      const maxTotal = Math.max(...data.by_column.map((c) => c.total), 1);
                      return data.by_column.map((col) => (
                        <div key={col.column_id} className="flex items-center gap-3">
                          <span className="text-xs text-[var(--navy-dark)] font-medium w-28 truncate flex-shrink-0">
                            {col.column_title}
                          </span>
                          <MiniBar value={col.total} max={maxTotal} className="bg-[var(--primary-blue)]" />
                          <span className="text-xs font-semibold text-[var(--navy-dark)] tabular-nums w-6 text-right flex-shrink-0">
                            {col.total}
                          </span>
                        </div>
                      ));
                    })()}
                  </div>
                </section>
              )}

              {/* Priority breakdown */}
              {data.by_priority.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide mb-3">By Priority</h4>
                  <div className="space-y-2">
                    {(() => {
                      const maxCount = Math.max(...data.by_priority.map((p) => p.count), 1);
                      return data.by_priority.map((p) => (
                        <div key={p.priority} className="flex items-center gap-3">
                          <span className={clsx("text-xs font-semibold uppercase w-16 flex-shrink-0", PRIORITY_TEXT[p.priority] ?? "text-[var(--gray-text)]")}>
                            {p.priority}
                          </span>
                          <MiniBar value={p.count} max={maxCount} className={PRIORITY_COLORS[p.priority] ?? "bg-gray-400"} />
                          <span className="text-xs font-semibold text-[var(--navy-dark)] tabular-nums w-6 text-right flex-shrink-0">
                            {p.count}
                          </span>
                        </div>
                      ));
                    })()}
                  </div>
                </section>
              )}

              {/* Label breakdown */}
              {data.by_label.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide mb-3">Top Labels</h4>
                  <div className="flex flex-wrap gap-2">
                    {data.by_label.slice(0, 12).map((l) => (
                      <span key={l.label} className="rounded-full bg-purple-50 border border-purple-100 px-3 py-1 text-xs font-semibold text-purple-700 flex items-center gap-1.5">
                        {l.label}
                        <span className="rounded-full bg-purple-200 text-purple-800 px-1.5 py-0.5 text-[10px] font-bold">
                          {l.count}
                        </span>
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* Sprint progress */}
              {data.sprints.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide mb-3">Sprint Progress</h4>
                  <div className="space-y-3">
                    {data.sprints.map((sprint) => {
                      const pct = sprint.total_cards > 0
                        ? Math.round((sprint.done_cards / sprint.total_cards) * 100)
                        : 0;
                      const hoursOver = sprint.actual_hours > 0 && sprint.estimated_hours > 0
                        ? sprint.actual_hours > sprint.estimated_hours
                        : false;

                      return (
                        <div key={sprint.sprint_id} className="rounded-xl border border-[var(--stroke)] p-3">
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="text-sm font-semibold text-[var(--navy-dark)] truncate">{sprint.sprint_title}</span>
                            <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase flex-shrink-0", STATUS_COLORS[sprint.status])}>
                              {sprint.status}
                            </span>
                          </div>

                          {sprint.total_cards > 0 && (
                            <div className="space-y-1.5">
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                                  <div
                                    className={clsx("h-full rounded-full transition-all", pct === 100 ? "bg-green-500" : "bg-[var(--primary-blue)]")}
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                                <span className="text-xs text-[var(--gray-text)] tabular-nums w-16 text-right flex-shrink-0">
                                  {sprint.done_cards}/{sprint.total_cards} ({pct}%)
                                </span>
                              </div>
                              {(sprint.estimated_hours > 0 || sprint.actual_hours > 0) && (
                                <p className={clsx("text-[10px]", hoursOver ? "text-red-500" : "text-[var(--gray-text)]")}>
                                  {sprint.actual_hours}h logged / {sprint.estimated_hours}h estimated
                                  {hoursOver && " — over estimate"}
                                </p>
                              )}
                            </div>
                          )}

                          {sprint.total_cards === 0 && (
                            <p className="text-xs text-[var(--gray-text)] italic">No cards assigned</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
