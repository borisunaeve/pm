import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, beforeEach } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";

const BOARD_ID = "board-test-1";

const mockBoardData = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-progress", title: "In Progress", cardIds: [] },
    { id: "col-done", title: "Done", cardIds: [] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Align roadmap themes", details: "Some details", priority: "medium", due_date: null, labels: "" },
    "card-2": { id: "card-2", title: "Gather customer signals", details: "", priority: "high", due_date: null, labels: "research" },
  },
};

const mockBoardsSummary = [{ id: BOARD_ID, title: "Test Board", created_at: null, card_count: 2 }];

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

const mockFetch = vi.fn((url: string, options?: RequestInit) => {
  // Auth token (simulated)
  localStorageMock.setItem("pm_token", "mock-token");
  localStorageMock.setItem("pm_user", JSON.stringify({ id: "user-1", username: "testuser" }));

  if (url === `/api/boards/${BOARD_ID}`) {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockBoardData),
    } as Response);
  }
  if (url === "/api/boards") {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockBoardsSummary),
    } as Response);
  }
  if (options?.method === "POST" && url === "/api/cards") {
    const body = JSON.parse(options.body as string);
    return Promise.resolve({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({
          id: "card-new-test",
          title: body.title,
          details: body.details || "",
          column_id: body.column_id,
          priority: "medium",
          due_date: null,
          labels: "",
        }),
    } as Response);
  }
  if (options?.method === "POST" && url === "/api/columns") {
    const body = JSON.parse(options.body as string);
    return Promise.resolve({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ id: "col-new", title: body.title, board_id: body.board_id, order: 3 }),
    } as Response);
  }
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ status: "success" }),
  } as Response);
}) as unknown as typeof fetch;

beforeEach(() => {
  global.fetch = mockFetch;
  mockFetch.mockClear();
  localStorageMock.setItem("pm_token", "mock-token");
  localStorageMock.setItem("pm_user", JSON.stringify({ id: "user-1", username: "testuser" }));
});

const getFirstColumn = async () => (await screen.findAllByTestId(/column-/i))[0];

describe("KanbanBoard", () => {
  it("renders columns from API", async () => {
    render(<KanbanBoard boardId={BOARD_ID} />);
    const cols = await screen.findAllByTestId(/column-/i);
    expect(cols.length).toBeGreaterThanOrEqual(1);
  });

  it("shows card titles", async () => {
    render(<KanbanBoard boardId={BOARD_ID} />);
    expect(await screen.findByText("Align roadmap themes")).toBeInTheDocument();
    expect(await screen.findByText("Gather customer signals")).toBeInTheDocument();
  });

  it("renames a column", async () => {
    render(<KanbanBoard boardId={BOARD_ID} />);
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds a card", async () => {
    render(<KanbanBoard boardId={BOARD_ID} />);
    const column = await getFirstColumn();
    const addButton = within(column).getByRole("button", { name: /add a card/i });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();
  });

  it("shows priority badge on cards", async () => {
    render(<KanbanBoard boardId={BOARD_ID} />);
    // "high" priority badge should appear for card-2
    expect(await screen.findByText("high")).toBeInTheDocument();
  });

  it("shows labels on cards", async () => {
    render(<KanbanBoard boardId={BOARD_ID} />);
    expect(await screen.findByText("research")).toBeInTheDocument();
  });
});
