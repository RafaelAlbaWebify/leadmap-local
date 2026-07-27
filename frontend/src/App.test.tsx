import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { mapMethods } = vi.hoisted(() => ({
  mapMethods: {
    loaded: vi.fn(() => true),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    getSource: vi.fn(() => undefined),
    on: vi.fn(),
    once: vi.fn(),
    fitBounds: vi.fn(),
    getCanvas: vi.fn(() => ({ style: { cursor: "" } })),
    remove: vi.fn()
  }
}));

vi.mock("maplibre-gl", () => ({
  default: { Map: vi.fn(() => mapMethods) }
}));

import { App } from "./App";

const checksum = "a".repeat(64);
const source = {
  dataset_title: "Local Authorities 2026",
  publisher: "Tailte Éireann",
  licence: "CC BY 4.0",
  edition_year: 2026,
  source_url: "https://example.invalid/boundaries.geojson",
  retrieved_at: "2026-07-20T10:00:00Z"
};

let territoryLinks: unknown[] = [];
let assistedState = "idle";
let candidateIncluded = true;
let boundedReview = false;
let currentQuerySequence = 1;
const responses: Record<string, unknown> = {
  "/api/v1/dashboard": {
    total_businesses: 3,
    qualified_leads: 1,
    needs_review: 2,
    stale_records: 0,
    territories: 31,
    recent_leads: []
  },
  "/api/v1/territories": [{
    id: "territory-1",
    name: "Galway City",
    country_code: "IE",
    administrative_area: "County Galway",
    locality: "Galway",
    created_at: "2026-07-19T00:00:00Z"
  }],
  "/api/v1/query-templates?country_code=IE": [{
    id: "template-1",
    name: "Accountancy",
    sector: "Professional Services",
    countries: ["IE"],
    phrases: ["accountant", "tax advisor"],
    created_at: "2026-07-19T00:00:00Z"
  }],
  "/api/v1/leads": [],
  "/api/v1/geography/coverage": [{
    territory_id: "territory-1",
    territory_name: "Galway City",
    checksum_sha256: checksum,
    boundary_external_id: "galway-city",
    boundary_name: "Galway City",
    lead_count: 12,
    latest_observed_at: "2026-07-18T12:00:00Z",
    freshness: "fresh"
  }],
  "/api/v1/geography/artifacts": [{
    schema_version: "1",
    idempotency_key: "import-1",
    checksum_sha256: checksum,
    source,
    feature_count: 1
  }],
  [`/api/v1/geography/artifacts/${checksum}/map`]: {
    schema_version: "1",
    idempotency_key: "import-1",
    checksum_sha256: checksum,
    source,
    feature_count: 1,
    boundaries: [{
      external_id: "galway-city",
      name: "Galway City",
      geometry_type: "Polygon",
      coordinates: [[[-9.2, 53.2], [-8.9, 53.2], [-8.9, 53.4], [-9.2, 53.2]]],
      bounding_box: { west: -9.2, south: 53.2, east: -8.9, north: 53.4 }
    }]
  }
};

function assistedSession() {
  return {
    session_id: assistedState === "idle" ? null : "session-1",
    state: assistedState,
    territory_id: assistedState === "idle" ? null : "territory-1",
    query_template_id: assistedState === "idle" ? null : "template-1",
    start_url: assistedState === "idle" ? null : "https://www.google.com/maps/search/accountant",
    error: null
  };
}

function assistedReview() {
  const queryText = currentQuerySequence === 1
    ? "accountant in Galway City, IE"
    : "tax advisor in Galway City, IE";
  const traversal = boundedReview ? {
    traversal_progress: {
      query_text: queryText,
      query_sequence: currentQuerySequence,
      scroll_step: 3,
      unique_cards: 1,
      stagnant_scrolls: 3,
      elapsed_seconds: 2.5,
      stop_reason: "no_new_results"
    },
    traversal_stop_reason: "no_new_results"
  } : {};
  return {
    ...assistedSession(),
    ...traversal,
    candidates: [{
      candidate_id: "candidate-1",
      provider_key: "place-1",
      displayed_name: "West Coast Accountancy",
      normalized_name: "west coast accountancy",
      category: "Accountant",
      address_text: "Galway",
      phone: "+353 91 000 001",
      website: "https://example.com",
      source_url: "https://maps.example/place-1",
      latitude: null,
      longitude: null,
      raw_evidence: "West Coast Accountancy · Accountant · Galway",
      included: candidateIncluded,
      query_text: boundedReview ? queryText : null,
      query_sequence: boundedReview ? currentQuerySequence : null,
      result_rank: boundedReview ? 1 : null,
      first_seen_scroll_step: boundedReview ? 0 : null,
      captured_at: boundedReview ? "2026-07-24T18:00:00Z" : null
    }],
    included_count: candidateIncluded ? 1 : 0,
    excluded_count: candidateIncluded ? 0 : 1
  };
}

vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input);
  if (url === "/api/v1/geography/territory-links") {
    return { ok: true, json: async () => territoryLinks };
  }
  if (url === "/api/v1/geography/territory-links/territory-1" && init?.method === "PUT") {
    territoryLinks = [{
      territory_id: "territory-1",
      checksum_sha256: checksum,
      boundary_external_id: "galway-city",
      boundary_name: "Galway City"
    }];
    return { ok: true, json: async () => territoryLinks[0] };
  }
  if (url === "/api/v1/discovery/prepared-plan" && init?.method === "POST") {
    return {
      ok: true,
      json: async () => ({
        territory_id: "territory-1",
        territory_name: "Galway City",
        country_code: "IE",
        query_template_id: "template-1",
        query_template_name: "Accountancy",
        sector: "Professional Services",
        max_results_per_query: 20,
        total_planned_queries: 2,
        prepared_queries: [
          { sequence: 1, phrase: "accountant", query_text: "accountant in Galway City, IE" },
          { sequence: 2, phrase: "tax advisor", query_text: "tax advisor in Galway City, IE" }
        ],
        mode: "assisted"
      })
    };
  }
  if (url === "/api/v1/discovery/prepared-session" && init?.method === "POST") {
    const payload = JSON.parse(String(init.body)) as { query_sequence: number };
    currentQuerySequence = payload.query_sequence;
    assistedState = "awaiting_operator";
    return { ok: true, json: async () => assistedSession() };
  }
  if (url === "/api/v1/discovery/session/session-1/ready" && init?.method === "POST") {
    assistedState = "ready";
    return { ok: true, json: async () => assistedSession() };
  }
  if (url.startsWith("/api/v1/discovery/session/session-1/collect-bounded?") && init?.method === "POST") {
    boundedReview = true;
    assistedState = "review";
    return { ok: true, json: async () => assistedReview() };
  }
  if (url === "/api/v1/discovery/session/session-1/capture-visible" && init?.method === "POST") {
    boundedReview = false;
    assistedState = "review";
    return { ok: true, json: async () => assistedReview() };
  }
  if (url === "/api/v1/discovery/session/session-1/candidates/candidate-1" && init?.method === "PATCH") {
    candidateIncluded = false;
    return { ok: true, json: async () => assistedReview() };
  }
  if (url === "/api/v1/discovery/session/session-1" && init?.method === "DELETE") {
    assistedState = "stopped";
    return { ok: true, json: async () => assistedSession() };
  }
  return { ok: true, json: async () => responses[url] };
}));

afterEach(() => {
  cleanup();
  territoryLinks = [];
  assistedState = "idle";
  candidateIncluded = true;
  boundedReview = false;
  currentQuerySequence = 1;
  vi.clearAllMocks();
});

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
}

async function previewPlan() {
  fireEvent.click(screen.getByRole("button", { name: /^Discover$/ }));
  await screen.findByRole("option", { name: "Galway City" });
  await screen.findByRole("option", { name: "Accountancy" });
  fireEvent.change(screen.getByLabelText("Territory"), { target: { value: "territory-1" } });
  fireEvent.change(screen.getByLabelText("Query group"), { target: { value: "template-1" } });
  const previewButton = screen.getByRole("button", { name: "Preview search plan" });
  fireEvent.click(previewButton);
  await screen.findByText("2 prepared queries · bounded result-panel traversal");
}

describe("App", () => {
  it("renders guided markets and geography data", async () => {
    renderApp();
    expect(await screen.findByRole("heading", { name: "Markets" })).toBeInTheDocument();
    expect(await screen.findByText("Galway City", { exact: true })).toBeInTheDocument();
  });

  it("previews and controls an assisted discovery session", async () => {
    renderApp();
    await previewPlan();
    fireEvent.click(screen.getByRole("button", { name: "Launch query 1" }));
    await screen.findByText(/awaiting operator/);
    fireEvent.click(screen.getByRole("button", { name: "Browser is ready" }));
    await screen.findByText(/Session status: ready/);
    fireEvent.click(screen.getByRole("button", { name: "Collect bounded results" }));
    await screen.findByText("1 unique cards collected");
    fireEvent.click(screen.getByRole("button", { name: "Stop assisted session" }));
    await screen.findByRole("button", { name: "Prepare query 2" });
  });

  it("updates candidate review decisions", async () => {
    renderApp();
    await previewPlan();
    fireEvent.click(screen.getByRole("button", { name: "Launch query 1" }));
    await screen.findByText(/awaiting operator/);
    fireEvent.click(screen.getByRole("button", { name: "Browser is ready" }));
    await screen.findByText(/Session status: ready/);
    fireEvent.click(screen.getByRole("button", { name: "Capture currently visible only" }));
    await screen.findByText("West Coast Accountancy");
    fireEvent.click(screen.getByRole("button", { name: "Exclude" }));
    await waitFor(() => expect(screen.getByText("0 included · 1 excluded")).toBeInTheDocument());
  });
});
