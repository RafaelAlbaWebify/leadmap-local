import { describe, expect, it } from "vitest";

import type { Deal } from "./dealApi";
import { deriveInsights } from "./insightsModel";
import type { Task } from "./taskApi";

const dashboard = {
  total_businesses: 8,
  qualified_leads: 3,
  needs_review: 2,
  stale_records: 1,
  territories: 4,
  recent_leads: []
};

const deals: Deal[] = [
  {
    id: "deal-1",
    business_id: "business-1",
    business_name: "Galway Dental",
    title: "SEO retainer",
    stage: "proposal",
    value_eur_cents: 720000,
    next_action: "Send tailored audit",
    created_at: "2026-07-24T10:00:00Z",
    updated_at: "2026-07-27T09:00:00Z"
  },
  {
    id: "deal-2",
    business_id: "business-2",
    business_name: "Kildare Accountancy",
    title: "Website redesign",
    stage: "won",
    value_eur_cents: null,
    next_action: null,
    created_at: "2026-07-25T13:10:00Z",
    updated_at: "2026-07-25T13:10:00Z"
  }
];

const tasks: Task[] = [
  {
    id: "task-1",
    title: "Prepare SEO audit",
    due_date: "2026-07-26",
    status: "open",
    business_id: null,
    deal_id: "deal-1",
    parent_type: "deal",
    parent_name: "SEO retainer",
    created_at: "2026-07-25T09:05:00Z",
    updated_at: "2026-07-25T09:05:00Z"
  },
  {
    id: "task-2",
    title: "Call owner",
    due_date: "2026-07-27",
    status: "open",
    business_id: "business-2",
    deal_id: null,
    parent_type: "business",
    parent_name: "Kildare Accountancy",
    created_at: "2026-07-25T09:05:00Z",
    updated_at: "2026-07-25T09:05:00Z"
  },
  {
    id: "task-3",
    title: "Review notes",
    due_date: null,
    status: "completed",
    business_id: "business-1",
    deal_id: null,
    parent_type: "business",
    parent_name: "Galway Dental",
    created_at: "2026-07-24T09:05:00Z",
    updated_at: "2026-07-26T09:05:00Z"
  }
];

describe("operational insights", () => {
  it("derives transparent current-state metrics", () => {
    const result = deriveInsights(dashboard, deals, tasks, "2026-07-27");

    expect(result.metrics).toEqual(expect.arrayContaining([
      { label: "BUSINESSES", value: "8", hint: "persisted records" },
      { label: "OPEN TASKS", value: "2", hint: "current follow-up" },
      { label: "COMPLETED TASKS", value: "1", hint: "explicitly completed" },
      { label: "DEALS", value: "2", hint: "persisted opportunities" },
      { label: "ENTERED VALUE", value: "7200,00 €", hint: "not forecast revenue" }
    ]));
    expect(result.stageCounts).toEqual({ lead: 0, discovery: 0, proposal: 1, won: 1, lost: 0 });
    expect(result.taskParentCounts).toEqual({ business: 1, deal: 1 });
  });

  it("treats only dates before the local date as overdue", () => {
    const result = deriveInsights(dashboard, deals, tasks, "2026-07-27");

    expect(result.overdueTasks.map((task) => task.id)).toEqual(["task-1"]);
    expect(result.actionDeals.map((deal) => deal.id)).toEqual(["deal-1"]);
  });
});
