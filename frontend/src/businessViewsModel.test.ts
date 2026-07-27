import { describe, expect, it } from "vitest";

import {
  applyBusinessView,
  businessViewId,
  emptyBusinessViewCriteria,
  parseSavedBusinessViews,
  serializeSavedBusinessViews
} from "./businessViewsModel";
import type { Lead } from "./types";

const leads: Lead[] = [
  {
    id: "b-2",
    name: "Beta Dental",
    category: "Dentist",
    locality: "Galway",
    postal_area: null,
    website: "https://beta.example",
    phone: null,
    first_observed_at: "2026-07-01T10:00:00Z",
    last_observed_at: "2026-07-03T10:00:00Z",
    freshness: "fresh",
    qualification_status: "qualified"
  },
  {
    id: "b-1",
    name: "Alpha Legal",
    category: "Solicitor",
    locality: "Dublin",
    postal_area: "D02",
    website: null,
    phone: null,
    first_observed_at: "2026-07-01T10:00:00Z",
    last_observed_at: "2026-07-02T10:00:00Z",
    freshness: "ageing",
    qualification_status: "needs_review"
  }
];

describe("business view model", () => {
  it("filters and sorts deterministically", () => {
    expect(applyBusinessView(leads, { ...emptyBusinessViewCriteria, text: "galway" }).map((lead) => lead.id)).toEqual(["b-2"]);
    expect(applyBusinessView(leads, { ...emptyBusinessViewCriteria, sort: "name_asc" }).map((lead) => lead.id)).toEqual(["b-1", "b-2"]);
    expect(applyBusinessView(leads, { ...emptyBusinessViewCriteria, qualification: "qualified" }).map((lead) => lead.id)).toEqual(["b-2"]);
  });

  it("creates deterministic collision-safe ids", () => {
    expect(businessViewId("Needs Review")).toBe("needs-review");
    expect(businessViewId("Needs Review", ["needs-review", "needs-review-2"])).toBe("needs-review-3");
  });

  it("round trips valid saved views", () => {
    const views = [{ id: "qualified", name: "Qualified", criteria: { ...emptyBusinessViewCriteria, qualification: "qualified" as const } }];
    expect(parseSavedBusinessViews(serializeSavedBusinessViews(views))).toEqual(views);
  });

  it("fails closed for invalid or unsupported storage", () => {
    expect(parseSavedBusinessViews("not json")).toEqual([]);
    expect(parseSavedBusinessViews(JSON.stringify({ version: 2, views: [] }))).toEqual([]);
    expect(parseSavedBusinessViews(JSON.stringify({ version: 1, views: [{ id: "x", name: "X", criteria: {} }] }))).toEqual([]);
  });
});
