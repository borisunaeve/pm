"use client";

import { useState, useEffect } from "react";
import * as api from "@/lib/api";

type Props = {
  boardId: string;
  onClose: () => void;
};

export const ShareDialog = ({ boardId, onClose }: Props) => {
  const [members, setMembers] = useState<api.BoardMember[]>([]);
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    api.listMembers(boardId).then(setMembers).finally(() => setLoading(false));
  }, [boardId]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;
    setAdding(true);
    setError("");
    try {
      await api.addMember(boardId, username.trim());
      const updated = await api.listMembers(boardId);
      setMembers(updated);
      setUsername("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add member");
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (userId: string) => {
    await api.removeMember(boardId, userId);
    setMembers((prev) => prev.filter((m) => m.user_id !== userId));
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
        <h3 className="font-display font-semibold text-[var(--navy-dark)] text-lg mb-4">Share Board</h3>

        <form onSubmit={handleAdd} className="flex gap-2 mb-4">
          <input
            value={username}
            onChange={(e) => { setUsername(e.target.value); setError(""); }}
            placeholder="Username to invite..."
            className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            autoFocus
          />
          <button
            type="submit"
            disabled={adding || !username.trim()}
            className="rounded-xl bg-[var(--primary-blue)] px-4 py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-60 transition"
          >
            {adding ? "..." : "Invite"}
          </button>
        </form>

        {error && <p className="text-sm text-red-500 mb-3">{error}</p>}

        {loading ? (
          <p className="text-sm text-[var(--gray-text)]">Loading members...</p>
        ) : members.length === 0 ? (
          <p className="text-sm text-[var(--gray-text)] italic">No shared members yet.</p>
        ) : (
          <ul className="space-y-2 max-h-48 overflow-y-auto">
            {members.map((m) => (
              <li key={m.user_id} className="flex items-center justify-between rounded-xl bg-gray-50 px-4 py-2">
                <div>
                  <span className="text-sm font-semibold text-[var(--navy-dark)]">{m.username}</span>
                  <span className="ml-2 text-xs text-[var(--gray-text)] capitalize">{m.role}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemove(m.user_id)}
                  className="text-xs text-[var(--gray-text)] hover:text-red-500 transition"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}

        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-xl border border-gray-200 py-2.5 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition"
        >
          Close
        </button>
      </div>
    </div>
  );
};
