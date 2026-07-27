import { useQuery } from "@tanstack/react-query";

import { fetchDashboard } from "./api";
import { fetchDeals, type Deal, type DealStage } from "./dealApi";
import { fetchTasks, type Task } from "./taskApi";

const dealStages: Array<{ value: DealStage; label: string }> = [
  { value: "lead", label: "Lead" },
  { value: "discovery", label: "Discovery" },
  { value: "proposal", label: "Proposal" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" }
];

type Dashboard = Awaited<ReturnType<typeof fetchDashboard>>;

export type InsightsSummary = {
  metrics: Array<{ label: string; value: string; hint: string }>;
  stageCounts: Record<DealStage, number>;
  taskParentCounts: { business: number; deal: number };
  overdueTasks: Task[];
  actionDeals: Deal[];
};

function formatMoney(valueEurCents: number): string {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR"
  }).format(valueEurCents / 100);
}

export function deriveInsights(
  dashboard: Dashboard,
  deals: Deal[],
  tasks: Task[],
  today: string
): InsightsSummary {
  const stageCounts = Object.fromEntries(dealStages.map(({ value }) => [value, 0])) as Record<DealStage, number>;
  for (const deal of deals) stageCounts[deal.stage] += 1;

  const openTasks = tasks.filter((task) => task.status === "open");
  const completedTasks = tasks.filter((task) => task.status === "completed");
  const taskParentCounts = {
    business: openTasks.filter((task) => task.parent_type === "business").length,
    deal: openTasks.filter((task) => task.parent_type === "deal").length
  };
  const pipelineValue = deals.reduce((total, deal) => total + (deal.value_eur_cents ?? 0), 0);

  return {
    metrics: [
      { label: "BUSINESSES", value: String(dashboard.total_businesses), hint: "persisted records" },
      { label: "QUALIFIED", value: String(dashboard.qualified_leads), hint: "ready for action" },
      { label: "NEEDS REVIEW", value: String(dashboard.needs_review), hint: "research queue" },
      { label: "OPEN TASKS", value: String(openTasks.length), hint: "current follow-up" },
      { label: "COMPLETED TASKS", value: String(completedTasks.length), hint: "explicitly completed" },
      { label: "DEALS", value: String(deals.length), hint: "persisted opportunities" },
      { label: "ENTERED VALUE", value: formatMoney(pipelineValue), hint: "not forecast revenue" }
    ],
    stageCounts,
    taskParentCounts,
    overdueTasks: openTasks
      .filter((task) => task.due_date !== null && task.due_date < today)
      .sort((left, right) => (left.due_date ?? "").localeCompare(right.due_date ?? "")),
    actionDeals: deals
      .filter((deal) => Boolean(deal.next_action?.trim()))
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
      .slice(0, 5)
  };
}

function localDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function InsightsWorkspace() {
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: fetchDashboard });
  const deals = useQuery({ queryKey: ["deals"], queryFn: fetchDeals });
  const tasks = useQuery({ queryKey: ["tasks"], queryFn: fetchTasks });

  if (dashboard.isPending || deals.isPending || tasks.isPending) {
    return <section className="panel page-panel"><div className="empty-state">Loading operational insights…</div></section>;
  }

  if (dashboard.isError || deals.isError || tasks.isError) {
    return <section className="panel page-panel"><div className="notice error">Operational insights could not be loaded.</div></section>;
  }

  const summary = deriveInsights(dashboard.data, deals.data, tasks.data, localDate());

  return (
    <section className="insights-workspace" aria-label="Operational insights">
      <div className="panel-heading insights-heading">
        <div><h2>Operational overview</h2><p>Current persisted state only. No inferred forecasts or attribution.</p></div>
        <span className="badge neutral">Live records</span>
      </div>

      <div className="insights-metrics">
        {summary.metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <div className="metric-label">{metric.label}</div>
            <div className="metric-value">{metric.value}</div>
            <div className="metric-hint">{metric.hint}</div>
          </article>
        ))}
      </div>

      <div className="insights-grid">
        <section className="panel" aria-label="Deal stage distribution">
          <div className="panel-heading"><div><h2>Deal stages</h2><p>{deals.data.length} persisted deals</p></div></div>
          <div className="distribution-list">
            {dealStages.map((stage) => (
              <div className="distribution-row" key={stage.value}>
                <span>{stage.label}</span><strong>{summary.stageCounts[stage.value]}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="panel" aria-label="Open task distribution">
          <div className="panel-heading"><div><h2>Open tasks</h2><p>Grouped by exact persisted parent</p></div></div>
          <div className="distribution-list">
            <div className="distribution-row"><span>Business tasks</span><strong>{summary.taskParentCounts.business}</strong></div>
            <div className="distribution-row"><span>Deal tasks</span><strong>{summary.taskParentCounts.deal}</strong></div>
          </div>
        </section>
      </div>

      <section className="panel attention-panel" aria-label="Attention list">
        <div className="panel-heading"><div><h2>Needs attention</h2><p>Overdue open tasks and explicit deal next actions</p></div></div>
        <div className="attention-grid">
          <div>
            <h3>Overdue tasks</h3>
            {summary.overdueTasks.map((task) => (
              <article className="attention-item" key={task.id}>
                <strong>{task.title}</strong><span>{task.parent_name}</span><small>Due {task.due_date}</small>
              </article>
            ))}
            {summary.overdueTasks.length === 0 && <div className="empty-state compact-empty">No overdue open tasks.</div>}
          </div>
          <div>
            <h3>Deal next actions</h3>
            {summary.actionDeals.map((deal) => (
              <article className="attention-item" key={deal.id}>
                <strong>{deal.title}</strong><span>{deal.business_name}</span><small>{deal.next_action}</small>
              </article>
            ))}
            {summary.actionDeals.length === 0 && <div className="empty-state compact-empty">No deal next actions recorded.</div>}
          </div>
        </div>
      </section>
    </section>
  );
}
