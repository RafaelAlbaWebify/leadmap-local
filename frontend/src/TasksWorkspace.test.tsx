import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TaskCreate, TasksWorkspace } from "./TasksWorkspace";
import type { Task } from "./taskApi";

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" }
  });
}

const openTask: Task = {
  id: "task-1",
  title: "Call decision maker",
  due_date: "2026-07-30",
  status: "open",
  business_id: "business-1",
  deal_id: null,
  parent_type: "business",
  parent_name: "Kildare Accountancy",
  created_at: "2026-07-26T12:00:00Z",
  updated_at: "2026-07-26T12:00:00Z"
};

const completedTask: Task = {
  ...openTask,
  id: "task-2",
  title: "Review signed proposal",
  status: "completed",
  business_id: null,
  deal_id: "deal-1",
  parent_type: "deal",
  parent_name: "Website redesign"
};

afterEach(() => vi.unstubAllGlobals());

describe("task workspace", () => {
  it("renders explicit business task fields", () => {
    renderWithClient(<TaskCreate businessId="business-1" />);

    expect(screen.getByRole("region", { name: "Create task" })).toBeInTheDocument();
    expect(screen.getByLabelText("Task title")).toBeInTheDocument();
    expect(screen.getByLabelText("Due date")).toHaveAttribute("type", "date");
    expect(screen.getByRole("button", { name: "Create task" })).toBeDisabled();
  });

  it("groups persisted open and completed tasks", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([openTask, completedTask])));
    renderWithClient(<TasksWorkspace />);

    const open = await screen.findByRole("region", { name: "Open tasks" });
    expect(within(open).getByText("Call decision maker")).toBeInTheDocument();
    expect(within(open).getByText("Kildare Accountancy")).toBeInTheDocument();
    expect(within(open).getByRole("button", { name: "Mark completed" })).toBeInTheDocument();

    const completed = screen.getByRole("region", { name: "Completed tasks" });
    expect(within(completed).getByText("Review signed proposal")).toBeInTheDocument();
    expect(within(completed).getByText("Website redesign")).toBeInTheDocument();
    expect(within(completed).queryByRole("button", { name: "Mark completed" })).not.toBeInTheDocument();
  });
});
