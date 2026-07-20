import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { mapMethods } = vi.hoisted(() => ({
  mapMethods: {
    loaded: vi.fn(() => true),
    resize: vi.fn(),
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

const responses: Record<string, unknown> = {
  "/api/v1/dashboard": {
    total_businesses: 3,
    qualified_leads: 1,
    needs_review: 2,
    stale_records: 0,
    territories: 1,
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
    phrases: ["accountant"],
    created_at: "2026-07-19T00:00:00Z"
  }],
  "/api/v1/leads": [],
  "/api/v1/geography/artifacts": [{
    schema_version: "1",
    idempotency_key: "import-1",
    checksum_sha256: checksum,
    source,
    feature_count: 1
  }],
  [`/api/v1/geography/artifacts/${checksum}`]: {
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

vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input);
  if (url === "/api/v1/discovery/plan" && init?.method === "POST") {
    return {
      ok: true,
      json: async () => ({
        territory_id: "territory-1",
        territory_name: "Galway City",
        country_code: "IE",
        query_template_id: "template-1",
        query_template_name: "Accountancy",
        sector: "Professional Services",
        phrases: ["accountant"],
        max_results_per_query: 20,
        total_planned_queries: 1,
        mode: "assisted"
      })
    };
  }
  return { ok: true, json: async () => responses[url] };
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
}

describe("App", () => {
  it("renders the validated geographic workspace", async () => {
    renderApp();
    expect(await screen.findByText("Local Authorities 2026")).toBeInTheDocument();
    expect(screen.getByText("1 validated boundaries")).toBeInTheDocument();
    await waitFor(() => expect(mapMethods.addSource).toHaveBeenCalled());
    await waitFor(() => expect(mapMethods.resize).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Territories/i }));
    expect(await screen.findByText("Galway City")).toBeInTheDocument();
  });

  it("previews an assisted discovery plan", async () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: /^Discovery/i }));
    await screen.findByRole("option", { name: "Galway City" });
    await screen.findByRole("option", { name: "Accountancy" });
    fireEvent.change(screen.getByLabelText("Territory"), { target: { value: "territory-1" } });
    fireEvent.change(screen.getByLabelText("Query group"), { target: { value: "template-1" } });
    const previewButton = screen.getByRole("button", { name: "Preview search plan" });
    await waitFor(() => expect(previewButton).not.toBeDisabled());
    fireEvent.click(previewButton);
    await waitFor(() => expect(screen.getByText(/Accountancy in Galway City/)).toBeInTheDocument());
  });
});
