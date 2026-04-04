import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, beforeEach } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

const mockFetch = vi.fn((url: string, options?: RequestInit) => {
  if (url === "/api/board") {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(initialData),
    } as Response);
  }
  if (options?.method === "POST" && url === "/api/cards") {
    const body = JSON.parse(options.body as string);
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          id: "card-test-new",
          title: body.title,
          details: body.details,
          column_id: body.column_id,
        }),
    } as Response);
  }
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ status: "success" }),
  } as Response);
}) as unknown as typeof fetch;

beforeEach(() => {
  global.fetch = mockFetch;
  mockFetch.mockClear();
});

const getFirstColumn = async () => (await screen.findAllByTestId(/column-/i))[0];

describe("KanbanBoard", () => {
  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});
