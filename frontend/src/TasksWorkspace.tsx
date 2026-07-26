import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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

type TaskCreatePayload = {
  title: string;
  due_date: string | null;
  business_id?: string;
  deal_id?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, init);
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
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

export function TaskCreate({
  businessId,
  dealId,
  label = "Create task"
}: {
  businessId?: string;
  dealId?: string;
  label?: string;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const mutation = useMutation({
    mutationFn: () => createTask({
      title,
      due_date: dueDate || null,
      ...(businessId ? { business_id: businessId } : { deal_id: dealId })
    }),
    onSuccess: async () => {
      setTitle("");
      setDueDate("");
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
    }
  });
  const canSubmit = title.trim().length > 0 && title.trim().length <= 300;

  return (
    <section className="task-create" aria-label={label}>
      <h4>{label}</h4>
      <div className="deal-form-grid">
        <label>Task title<input value={title} maxLength={300} disabled={mutation.isPending} onChange={(event) => setTitle(event.target.value)} /></label>
        <label>Due date<input type="date" value={dueDate} disabled={mutation.isPending} onChange={(event) => setDueDate(event.target.value)} /></label>
      </div>
      <button className="secondary-action compact" disabled={!canSubmit || mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? "Creating…" : "Create task"}</button>
      {mutation.isSuccess && <div className="notice success" role="status">Task created.</div>}
      {mutation.isError && <div className="notice error" role="alert">Task could not be created. Your entered values are retained.</div>}
    </section>
  );
}

function TaskCard({ task }: { task: Task }) {
  const queryClient = useQueryClient();
  const completion = useMutation({
    mutationFn: () => completeTask(task.id),
    onSuccess: async (updated) => {
      queryClient.setQueryData<Task[]>(["tasks"], (current) =>
        current?.map((item) => item.id === updated.id ? updated : item) ?? [updated]
      );
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
    }
  });

  return (
    <article className="record-card task-card">
      <span className="badge neutral">{task.parent_type}</span>
      <h3>{task.title}</h3>
      <p>{task.parent_name}</p>
      <small>{task.due_date ? `Due ${new Date(`${task.due_date}T00:00:00`).toLocaleDateString()}` : "No due date"}</small>
      {task.status === "open" && <button className="primary-action compact" disabled={completion.isPending} onClick={() => completion.mutate()}>{completion.isPending ? "Completing…" : "Mark completed"}</button>}
      {completion.isError && <div className="notice error" role="alert">Task could not be completed.</div>}
    </article>
  );
}

export function TasksWorkspace() {
  const tasks = useQuery({ queryKey: ["tasks"], queryFn: fetchTasks });
  if (tasks.isPending) return <div className="notice">Loading tasks…</div>;
  if (tasks.isError) return <div className="notice error">Tasks could not be loaded.</div>;

  const open = tasks.data.filter((task) => task.status === "open");
  const completed = tasks.data.filter((task) => task.status === "completed");
  return (
    <section className="task-workspace" aria-label="Tasks workspace">
      <section aria-label="Open tasks">
        <div className="panel-heading"><div><h2>Open tasks</h2><p>{open.length} explicit follow-up actions</p></div></div>
        <div className="card-grid">{open.map((task) => <TaskCard key={task.id} task={task} />)}{open.length === 0 && <div className="empty-state">No open tasks.</div>}</div>
      </section>
      <section aria-label="Completed tasks">
        <div className="panel-heading"><div><h2>Completed tasks</h2><p>{completed.length} completed actions</p></div></div>
        <div className="card-grid">{completed.map((task) => <TaskCard key={task.id} task={task} />)}{completed.length === 0 && <div className="empty-state">No completed tasks.</div>}</div>
      </section>
    </section>
  );
}
