import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { KanbanCard } from "@/components/KanbanCard";
import type { Card } from "@/lib/kanban";

// useSortable returns minimal no-op values so we can render without DnD context
vi.mock("@dnd-kit/sortable", () => ({
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: () => {},
    transform: null,
    transition: undefined,
    isDragging: false,
  }),
}));
vi.mock("@dnd-kit/utilities", () => ({
  CSS: { Transform: { toString: () => "" } },
}));

const makeCard = (overrides: Partial<Card> = {}): Card => ({
  id: "card-1",
  title: "Test card",
  details: "",
  priority: "medium",
  due_date: null,
  labels: "",
  ...overrides,
});

const noop = async () => {};

describe("KanbanCard due date display", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-05T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows no date badge when due_date is null", () => {
    render(<KanbanCard card={makeCard()} onDelete={noop} onUpdate={noop} />);
    expect(screen.queryByText(/overdue/i)).not.toBeInTheDocument();
  });

  it("shows overdue badge and red border for past due date", () => {
    render(
      <KanbanCard
        card={makeCard({ due_date: "2026-04-01" })}
        onDelete={noop}
        onUpdate={noop}
      />
    );
    expect(screen.getByText(/overdue/i)).toBeInTheDocument();
    const article = screen.getByTestId("card-card-1");
    expect(article.className).toMatch(/border-red/);
  });

  it("shows amber border for due date within 3 days", () => {
    render(
      <KanbanCard
        card={makeCard({ due_date: "2026-04-07" })}
        onDelete={noop}
        onUpdate={noop}
      />
    );
    const article = screen.getByTestId("card-card-1");
    expect(article.className).toMatch(/border-amber/);
    expect(screen.queryByText(/overdue/i)).not.toBeInTheDocument();
  });

  it("shows plain blue badge for future due date", () => {
    render(
      <KanbanCard
        card={makeCard({ due_date: "2026-05-01" })}
        onDelete={noop}
        onUpdate={noop}
      />
    );
    expect(screen.queryByText(/overdue/i)).not.toBeInTheDocument();
    const article = screen.getByTestId("card-card-1");
    expect(article.className).not.toMatch(/border-red/);
    expect(article.className).not.toMatch(/border-amber/);
  });
});

describe("KanbanCard priority badges", () => {
  it("shows priority badge", () => {
    render(<KanbanCard card={makeCard({ priority: "high" })} onDelete={noop} onUpdate={noop} />);
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("shows labels as chips", () => {
    render(
      <KanbanCard
        card={makeCard({ labels: "frontend, bug" })}
        onDelete={noop}
        onUpdate={noop}
      />
    );
    expect(screen.getByText("frontend")).toBeInTheDocument();
    expect(screen.getByText("bug")).toBeInTheDocument();
  });
});
