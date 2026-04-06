"use client";

import { useState, useMemo } from "react";
import clsx from "clsx";
import type { BoardData } from "@/lib/kanban";
import { FilterState } from "@/components/FilterBar";

type SortField = "title" | "priority" | "due_date" | "labels" | "assignee" | "column" | "checklist";
type SortDir = "asc" | "desc";

const PRIORITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };
const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-500/15 text-red-500",
  medium: "bg-amber-500/15 text-amber-600",
  low: "bg-green-500/15 text-green-600",
};

function isOverdue(due: string | null | undefined): boolean {
  if (!due) return false;
  return due < new Date().toISOString().split("T")[0];
}

function isDueSoon(due: string | null | undefined): boolean {
  if (!due) return false;
  const today = new Date().toISOString().split("T")[0];
  const soon = new Date(Date.now() + 3 * 86400000).toISOString().split("T")[0];
  return due >= today && due <= soon;
}

type BoardListViewProps = {
  board: BoardData;
  filters: FilterState;
  onCardClick: (cardId: string) => void;
};

export function BoardListView({ board, filters, onCardClick }: BoardListViewProps) {
  const [sortField, setSortField] = useState<SortField>("column");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Build flat list of cards with column info
  const allCards = useMemo(() => {
    return board.columns.flatMap((col, colIndex) =>
      col.cardIds.map((cid) => ({
        ...board.cards[cid],
        columnTitle: col.title,
        columnIndex: colIndex,
        columnId: col.id,
      }))
    ).filter(Boolean);
  }, [board]);

  // Apply filters
  const filtered = useMemo(() => {
    return allCards.filter((c) => {
      if (filters.search && !c.title.toLowerCase().includes(filters.search.toLowerCase()) &&
          !c.details?.toLowerCase().includes(filters.search.toLowerCase())) return false;
      if (filters.priority && c.priority !== filters.priority) return false;
      if (filters.label) {
        const labels = (c.labels ?? "").split(",").map((l) => l.trim().toLowerCase());
        if (!labels.includes(filters.label.toLowerCase())) return false;
      }
      return true;
    });
  }, [allCards, filters]);

  // Sort
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "title": cmp = a.title.localeCompare(b.title); break;
        case "priority":
          cmp = (PRIORITY_ORDER[a.priority ?? "medium"] ?? 1) - (PRIORITY_ORDER[b.priority ?? "medium"] ?? 1);
          break;
        case "due_date":
          if (!a.due_date && !b.due_date) cmp = 0;
          else if (!a.due_date) cmp = 1;
          else if (!b.due_date) cmp = -1;
          else cmp = a.due_date.localeCompare(b.due_date);
          break;
        case "labels": cmp = (a.labels ?? "").localeCompare(b.labels ?? ""); break;
        case "assignee": cmp = (a.assignee_username ?? "").localeCompare(b.assignee_username ?? ""); break;
        case "column": cmp = a.columnIndex - b.columnIndex; break;
        case "checklist":
          cmp = (b.checklist_done ?? 0) - (a.checklist_done ?? 0); break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortField, sortDir]);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDir((d) => d === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const sortIcon = (field: SortField) =>
    sortField !== field
      ? <span className="text-gray-300 ml-1">&#8597;</span>
      : <span className="text-[var(--primary-blue)] ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;

  const thClass = "text-left text-xs font-semibold text-[var(--gray-text)] uppercase tracking-wide px-3 py-2.5 cursor-pointer select-none hover:text-[var(--navy-dark)] whitespace-nowrap";

  return (
    <div className="overflow-x-auto rounded-2xl border border-[var(--stroke)] bg-white">
      {sorted.length === 0 ? (
        <div className="py-16 text-center text-[var(--gray-text)] text-sm italic">
          No cards match the current filters.
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--stroke)] bg-gray-50/60">
            <tr>
              <th className={thClass} onClick={() => handleSort("title")}>
                Title {sortIcon("title")}
              </th>
              <th className={thClass} onClick={() => handleSort("column")}>
                Column {sortIcon("column")}
              </th>
              <th className={thClass} onClick={() => handleSort("priority")}>
                Priority {sortIcon("priority")}
              </th>
              <th className={thClass} onClick={() => handleSort("due_date")}>
                Due Date {sortIcon("due_date")}
              </th>
              <th className={thClass} onClick={() => handleSort("assignee")}>
                Assignee {sortIcon("assignee")}
              </th>
              <th className={thClass} onClick={() => handleSort("labels")}>
                Labels {sortIcon("labels")}
              </th>
              <th className={thClass} onClick={() => handleSort("checklist")}>
                Progress {sortIcon("checklist")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--stroke)]">
            {sorted.map((card) => {
              const overdue = isOverdue(card.due_date);
              const soon = !overdue && isDueSoon(card.due_date);
              const checkTotal = card.checklist_total ?? 0;
              const checkDone = card.checklist_done ?? 0;
              const pct = checkTotal > 0 ? Math.round((checkDone / checkTotal) * 100) : null;

              return (
                <tr
                  key={card.id}
                  onClick={() => onCardClick(card.id)}
                  className="cursor-pointer hover:bg-gray-50 transition-colors group"
                >
                  <td className="px-3 py-2.5 max-w-xs">
                    <div className="flex items-center gap-2">
                      {card.subtask_count != null && card.subtask_count > 0 && (
                        <span className="text-[10px] text-[var(--gray-text)] shrink-0"
                              title={`${card.subtask_count} sub-task${card.subtask_count !== 1 ? "s" : ""}`}>
                          &#8627;{card.subtask_count}
                        </span>
                      )}
                      <span className="text-[var(--navy-dark)] font-medium group-hover:text-[var(--primary-blue)] transition-colors truncate">
                        {card.title}
                      </span>
                      {card.parent_card_id && (
                        <span className="text-[10px] text-[var(--gray-text)] shrink-0" title="Sub-task">sub</span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <span className="text-[var(--gray-text)] text-xs">{card.columnTitle}</span>
                  </td>
                  <td className="px-3 py-2.5">
                    <span className={clsx(
                      "text-[10px] font-semibold px-2 py-0.5 rounded-full",
                      PRIORITY_COLORS[card.priority ?? "medium"] ?? PRIORITY_COLORS.medium
                    )}>
                      {card.priority ?? "medium"}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    {card.due_date ? (
                      <span className={clsx(
                        "text-xs font-medium",
                        overdue ? "text-red-500" : soon ? "text-amber-500" : "text-[var(--gray-text)]"
                      )}>
                        {overdue ? "Overdue · " : soon ? "Soon · " : ""}
                        {card.due_date}
                      </span>
                    ) : (
                      <span className="text-[var(--stroke)] text-xs">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    {card.assignee_username ? (
                      <div className="flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-full bg-[var(--purple-sec)] text-white text-[9px] font-bold flex items-center justify-center">
                          {card.assignee_username.slice(0, 1).toUpperCase()}
                        </span>
                        <span className="text-xs text-[var(--gray-text)]">{card.assignee_username}</span>
                      </div>
                    ) : (
                      <span className="text-[var(--stroke)] text-xs">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 max-w-[160px]">
                    {card.labels ? (
                      <div className="flex flex-wrap gap-1">
                        {card.labels.split(",").filter(Boolean).slice(0, 3).map((l) => (
                          <span key={l} className="text-[9px] px-1.5 py-0.5 rounded-full bg-[#209dd7]/10 text-[#209dd7] font-medium">
                            {l.trim()}
                          </span>
                        ))}
                        {card.labels.split(",").filter(Boolean).length > 3 && (
                          <span className="text-[9px] text-[var(--gray-text)]">+{card.labels.split(",").filter(Boolean).length - 3}</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-[var(--stroke)] text-xs">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    {pct !== null ? (
                      <div className="flex items-center gap-2 min-w-[80px]">
                        <div className="flex-1 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                          <div
                            className={clsx("h-full rounded-full", pct >= 100 ? "bg-green-500" : "bg-[var(--primary-blue)]")}
                            style={{ width: `${Math.min(100, pct)}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-[var(--gray-text)] shrink-0">{pct}%</span>
                      </div>
                    ) : (
                      <span className="text-[var(--stroke)] text-xs">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
