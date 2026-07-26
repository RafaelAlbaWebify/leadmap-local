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

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
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

describe("task workflow", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("creates a business task and clears only after success", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(openTask, 201)
    );
    renderWithClient(<TaskCreate businessId="business-1" />);

    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "Call decision maker" }
    });
    fireEvent.change(screen.getByLabelText("Due date"), {
      target: { value: "2026-07-30" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Task title")).toHaveValue("");
      expect(screen.getByLabelText("Due date")).toHaveValue("");
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/tasks",
      expect.objectContaining({ method: "POST" })
    );
    const request = fetchMock.mock.calls[0][1];
    expect(JSON.parse(String(request?.body))).toEqual({
      title: "Call decision maker",
      due_date: "2026-07-30",
      business_id: "business-1"
    });
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
      .mockResolvedValueOnce(jsonResponse([openTask]))
      .mockResolvedValueOnce(jsonResponse(completed));
    renderWithClient(<TasksWorkspace />);

    const open = await screen.findByRole("region", { name: "Open tasks" });
    fireEvent.click(within(open).getByRole("button", { name: "Mark completed" }));

    const completedRegion = await screen.findByRole("region", {
      name: "Completed tasks"
    });
    expect(await within(completedRegion).findByText("Call decision maker")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/tasks/task-1/complete",
      expect.objectContaining({ method: "PATCH" })
    );
  });
});
