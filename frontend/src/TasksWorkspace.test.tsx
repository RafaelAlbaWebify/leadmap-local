import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TaskCreate, TasksWorkspace } from "./TasksWorkspace";
import * as taskApi from "./taskApi";
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
    const create = vi.spyOn(taskApi, "createTask").mockResolvedValue(openTask);
    renderWithClient(<TaskCreate businessId="business-1" />);

    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "Call decision maker" }
    });
    fireEvent.change(screen.getByLabelText("Due date"), {
      target: { value: "2026-07-30" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() => expect(create).toHaveBeenCalledWith({
      title: "Call decision maker",
      due_date: "2026-07-30",
      business_id: "business-1"
    }));
    expect(await screen.findByRole("status")).toHaveTextContent("Task created.");
    expect(screen.getByLabelText("Task title")).toHaveValue("");
    expect(screen.getByLabelText("Due date")).toHaveValue("");
  });

  it("retains entered task values after failure", async () => {
    vi.spyOn(taskApi, "createTask").mockRejectedValue(new Error("failed"));
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
    vi.spyOn(taskApi, "fetchTasks").mockResolvedValue([openTask]);
    const complete = vi.spyOn(taskApi, "completeTask").mockResolvedValue(completed);
    renderWithClient(<TasksWorkspace />);

    const open = await screen.findByRole("region", { name: "Open tasks" });
    fireEvent.click(within(open).getByRole("button", { name: "Mark completed" }));

    await waitFor(() => expect(complete).toHaveBeenCalledWith("task-1"));
    const completedRegion = await screen.findByRole("region", {
      name: "Completed tasks"
    });
    expect(await within(completedRegion).findByText("Call decision maker")).toBeInTheDocument();
  });
});
