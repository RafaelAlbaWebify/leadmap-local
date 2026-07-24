import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";

const checksum = "a".repeat(64);
const artifactPath = `/api/v1/geography/artifacts/${checksum}`;
const source = {
  dataset_title: "Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
  publisher: "Tailte Éireann",
  licence: "CC BY 4.0",
  edition_year: 2026,
  source_url: "https://example.invalid/ireland-local-authorities.geojson",
  retrieved_at: "2026-07-20T10:00:00Z"
};

const territories = [
  {
    id: "territory-kildare",
    name: "Kildare County",
    country_code: "IE",
    administrative_area: "County Kildare",
    locality: null,
    created_at: "2026-07-19T00:00:00Z"
  },
  {
    id: "territory-wicklow",
    name: "Wicklow County",
    country_code: "IE",
    administrative_area: "County Wicklow",
    locality: null,
    created_at: "2026-07-19T00:00:00Z"
  },
  {
    id: "territory-1",
    name: "Galway City",
    country_code: "IE",
    administrative_area: "County Galway",
    locality: "Galway",
    created_at: "2026-07-19T00:00:00Z"
  }
];

const responses = {
  "/api/v1/dashboard": {
    total_businesses: 3,
    qualified_leads: 1,
    needs_review: 2,
    stale_records: 0,
    territories: 31,
    recent_leads: []
  },
  "/api/v1/territories": territories,
  "/api/v1/query-templates?country_code=IE": [
    {
      id: "template-accountancy",
      name: "Accountancy",
      sector: "Professional Services",
      countries: ["IE"],
      phrases: ["accountant", "accounting firm", "tax advisor", "bookkeeper"],
      created_at: "2026-07-19T00:00:00Z"
    }
  ],
  "/api/v1/leads": [],
  "/api/v1/geography/territory-links": [
    {
      territory_id: "territory-1",
      checksum_sha256: checksum,
      boundary_external_id: "galway-city",
      boundary_name: "Galway City"
    }
  ],
  "/api/v1/geography/coverage": [
    {
      territory_id: "territory-1",
      territory_name: "Galway City",
      checksum_sha256: checksum,
      boundary_external_id: "galway-city",
      boundary_name: "Galway City",
      lead_count: 12,
      latest_observed_at: "2026-07-18T12:00:00Z",
      freshness: "fresh"
    }
  ],
  "/api/v1/geography/artifacts": [
    {
      schema_version: "1",
      idempotency_key: "import-1",
      checksum_sha256: checksum,
      source,
      feature_count: 2
    }
  ],
  [artifactPath]: {
    schema_version: "1",
    idempotency_key: "import-1",
    checksum_sha256: checksum,
    source,
    feature_count: 2,
    boundaries: [
      {
        external_id: "galway-city",
        name: "Galway City",
        geometry_type: "Polygon",
        coordinates: [[
          [-10.2, 51.5],
          [-8.2, 51.6],
          [-8.1, 55.2],
          [-9.5, 55.4],
          [-10.2, 51.5]
        ]],
        bounding_box: { west: -10.2, south: 51.5, east: -8.1, north: 55.4 }
      },
      {
        external_id: "dublin-city",
        name: "Dublin City",
        geometry_type: "Polygon",
        coordinates: [[
          [-8.1, 51.6],
          [-5.8, 51.5],
          [-6.1, 55.2],
          [-8.1, 55.2],
          [-8.1, 51.6]
        ]],
        bounding_box: { west: -8.1, south: 51.5, east: -5.8, north: 55.2 }
      }
    ]
  }
};

function session(state) {
  return {
    session_id: "session-1",
    state,
    territory_id: "territory-kildare",
    query_template_id: "template-accountancy",
    start_url: "https://www.google.com/maps/search/accountant+Kildare+County",
    error: null
  };
}

function boundedReview() {
  return {
    ...session("review"),
    traversal_progress: {
      query_text: "accountant Kildare County",
      query_sequence: 1,
      scroll_step: 4,
      unique_cards: 2,
      stagnant_scrolls: 3,
      elapsed_seconds: 4.2,
      stop_reason: "no_new_results"
    },
    traversal_stop_reason: "no_new_results",
    candidates: [
      {
        candidate_id: "candidate-1",
        provider_key: "place-1",
        displayed_name: "Kildare Accountancy",
        normalized_name: "kildare accountancy",
        category: "Accountant",
        address_text: "Kildare County",
        phone: null,
        website: "https://example.com",
        source_url: "https://www.google.com/maps/place/Kildare+Accountancy",
        latitude: "53.15",
        longitude: "-6.91",
        raw_evidence: "Kildare Accountancy · Accountant",
        included: true,
        query_text: "accountant Kildare County",
        query_sequence: 1,
        result_rank: 1,
        first_seen_scroll_step: 0,
        captured_at: "2026-07-24T18:00:00Z"
      },
      {
        candidate_id: "candidate-2",
        provider_key: "place-2",
        displayed_name: "County Books",
        normalized_name: "county books",
        category: "Bookkeeping service",
        address_text: "Kildare County",
        phone: null,
        website: null,
        source_url: "https://www.google.com/maps/place/County+Books",
        latitude: "53.17",
        longitude: "-6.89",
        raw_evidence: "County Books · Bookkeeping service",
        included: true,
        query_text: "accountant Kildare County",
        query_sequence: 1,
        result_rank: 2,
        first_seen_scroll_step: 1,
        captured_at: "2026-07-24T18:00:01Z"
      }
    ],
    included_count: 2,
    excluded_count: 0
  };
}

async function waitForServer(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Vite is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function waitForStableMap(page) {
  await page.locator(".geography-map canvas").waitFor({ state: "visible" });
  await page.waitForTimeout(1000);
}

const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1"], {
  stdio: "inherit",
  shell: process.platform === "win32"
});

try {
  await waitForServer("http://127.0.0.1:5173");
  await mkdir("artifacts/screenshots", { recursive: true });

  const chromiumArgs = process.platform === "win32"
    ? ["--enable-webgl"]
    : ["--use-gl=swiftshader", "--enable-webgl"];
  const browser = await chromium.launch({ headless: true, args: chromiumArgs });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  let artifactRequests = 0;
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api/v1/**", async (route) => {
    const requestUrl = new URL(route.request().url());
    const path = requestUrl.pathname + requestUrl.search;
    const method = route.request().method();
    if (path === artifactPath) artifactRequests += 1;

    let payload = responses[path];
    if (path === "/api/v1/discovery/plan" && method === "POST") {
      payload = {
        territory_id: "territory-kildare",
        territory_name: "Kildare County",
        country_code: "IE",
        query_template_id: "template-accountancy",
        query_template_name: "Accountancy",
        sector: "Professional Services",
        phrases: ["accountant", "accounting firm", "tax advisor", "bookkeeper"],
        max_results_per_query: 20,
        total_planned_queries: 4,
        mode: "assisted"
      };
    } else if (path === "/api/v1/discovery/session" && method === "POST") {
      payload = session("awaiting_operator");
    } else if (path === "/api/v1/discovery/session/session-1/ready" && method === "POST") {
      payload = session("ready");
    } else if (path.startsWith("/api/v1/discovery/session/session-1/collect-bounded?") && method === "POST") {
      payload = boundedReview();
    }

    if (payload === undefined) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Not found" })
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload)
    });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Markets", exact: true }).waitFor();
  await page.getByRole("heading", { name: "Find the best markets before collecting businesses." }).waitFor();
  await page.getByText("2 validated boundaries").waitFor();
  await page.getByLabel("Coverage freshness legend").waitFor();
  await waitForStableMap(page);
  await page.screenshot({ path: "artifacts/screenshots/markets-guided-shell.png", fullPage: true });

  await page.getByLabel("Sector").selectOption("template-accountancy");
  await page.getByRole("button", { name: "Recommend markets" }).click();
  await page.getByRole("heading", { name: "Recommended markets" }).waitFor();
  await page.getByRole("heading", { name: "Kildare County" }).waitFor();
  await page.screenshot({ path: "artifacts/screenshots/markets-recommendations.png", fullPage: true });

  const kildareCard = page.locator(".recommendation-card").filter({ hasText: "Kildare County" });
  await kildareCard.getByRole("button", { name: "Research this market" }).click();
  await page.getByRole("heading", { name: "Discover", exact: true }).waitFor();
  await page.getByLabel("Territory").waitFor();
  if (await page.getByLabel("Territory").inputValue() !== "territory-kildare") {
    throw new Error("Markets-to-Discover handoff did not retain Kildare County.");
  }
  if (await page.getByLabel("Query group").inputValue() !== "template-accountancy") {
    throw new Error("Markets-to-Discover handoff did not retain Accountancy.");
  }
  await page.screenshot({ path: "artifacts/screenshots/discover-prefilled-market.png", fullPage: true });

  await page.getByRole("button", { name: "Preview search plan" }).click();
  await page.getByLabel("Current approved query").waitFor();
  if (await page.getByLabel("Current approved query").inputValue() !== "accountant Kildare County") {
    throw new Error("Discovery plan did not prepare the approved query text.");
  }
  await page.getByRole("button", { name: "Launch visible browser" }).click();
  await page.getByText("awaiting operator").waitFor();
  await page.getByRole("button", { name: "Browser is ready" }).click();
  await page.getByRole("button", { name: "Collect bounded results" }).click();
  await page.getByLabel("Traversal summary").waitFor();
  await page.getByText("2 unique cards collected").waitFor();
  await page.getByText(/stopped: no new results/).waitFor();
  await page.getByText("Kildare Accountancy").waitFor();
  await page.getByText("County Books").waitFor();
  await page.screenshot({ path: "artifacts/screenshots/discover-bounded-results.png", fullPage: true });

  await page.getByRole("button", { name: /^Territories$/ }).click();
  await page.getByRole("heading", { name: "Geographic workspace" }).waitFor();
  await waitForStableMap(page);
  await page.screenshot({ path: "artifacts/screenshots/territories-geography.png", fullPage: true });

  const mapBox = await page.locator(".geography-map").boundingBox();
  if (!mapBox) throw new Error("Geographic map did not produce a visible bounding box.");
  await page.mouse.click(mapBox.x + mapBox.width * 0.45, mapBox.y + mapBox.height * 0.5);
  await page.locator(".geography-detail").getByRole("heading", { name: "Galway City" }).waitFor();
  await page.getByText("12 leads").waitFor();
  await page.getByRole("button", { name: "Assign boundary" }).waitFor();
  await page.waitForTimeout(250);
  await page.screenshot({
    path: "artifacts/screenshots/territories-selected-boundary.png",
    fullPage: true
  });

  if (artifactRequests !== 1) {
    throw new Error(`Expected one full geography artifact request; received ${artifactRequests}.`);
  }
  if (consoleErrors.length > 0) {
    throw new Error(`Browser console errors:\n${consoleErrors.join("\n")}`);
  }

  await browser.close();
} finally {
  server.kill("SIGTERM");
}
