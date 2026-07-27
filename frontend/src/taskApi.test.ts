import { afterEach, describe, expect, it, vi } from "vitest";

import { completeTask, createTask, fetchTasks, type Task } from "./taskApi";

const task: Task = {
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

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("task API", () => {
  it("lists persisted tasks", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([task]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchTasks()).resolves.toEqual([task]);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/tasks", undefined);
  });

  it("creates a task with exactly one explicit parent", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(task, 201));
    vi.stubGlobal("fetch", fetchMock);

    await createTask({
      title: "Call decision maker",
      due_date: "2026-07-30",
      business_id: "business-1"
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/tasks",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          title: "Call decision maker",
          due_date: "2026-07-30",
          business_id: "business-1"
        })
      })
    );
  });

  it("completes a task only through the explicit completion endpoint", async () => {
    const completed = { ...task, status: "completed" as const };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(completed));
    vi.stubGlobal("fetch", fetchMock);

    await expect(completeTask("task-1")).resolves.toEqual(completed);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/tasks/task-1/complete",
      { method: "PATCH" }
    );
  });
});
