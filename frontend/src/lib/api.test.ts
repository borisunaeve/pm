import { describe, it, expect, vi, beforeEach } from "vitest";
import { saveAuth, clearAuth, getToken, getUser, isLoggedIn } from "@/lib/api";
import type { DashboardCard, PersistentNotification, BoardSummary } from "@/lib/api";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

describe("Auth token helpers", () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it("saveAuth stores token and user", () => {
    saveAuth({ access_token: "tok123", token_type: "bearer", user_id: "u1", username: "alice" });
    expect(getToken()).toBe("tok123");
    expect(getUser()).toEqual({ id: "u1", username: "alice" });
  });

  it("isLoggedIn returns true after saveAuth", () => {
    expect(isLoggedIn()).toBe(false);
    saveAuth({ access_token: "tok", token_type: "bearer", user_id: "u1", username: "alice" });
    expect(isLoggedIn()).toBe(true);
  });

  it("clearAuth removes token and user", () => {
    saveAuth({ access_token: "tok", token_type: "bearer", user_id: "u1", username: "alice" });
    clearAuth();
    expect(getToken()).toBeNull();
    expect(getUser()).toBeNull();
    expect(isLoggedIn()).toBe(false);
  });

  it("getUser returns null when no user stored", () => {
    expect(getUser()).toBeNull();
  });

  it("getToken returns null when not logged in", () => {
    expect(getToken()).toBeNull();
  });
});

describe("Type shapes", () => {
  it("DashboardCard has required fields", () => {
    const card: DashboardCard = {
      id: "c1", title: "Fix bug", priority: "high",
      due_date: "2026-04-10", labels: "frontend",
      board_id: "b1", board_title: "My Board",
      column_id: "col1", column_title: "In Progress",
      checklist_total: 3, checklist_done: 1,
    };
    expect(card.board_title).toBe("My Board");
    expect(card.column_title).toBe("In Progress");
    expect(card.checklist_total).toBe(3);
  });

  it("PersistentNotification has read field", () => {
    const notif: PersistentNotification = {
      id: 1, user_id: "u1", board_id: "b1", card_id: "c1",
      type: "card_updated", message: "Alice updated task",
      read: false, created_at: "2026-04-06T10:00:00",
    };
    expect(notif.read).toBe(false);
    expect(notif.type).toBe("card_updated");
  });

  it("BoardSummary includes color and description fields", () => {
    const board: BoardSummary = {
      id: "b1", title: "Test Board", description: "A test",
      color: "#209dd7", created_at: null, card_count: 5, member_count: 2,
    };
    expect(board.color).toBe("#209dd7");
    expect(board.description).toBe("A test");
    expect(board.member_count).toBe(2);
  });

  it("BoardSummary allows null color", () => {
    const board: BoardSummary = {
      id: "b1", title: "No Color", description: "",
      color: null, created_at: null, card_count: 0, member_count: 0,
    };
    expect(board.color).toBeNull();
  });
});
