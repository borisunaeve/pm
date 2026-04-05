import { describe, it, expect, vi, beforeEach } from "vitest";
import { saveAuth, clearAuth, getToken, getUser, isLoggedIn } from "@/lib/api";

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
