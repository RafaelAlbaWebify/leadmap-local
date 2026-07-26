import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TaskCreate, TasksWorkspace } from "./TasksWorkspace";
import type { Task } from "./taskApi";

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
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

describe("task workflow", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("creates a business task and clears only after success", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(openTask), {
        status: 201,
        headers: { "Content-Type": "application/json" }
      })
    );
    renderWithClient(<TaskCreate businessId="business-1" />);
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "Call decision maker" }
    });
    fireEvent.change(screen.getByLabelText("Due date"), {
      target: { value: "2026-07-30" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      title: "Call decision maker",
      due_date: "2026-07-30",
      business_id: "business-1"
    });
    expect(screen.getByLabelText("Task title")).toHaveValue("");
    expect(screen.getByLabelText("Due date")).toHaveValue("");
  });

  it("retains entered task values after failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("failed", { status: 500 }));
    renderWithClient(<TaskCreate dealId="deal-1" />);
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "Review proposal" }
    });
    fireEvent.change(screen.getByLabelText("Due date"), {
      target: { value: "2026-08-01" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your entered values are retained"
    );
    expect(screen.getByLabelText("Task title")).toHaveValue("Review proposal");
    expect(screen.getByLabelText("Due date")).toHaveValue("2026-08-01");
  });

  it("groups tasks and completes only after an explicit action", async () => {
    const completed: Task = {
      ...openTask,
      status: "completed",
      updated_at: "2026-07-26T13:00:00Z"
    };
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([openTask]), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify(completed), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }))
      .mockResolvedValue(new Response(JSON.stringify([completed]), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }));
    renderWithClient(<TasksWorkspace />);
    const open = await screen.findByRole("region", { name: "Open tasks" });
    fireEvent.click(within(open).getByRole("button", { name: "Mark completed" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/tasks/task-1/complete");
    const completedRegion = await screen.findByRole("region", {
      name: "Completed tasks"
    });
    expect(within(completedRegion).getByText("Call decision maker")).toBeInTheDocument();
  });
});
