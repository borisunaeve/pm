"use client";

import clsx from "clsx";

export type FilterState = {
  search: string;
  priority: "" | "low" | "medium" | "high";
  label: string;
};

type FilterBarProps = {
  filter: FilterState;
  onChange: (f: FilterState) => void;
  allLabels: string[];
};

export const FilterBar = ({ filter, onChange, allLabels }: FilterBarProps) => {
  const hasFilter = filter.search || filter.priority || filter.label;

  return (
    <div className="flex flex-wrap items-center gap-3" data-testid="filter-bar">
      {/* Text search */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--gray-text)]"
          xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          value={filter.search}
          onChange={(e) => onChange({ ...filter, search: e.target.value })}
          placeholder="Search cards..."
          className="rounded-xl border border-[var(--stroke)] bg-white pl-9 pr-4 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)] w-52"
          data-testid="filter-search"
        />
      </div>

      {/* Priority filter */}
      <select
        value={filter.priority}
        onChange={(e) => onChange({ ...filter, priority: e.target.value as FilterState["priority"] })}
        className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        data-testid="filter-priority"
      >
        <option value="">All priorities</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>

      {/* Label filter */}
      {allLabels.length > 0 && (
        <select
          value={filter.label}
          onChange={(e) => onChange({ ...filter, label: e.target.value })}
          className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          data-testid="filter-label"
        >
          <option value="">All labels</option>
          {allLabels.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      )}

      {/* Clear */}
      {hasFilter && (
        <button
          onClick={() => onChange({ search: "", priority: "", label: "" })}
          className="rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition-colors"
          data-testid="filter-clear"
        >
          Clear
        </button>
      )}

      {hasFilter && (
        <span className="text-xs text-[var(--gray-text)]" data-testid="filter-active-indicator">
          Filtering
        </span>
      )}
    </div>
  );
};
