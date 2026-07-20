import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";

const checksum = "a".repeat(64);
const source = {
  dataset_title: "Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
  publisher: "Tailte Éireann",
  licence: "CC BY 4.0",
  edition_year: 2026,
  source_url: "https://example.invalid/ireland-local-authorities.geojson",
  retrieved_at: "2026-07-20T10:00:00Z"
};

const responses = {
  "/api/v1/dashboard": {
    total_businesses: 3,
    qualified_leads: 1,
    needs_review: 2,
    stale_records: 0,
    territories: 1,
    recent_leads: []
  },
  "/api/v1/territories": [
    {
      id: "territory-1",
      name: "Galway City",
      country_code: "IE",
      administrative_area: "County Galway",
      locality: "Galway",
      created_at: "2026-07-19T00:00:00Z"
    }
  ],
  "/api/v1/query-templates?country_code=IE": [],
  "/api/v1/leads": [],
  "/api/v1/geography/artifacts": [
    {
      schema_version: "1",
      idempotency_key: "import-1",
      checksum_sha256: checksum,
      source,
      feature_count: 2
    }
  ],
  [`/api/v1/geography/artifacts/${checksum}`]: {
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
        coordinates: [[[-9.25, 53.22], [-8.95, 53.22], [-8.95, 53.42], [-9.25, 53.42], [-9.25, 53.22]]],
        bounding_box: { west: -9.25, south: 53.22, east: -8.95, north: 53.42 }
      },
      {
        external_id: "dublin-city",
        name: "Dublin City",
        geometry_type: "Polygon",
        coordinates: [[[-6.42, 53.25], [-6.08, 53.25], [-6.08, 53.45], [-6.42, 53.45], [-6.42, 53.25]]],
        bounding_box: { west: -6.42, south: 53.25, east: -6.08, north: 53.45 }
      }
    ]
  }
};

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

const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1"], {
  stdio: "inherit",
  shell: process.platform === "win32"
});

try {
  await waitForServer("http://127.0.0.1:5173");
  await mkdir("artifacts/screenshots", { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    args: ["--use-gl=swiftshader", "--enable-webgl"]
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname + new URL(route.request().url()).search;
    const payload = responses[path];
    if (payload === undefined) {
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByText("2 validated boundaries").waitFor();
  await page.locator(".geography-map canvas").waitFor({ state: "visible" });
  await page.screenshot({ path: "artifacts/screenshots/overview-geography.png", fullPage: true });

  await page.getByRole("button", { name: /Territories/i }).click();
  await page.getByRole("heading", { name: "Geographic workspace" }).waitFor();
  await page.screenshot({ path: "artifacts/screenshots/territories-geography.png", fullPage: true });

  if (consoleErrors.length > 0) {
    throw new Error(`Browser console errors:\n${consoleErrors.join("\n")}`);
  }

  await browser.close();
} finally {
  server.kill("SIGTERM");
}
