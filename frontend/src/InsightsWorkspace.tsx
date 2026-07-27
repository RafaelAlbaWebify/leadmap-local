import { useQuery } from "@tanstack/react-query";

import { fetchDashboard } from "./api";
import { fetchDeals } from "./dealApi";
import { dealStages, deriveInsights } from "./insightsModel";
import { fetchTasks } from "./taskApi";

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
