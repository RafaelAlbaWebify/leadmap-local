import { fetchDashboard } from "./api";
import type { Deal, DealStage } from "./dealApi";
import type { Task } from "./taskApi";

export const dealStages: Array<{ value: DealStage; label: string }> = [
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
