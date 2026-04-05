/**
 * Typed API client — all calls go through here so JWT headers
 * are injected in one place.
 */

export type TokenPayload = {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
};

export type UserProfile = {
  id: string;
  username: string;
  created_at: string | null;
};

export type BoardSummary = {
  id: string;
  title: string;
  created_at: string | null;
  card_count: number;
};

export type Card = {
  id: string;
  title: string;
  details: string;
  priority: "low" | "medium" | "high";
  due_date: string | null | undefined;
  labels: string;
  checklist_total?: number;
  checklist_done?: number;
  assignee_id?: string | null;
  assignee_username?: string | null;
};

export type ActivityEntry = {
  id: number;
  board_id: string;
  user_id: string;
  username: string;
  action: string;
  entity_type: string;
  entity_title: string | null;
  created_at: string;
};

export type Column = {
  id: string;
  title: string;
  cardIds: string[];
  wip_limit?: number | null;
};

export type ChecklistItem = {
  id: string;
  title: string;
  checked: boolean;
  order: number;
};

export type Comment = {
  id: string;
  card_id: string;
  user_id: string;
  username: string;
  content: string;
  created_at: string;
};

export type BoardMember = {
  user_id: string;
  username: string;
  role: string;
  added_at: string;
};

export type BoardData = {
  columns: Column[];
  cards: Record<string, Card>;
};

// ── Token storage ──────────────────────────────────────────────────────────────

const TOKEN_KEY = "pm_token";
const USER_KEY = "pm_user";

export const saveAuth = (payload: TokenPayload) => {
  localStorage.setItem(TOKEN_KEY, payload.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify({ id: payload.user_id, username: payload.username }));
};

export const clearAuth = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const getToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const getUser = (): { id: string; username: string } | null => {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
};

export const isLoggedIn = (): boolean => !!getToken();

// ── Base fetcher ───────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });

  if (res.status === 401 || res.status === 403) {
    clearAuth();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ───────────────────────────────────────────────────────────────────────

export const login = (username: string, password: string) =>
  apiFetch<TokenPayload>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const register = (username: string, password: string) =>
  apiFetch<TokenPayload>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const getMe = () => apiFetch<UserProfile>("/api/auth/me");

export const changePassword = (current_password: string, new_password: string) =>
  apiFetch("/api/auth/password", {
    method: "PUT",
    body: JSON.stringify({ current_password, new_password }),
  });

// ── Boards ─────────────────────────────────────────────────────────────────────

export const listBoards = () => apiFetch<BoardSummary[]>("/api/boards");

export const createBoard = (title: string) =>
  apiFetch<BoardSummary>("/api/boards", { method: "POST", body: JSON.stringify({ title }) });

export const getBoard = (boardId: string) =>
  apiFetch<BoardData>(`/api/boards/${boardId}`);

export const updateBoard = (boardId: string, title: string) =>
  apiFetch(`/api/boards/${boardId}`, { method: "PUT", body: JSON.stringify({ title }) });

export const deleteBoard = (boardId: string) =>
  apiFetch(`/api/boards/${boardId}`, { method: "DELETE" });

// ── Columns ────────────────────────────────────────────────────────────────────

export const createColumn = (boardId: string, title: string) =>
  apiFetch<{ id: string; title: string }>("/api/columns", {
    method: "POST",
    body: JSON.stringify({ title, board_id: boardId }),
  });

export const updateColumn = (columnId: string, title: string, wip_limit?: number | null) =>
  apiFetch(`/api/columns/${columnId}`, { method: "PUT", body: JSON.stringify({ title, wip_limit }) });

export const deleteColumn = (columnId: string) =>
  apiFetch(`/api/columns/${columnId}`, { method: "DELETE" });

export const reorderColumns = (columnIds: string[]) =>
  apiFetch("/api/columns/reorder", { method: "POST", body: JSON.stringify({ column_ids: columnIds }) });

// ── Cards ──────────────────────────────────────────────────────────────────────

export const createCard = (params: {
  title: string;
  details?: string;
  column_id: string;
  priority?: string;
  due_date?: string;
  labels?: string;
}) => apiFetch<Card>("/api/cards", { method: "POST", body: JSON.stringify(params) });

export const updateCard = (
  cardId: string,
  params: {
    column_id: string;
    order: number;
    title?: string;
    details?: string;
    priority?: string;
    due_date?: string | null | undefined;
    labels?: string;
    assignee_id?: string | null;
  }
) => apiFetch(`/api/cards/${cardId}`, { method: "PUT", body: JSON.stringify(params) });

export const deleteCard = (cardId: string) =>
  apiFetch(`/api/cards/${cardId}`, { method: "DELETE" });

// ── Comments ───────────────────────────────────────────────────────────────────

export const listComments = (cardId: string) =>
  apiFetch<Comment[]>(`/api/cards/${cardId}/comments`);

export const createComment = (cardId: string, content: string) =>
  apiFetch<Comment>(`/api/cards/${cardId}/comments`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });

export const deleteComment = (cardId: string, commentId: string) =>
  apiFetch(`/api/cards/${cardId}/comments/${commentId}`, { method: "DELETE" });

// ── Checklist ──────────────────────────────────────────────────────────────────

export const listChecklist = (cardId: string) =>
  apiFetch<ChecklistItem[]>(`/api/cards/${cardId}/checklist`);

export const createChecklistItem = (cardId: string, title: string) =>
  apiFetch<ChecklistItem>(`/api/cards/${cardId}/checklist`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });

export const updateChecklistItem = (
  cardId: string,
  itemId: string,
  updates: { title?: string; checked?: boolean }
) =>
  apiFetch<ChecklistItem>(`/api/cards/${cardId}/checklist/${itemId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });

export const deleteChecklistItem = (cardId: string, itemId: string) =>
  apiFetch(`/api/cards/${cardId}/checklist/${itemId}`, { method: "DELETE" });

// ── Sharing ────────────────────────────────────────────────────────────────────

export const listMembers = (boardId: string) =>
  apiFetch<BoardMember[]>(`/api/boards/${boardId}/members`);

export const addMember = (boardId: string, username: string) =>
  apiFetch(`/api/boards/${boardId}/members`, {
    method: "POST",
    body: JSON.stringify({ username }),
  });

export const removeMember = (boardId: string, userId: string) =>
  apiFetch(`/api/boards/${boardId}/members/${userId}`, { method: "DELETE" });

// ── Export ─────────────────────────────────────────────────────────────────────

export const exportBoard = async (boardId: string, format: "json" | "csv") => {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`/api/boards/${boardId}/export?format=${format}`, { headers });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `board-${boardId}.${format}`;
  a.click();
  URL.revokeObjectURL(url);
};

// ── Activity ───────────────────────────────────────────────────────────────────

export const getBoardActivity = (boardId: string, limit = 50) =>
  apiFetch<ActivityEntry[]>(`/api/boards/${boardId}/activity?limit=${limit}`);

// ── AI Chat ────────────────────────────────────────────────────────────────────

export const aiChat = (
  boardId: string,
  messages: { role: string; content: string }[]
) =>
  apiFetch<{ status: string; message: string; actions: unknown[] }>(
    `/api/ai/chat/${boardId}`,
    { method: "POST", body: JSON.stringify({ messages }) }
  );
