"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import type { BoardData } from "@/lib/kanban";
import { FilterState } from "@/components/FilterBar";

const PRIORITY_DOT: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-amber-400",
  low: "bg-green-500",
};

type CalendarViewProps = {
  board: BoardData;
  filters: FilterState;
  onCardClick: (cardId: string) => void;
};

export function CalendarView({ board, filters, onCardClick }: CalendarViewProps) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth()); // 0-indexed

  const todayStr = today.toISOString().split("T")[0];

  // Filter cards to only those with due dates
  const cardsByDate = useMemo(() => {
    const q = filters.search.toLowerCase();
    const map: Record<string, typeof board.cards[string][]> = {};
    Object.values(board.cards).forEach((c) => {
      if (!c.due_date) return;
      if (q && !c.title.toLowerCase().includes(q) && !(c.details || "").toLowerCase().includes(q)) return;
      if (filters.priority && c.priority !== filters.priority) return;
      if (filters.label) {
        const cardLabels = (c.labels || "").split(",").map((l) => l.trim());
        if (!cardLabels.includes(filters.label)) return;
      }
      const key = c.due_date;
      map[key] = map[key] ?? [];
      map[key].push(c);
    });
    return map;
  }, [board.cards, filters]);

  // Build calendar grid
  const weeks = useMemo(() => {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDow = firstDay.getDay(); // 0=Sun

    const days: (Date | null)[] = [];
    for (let i = 0; i < startDow; i++) days.push(null);
    for (let d = 1; d <= lastDay.getDate(); d++) days.push(new Date(year, month, d));
    // Pad to full weeks
    while (days.length % 7 !== 0) days.push(null);

    const result: (Date | null)[][] = [];
    for (let i = 0; i < days.length; i += 7) result.push(days.slice(i, i + 7));
    return result;
  }, [year, month]);

  const monthName = new Date(year, month, 1).toLocaleString("default", { month: "long", year: "numeric" });
  const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  const prevMonth = () => {
    if (month === 0) { setYear(y => y - 1); setMonth(11); }
    else setMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (month === 11) { setYear(y => y + 1); setMonth(0); }
    else setMonth(m => m + 1);
  };

  const totalWithDates = Object.values(board.cards).filter((c) => c.due_date).length;

  return (
    <div className="space-y-4">
      {/* Month nav */}
      <div className="flex items-center justify-between rounded-2xl border border-[var(--stroke)] bg-white px-5 py-3">
        <button
          type="button"
          onClick={prevMonth}
          className="rounded-xl border border-[var(--stroke)] p-2 hover:bg-gray-50 transition"
          aria-label="Previous month"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="text-center">
          <p className="font-display font-semibold text-[var(--navy-dark)] text-lg">{monthName}</p>
          <p className="text-[11px] text-[var(--gray-text)]">{totalWithDates} card{totalWithDates !== 1 ? "s" : ""} with due dates</p>
        </div>
        <button
          type="button"
          onClick={nextMonth}
          className="rounded-xl border border-[var(--stroke)] p-2 hover:bg-gray-50 transition"
          aria-label="Next month"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      {/* Calendar grid */}
      <div className="rounded-2xl border border-[var(--stroke)] bg-white overflow-hidden">
        {/* Day-of-week headers */}
        <div className="grid grid-cols-7 border-b border-[var(--stroke)]">
          {DOW.map((d) => (
            <div key={d} className="py-2 text-center text-[11px] font-semibold text-[var(--gray-text)] uppercase tracking-wide">
              {d}
            </div>
          ))}
        </div>

        {/* Weeks */}
        {weeks.map((week, wi) => (
          <div key={wi} className="grid grid-cols-7 border-b border-[var(--stroke)] last:border-b-0">
            {week.map((day, di) => {
              if (!day) {
                return <div key={di} className="min-h-[100px] border-r border-[var(--stroke)] last:border-r-0 bg-gray-50/40" />;
              }
              const dateStr = day.toISOString().split("T")[0];
              const cards = cardsByDate[dateStr] ?? [];
              const isToday = dateStr === todayStr;
              const isPast = dateStr < todayStr;

              return (
                <div
                  key={di}
                  className={clsx(
                    "min-h-[100px] border-r border-[var(--stroke)] last:border-r-0 p-1.5",
                    isPast && !isToday && "bg-gray-50/60",
                    isToday && "bg-blue-50/40"
                  )}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={clsx(
                      "text-xs font-semibold w-6 h-6 flex items-center justify-center rounded-full",
                      isToday ? "bg-[var(--primary-blue)] text-white" : "text-[var(--navy-dark)]",
                      isPast && !isToday && "text-[var(--gray-text)]"
                    )}>
                      {day.getDate()}
                    </span>
                    {cards.length > 0 && (
                      <span className="text-[9px] text-[var(--gray-text)] font-medium">{cards.length}</span>
                    )}
                  </div>
                  <div className="space-y-1">
                    {cards.slice(0, 3).map((card) => (
                      <button
                        key={card.id}
                        type="button"
                        onClick={() => onCardClick(card.id)}
                        className={clsx(
                          "w-full text-left px-1.5 py-1 rounded-lg text-[10px] font-medium transition-all",
                          "hover:opacity-80 truncate flex items-center gap-1",
                          isPast ? "bg-red-100 text-red-800" : "bg-[#209dd7]/10 text-[#209dd7]"
                        )}
                        style={card.color ? { backgroundColor: card.color + "22", color: card.color } : {}}
                        title={card.title}
                      >
                        <span
                          className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0", PRIORITY_DOT[card.priority ?? "medium"])}
                        />
                        <span className="truncate">{card.title}</span>
                      </button>
                    ))}
                    {cards.length > 3 && (
                      <p className="text-[9px] text-[var(--gray-text)] pl-1">+{cards.length - 3} more</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
