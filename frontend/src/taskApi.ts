export type Task = {
  id: string;
  title: string;
  due_date: string | null;
  status: "open" | "completed";
  business_id: string | null;
  deal_id: string | null;
  parent_type: "business" | "deal";
  parent_name: string;
  created_at: string;
  updated_at: string;
};

export type TaskCreatePayload = {
  title: string;
  due_date: string | null;
  business_id?: string;
  deal_id?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, init);
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchTasks(): Promise<Task[]> {
  return request<Task[]>("/tasks");
}

export function createTask(payload: TaskCreatePayload): Promise<Task> {
  return request<Task>("/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export function completeTask(taskId: string): Promise<Task> {
  return request<Task>(`/tasks/${taskId}/complete`, { method: "PATCH" });
}
