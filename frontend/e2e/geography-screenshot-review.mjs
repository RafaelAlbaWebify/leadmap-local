import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";

const checksum = "a".repeat(64);
const artifactPath = `/api/v1/geography/artifacts/${checksum}/map`;
const canonicalArtifactPath = `/api/v1/geography/artifacts/${checksum}`;
const source = {
  dataset_title: "Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
  publisher: "Tailte Éireann",
  licence: "CC BY 4.0",
  edition_year: 2026,
  source_url: "https://example.invalid/ireland-local-authorities.geojson",
  retrieved_at: "2026-07-20T10:00:00Z"
};

const territories = [
  { id: "territory-kildare", name: "Kildare County", country_code: "IE", administrative_area: "County Kildare", locality: null, created_at: "2026-07-19T00:00:00Z" },
  { id: "territory-wicklow", name: "Wicklow County", country_code: "IE", administrative_area: "County Wicklow", locality: null, created_at: "2026-07-19T00:00:00Z" },
  { id: "territory-1", name: "Galway City", country_code: "IE", administrative_area: "County Galway", locality: "Galway", created_at: "2026-07-19T00:00:00Z" }
];

const artifact = {
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
      coordinates: [[[-10.2, 51.5], [-8.2, 51.6], [-8.1, 55.2], [-9.5, 55.4], [-10.2, 51.5]]],
      bounding_box: { west: -10.2, south: 51.5, east: -8.1, north: 55.4 }
    },
    {
      external_id: "dublin-city",
      name: "Dublin City",
      geometry_type: "Polygon",
      coordinates: [[[-8.1, 51.6], [-5.8, 51.5], [-6.1, 55.2], [-8.1, 55.2], [-8.1, 51.6]]],
      bounding_box: { west: -8.1, south: 51.5, east: -5.8, north: 55.2 }
    }
  ]
};

const responses = {
  "/api/v1/dashboard": { total_businesses: 3, qualified_leads: 1, needs_review: 2, stale_records: 0, territories: 31, recent_leads: [] },
  "/api/v1/territories": territories,
  "/api/v1/query-templates?country_code=IE": [{ id: "template-accountancy", name: "Accountancy", sector: "Professional Services", countries: ["IE"], phrases: ["accountant", "accounting firm", "tax advisor", "bookkeeper"], created_at: "2026-07-19T00:00:00Z" }],
  "/api/v1/leads": [],
  "/api/v1/geography/territory-links": [{ territory_id: "territory-1", checksum_sha256: checksum, boundary_external_id: "galway-city", boundary_name: "Galway City" }],
  "/api/v1/geography/coverage": [{ territory_id: "territory-1", territory_name: "Galway City", checksum_sha256: checksum, boundary_external_id: "galway-city", boundary_name: "Galway City", lead_count: 12, latest_observed_at: "2026-07-18T12:00:00Z", freshness: "fresh" }],
  "/api/v1/geography/artifacts": [{ schema_version: "1", idempotency_key: "import-1", checksum_sha256: checksum, source, feature_count: 2 }],
  [artifactPath]: artifact
};

const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1"], { stdio: "inherit", shell: process.platform === "win32" });

async function waitForServer(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try { const response = await fetch(url); if (response.ok) return; } catch { /* Vite starting. */ }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

try {
  await waitForServer("http://127.0.0.1:5173");
  await mkdir("artifacts/screenshots", { recursive: true });
  const browser = await chromium.launch({ headless: true, args: process.platform === "win32" ? ["--enable-webgl"] : ["--use-gl=swiftshader", "--enable-webgl"] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  let mapRequests = 0;
  let canonicalRequests = 0;
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api/v1/**", async (route) => {
    const requestUrl = new URL(route.request().url());
    const key = `${requestUrl.pathname}${requestUrl.search}`;
    if (requestUrl.pathname === artifactPath) mapRequests += 1;
    if (requestUrl.pathname === canonicalArtifactPath) canonicalRequests += 1;
    const payload = responses[key];
    await route.fulfill({ status: payload === undefined ? 404 : 200, contentType: "application/json", body: JSON.stringify(payload ?? { detail: "Not found" }) });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Territories$/ }).click();
  await page.getByText("Galway City", { exact: true }).first().waitFor();
  await page.screenshot({ path: "artifacts/screenshots/territories-geography.png", fullPage: true });

  const mapCanvas = page.locator(".geography-map canvas");
  await mapCanvas.waitFor();
  await mapCanvas.click({ position: { x: 100, y: 180 } });
  await page.getByText("12 persisted leads", { exact: true }).waitFor();
  await page.screenshot({ path: "artifacts/screenshots/territories-selected-boundary.png", fullPage: true });

  if (mapRequests !== 1) throw new Error(`Expected one lightweight map request, received ${mapRequests}.`);
  if (canonicalRequests !== 0) throw new Error(`Canonical artifact was requested ${canonicalRequests} times during map rendering.`);
  if (consoleErrors.length > 0) throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
  await browser.close();
} finally {
  server.kill();
}
