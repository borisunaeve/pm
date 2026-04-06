"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import type { BoardData } from "@/lib/kanban";
import { FilterState } from "@/components/FilterBar";

type GroupBy = "priority" | "assignee" | "label";

const PRIORITY_ORDER = ["high", "medium", "low"];
const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700 border-red-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low: "bg-green-100 text-green-700 border-green-200",
};
const PRIORITY_STRIP: Record<string, string> = {
  high: "bg-red-400",
  medium: "bg-amber-400",
  low: "bg-green-400",
};

type SwimlanesViewProps = {
  board: BoardData;
  filters: FilterState;
  onCardClick: (cardId: string) => void;
};

export function SwimlanesView({ board, filters, onCardClick }: SwimlanesViewProps) {
  const [groupBy, setGroupBy] = useState<GroupBy>("priority");

  // Apply filters
  const filtered = useMemo(() => {
    const q = filters.search.toLowerCase();
    return Object.values(board.cards).filter((c) => {
      if (q && !c.title.toLowerCase().includes(q) && !(c.details || "").toLowerCase().includes(q)) return false;
      if (filters.priority && c.priority !== filters.priority) return false;
      if (filters.label) {
        const cardLabels = (c.labels || "").split(",").map((l) => l.trim());
        if (!cardLabels.includes(filters.label)) return false;
      }
      return true;
    });
  }, [board.cards, filters]);

  // Build swimlane groups
  const groups = useMemo((): { key: string; label: string; cardIds: string[] }[] => {
    if (groupBy === "priority") {
      const byPriority: Record<string, string[]> = { high: [], medium: [], low: [] };
      filtered.forEach((c) => {
        const p = c.priority ?? "medium";
        byPriority[p] = byPriority[p] ?? [];
        byPriority[p].push(c.id);
      });
      return PRIORITY_ORDER.map((p) => ({
        key: p,
        label: p.charAt(0).toUpperCase() + p.slice(1) + " Priority",
        cardIds: byPriority[p] ?? [],
      })).filter((g) => g.cardIds.length > 0);
    }

    if (groupBy === "assignee") {
      const byAssignee: Record<string, { label: string; cardIds: string[] }> = {};
      filtered.forEach((c) => {
        const key = c.assignee_username ?? "__unassigned";
        const label = c.assignee_username ?? "Unassigned";
        if (!byAssignee[key]) byAssignee[key] = { label, cardIds: [] };
        byAssignee[key].cardIds.push(c.id);
      });
      return Object.entries(byAssignee)
        .sort(([a], [b]) => (a === "__unassigned" ? 1 : b === "__unassigned" ? -1 : a.localeCompare(b)))
        .map(([key, v]) => ({ key, label: v.label, cardIds: v.cardIds }));
    }

    // label
    const byLabel: Record<string, string[]> = { __none: [] };
    filtered.forEach((c) => {
      const lbls = (c.labels || "").split(",").map((l) => l.trim()).filter(Boolean);
      if (lbls.length === 0) {
        byLabel.__none.push(c.id);
      } else {
        lbls.forEach((l) => {
          byLabel[l] = byLabel[l] ?? [];
          byLabel[l].push(c.id);
        });
      }
    });
    const result = Object.entries(byLabel)
      .filter(([, ids]) => ids.length > 0)
      .map(([key, cardIds]) => ({ key, label: key === "__none" ? "No Label" : key, cardIds }));
    return result.sort((a, b) => (a.key === "__none" ? 1 : b.key === "__none" ? -1 : a.label.localeCompare(b.label)));
  }, [filtered, groupBy]);

  const columnById = useMemo(() => {
    const m: Record<string, string> = {};
    board.columns.forEach((c) => { m[c.id] = c.title; });
    return m;
  }, [board.columns]);

  if (filtered.length === 0) {
    return (
      <div className="py-16 text-center text-[var(--gray-text)] text-sm italic rounded-2xl border border-[var(--stroke)] bg-white">
        No cards match the current filters.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Group-by selector */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide">Group by:</span>
        <div className="flex rounded-xl border border-[var(--stroke)] overflow-hidden bg-white">
          {(["priority", "assignee", "label"] as GroupBy[]).map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => setGroupBy(opt)}
              className={clsx(
                "px-3 py-1.5 text-xs font-semibold transition capitalize",
                groupBy === opt
                  ? "bg-[var(--primary-blue)] text-white"
                  : "text-[var(--navy-dark)] hover:bg-gray-50"
              )}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Swimlane rows */}
      {groups.map((group) => (
        <div key={group.key} className="rounded-2xl border border-[var(--stroke)] overflow-hidden">
          {/* Row header */}
          <div className={clsx(
            "flex items-center gap-3 px-4 py-2.5 border-b border-[var(--stroke)]",
            groupBy === "priority" ? PRIORITY_COLORS[group.key] ?? "bg-gray-100 text-gray-700 border-gray-200" : "bg-gray-50 text-[var(--navy-dark)]"
          )}>
            {groupBy === "priority" && (
              <span className={clsx("w-2.5 h-2.5 rounded-full flex-shrink-0", PRIORITY_STRIP[group.key])} />
            )}
            {groupBy === "assignee" && group.key !== "__unassigned" && (
              <span className="w-5 h-5 rounded-full bg-[var(--purple-sec)] text-white text-[9px] font-bold flex items-center justify-center flex-shrink-0">
                {group.label.charAt(0).toUpperCase()}
              </span>
            )}
            <span className="text-sm font-semibold">{group.label}</span>
            <span className="text-xs text-[var(--gray-text)] ml-auto">{group.cardIds.length} card{group.cardIds.length !== 1 ? "s" : ""}</span>
          </div>

          {/* Cards grid - grouped by column */}
          <div className="flex gap-0 overflow-x-auto">
            {board.columns.map((col) => {
              const colCards = group.cardIds
                .filter((id) => col.cardIds.includes(id))
                .map((id) => board.cards[id])
                .filter(Boolean);

              return (
                <div key={col.id} className="flex-shrink-0 min-w-[200px] border-r border-[var(--stroke)] last:border-r-0 p-3">
                  <p className="text-[10px] font-semibold text-[var(--gray-text)] uppercase tracking-wide mb-2">
                    {col.title} ({colCards.length})
                  </p>
                  <div className="space-y-2">
                    {colCards.map((card) => (
                      <button
                        key={card.id}
                        type="button"
                        onClick={() => onCardClick(card.id)}
                        className="w-full text-left rounded-xl border border-[var(--stroke)] bg-white p-2.5 hover:border-[var(--primary-blue)] hover:shadow-sm transition-all group overflow-hidden"
                      >
                        {card.color && (
                          <div className="h-1 w-full -mx-2.5 -mt-2.5 mb-2" style={{ backgroundColor: card.color, marginLeft: "-10px", marginRight: "-10px", width: "calc(100% + 20px)" }} />
                        )}
                        <p className="text-xs font-semibold text-[var(--navy-dark)] group-hover:text-[var(--primary-blue)] transition-colors line-clamp-2">
                          {card.title}
                        </p>
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {card.due_date && (
                            <span className={clsx(
                              "text-[9px] px-1.5 py-0.5 rounded-full font-medium",
                              card.due_date < new Date().toISOString().split("T")[0]
                                ? "bg-red-100 text-red-600"
                                : "bg-gray-100 text-[var(--gray-text)]"
                            )}>
                              {card.due_date}
                            </span>
                          )}
                          {card.assignee_username && groupBy !== "assignee" && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">
                              @{card.assignee_username}
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                    {colCards.length === 0 && (
                      <div className="h-8 rounded-lg border border-dashed border-gray-200" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
