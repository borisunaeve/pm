"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import clsx from "clsx";
import * as api from "@/lib/api";

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-green-100 text-green-700",
};

type SearchOverlayProps = {
  onClose: () => void;
};

export const SearchOverlay = ({ onClose }: SearchOverlayProps) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<api.SearchResultCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const doSearch = useCallback(async (q: string, archived: boolean) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const data = await api.searchCards(q.trim(), archived);
      setResults(data);
      setSelectedIndex(0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      doSearch(query, includeArchived);
    }, 250);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, includeArchived, doSearch]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[selectedIndex]) {
      navigateTo(results[selectedIndex]);
    }
  };

  const navigateTo = (result: api.SearchResultCard) => {
    window.location.href = `/board?id=${result.board_id}`;
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center pt-[10vh] p-4 bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-xl flex flex-col overflow-hidden"
        style={{ maxHeight: "70vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-[var(--gray-text)] flex-shrink-0"
          >
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search cards across all boards..."
            className="flex-1 text-sm text-[var(--navy-dark)] outline-none bg-transparent placeholder:text-[var(--gray-text)]"
          />
          {loading && (
            <span className="text-xs text-[var(--gray-text)] flex-shrink-0 animate-pulse">
              Searching...
            </span>
          )}
          <kbd className="hidden sm:block rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-[10px] font-mono text-[var(--gray-text)] flex-shrink-0">
            Esc
          </kbd>
        </div>

        {/* Archived toggle */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-100 bg-gray-50/50">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-[var(--gray-text)]">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="rounded border-gray-300 accent-[var(--primary-blue)]"
            />
            Include archived cards
          </label>
        </div>

        {/* Results */}
        <div className="overflow-y-auto flex-1">
          {!query.trim() && (
            <div className="py-10 text-center text-sm text-[var(--gray-text)] italic">
              Type to search cards by title or description
            </div>
          )}

          {query.trim() && !loading && results.length === 0 && (
            <div className="py-10 text-center text-sm text-[var(--gray-text)] italic">
              No cards found for &ldquo;{query}&rdquo;
            </div>
          )}

          {results.length > 0 && (
            <ul className="py-2">
              {results.map((result, idx) => (
                <li key={result.id}>
                  <button
                    type="button"
                    onClick={() => navigateTo(result)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={clsx(
                      "w-full text-left px-4 py-3 flex items-start gap-3 transition-colors",
                      idx === selectedIndex
                        ? "bg-[var(--primary-blue)]/8"
                        : "hover:bg-gray-50"
                    )}
                  >
                    {/* Priority dot */}
                    <span
                      className={clsx(
                        "mt-1 flex-shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase",
                        PRIORITY_COLORS[result.priority] ?? "bg-gray-100 text-gray-600"
                      )}
                    >
                      {result.priority}
                    </span>

                    <div className="flex-1 min-w-0">
                      <p className={clsx(
                        "text-sm font-semibold truncate",
                        result.archived ? "line-through text-[var(--gray-text)]" : "text-[var(--navy-dark)]"
                      )}>
                        {result.title}
                        {result.archived && (
                          <span className="ml-2 text-[10px] font-normal normal-case no-underline bg-amber-100 text-amber-700 rounded-full px-1.5 py-0.5">
                            archived
                          </span>
                        )}
                      </p>
                      {result.details && (
                        <p className="mt-0.5 text-xs text-[var(--gray-text)] truncate">
                          {result.details}
                        </p>
                      )}
                      <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] font-semibold text-[var(--primary-blue)] bg-blue-50 rounded-full px-2 py-0.5">
                          {result.board_title}
                        </span>
                        <span className="text-[10px] text-[var(--gray-text)]">
                          {result.column_title}
                        </span>
                        {result.labels && result.labels.split(",").map((l) => l.trim()).filter(Boolean).map((label) => (
                          <span
                            key={label}
                            className="text-[10px] bg-purple-50 text-purple-700 rounded-full px-2 py-0.5 font-semibold"
                          >
                            {label}
                          </span>
                        ))}
                      </div>
                    </div>

                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={clsx(
                        "flex-shrink-0 mt-1 transition-opacity",
                        idx === selectedIndex ? "opacity-100 text-[var(--primary-blue)]" : "opacity-0"
                      )}
                    >
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer hint */}
        {results.length > 0 && (
          <div className="border-t border-gray-100 px-4 py-2 flex items-center gap-4 text-[10px] text-[var(--gray-text)]">
            <span><kbd className="font-mono">↑↓</kbd> navigate</span>
            <span><kbd className="font-mono">Enter</kbd> open board</span>
            <span><kbd className="font-mono">Esc</kbd> close</span>
            <span className="ml-auto">{results.length} result{results.length !== 1 ? "s" : ""}</span>
          </div>
        )}
      </div>
    </div>
  );
};
