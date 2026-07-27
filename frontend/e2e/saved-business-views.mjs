import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";

const checksum = "b".repeat(64);
const source = {
  dataset_title: "Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
  publisher: "Tailte Éireann",
  licence: "CC BY 4.0",
  edition_year: 2026,
  source_url: "https://example.invalid/authorities.geojson",
  retrieved_at: "2026-07-20T10:00:00Z"
};
const leads = [
  {
    id: "business-zeta",
    name: "Zeta Web Studio",
    category: "Web design",
    locality: "Galway",
    postal_area: "H91",
    website: "https://zeta.example",
    phone: null,
    first_observed_at: "2026-07-20T10:00:00Z",
    last_observed_at: "2026-07-26T12:00:00Z",
    freshness: "fresh",
    qualification_status: "qualified"
  },
  {
    id: "business-alpha",
    name: "Alpha Accounting",
    category: "Accountancy",
    locality: "Dublin",
    postal_area: "D02",
    website: "https://alpha.example",
    phone: null,
    first_observed_at: "2026-07-18T10:00:00Z",
    last_observed_at: "2026-07-24T12:00:00Z",
    freshness: "ageing",
    qualification_status: "qualified"
  },
  {
    id: "business-bravo",
    name: "Bravo Legal",
    category: "Legal services",
    locality: "Cork",
    postal_area: null,
    website: null,
    phone: null,
    first_observed_at: "2026-07-17T10:00:00Z",
    last_observed_at: "2026-07-23T12:00:00Z",
    freshness: "stale",
    qualification_status: "needs_review"
  }
];

const responses = {
  "/api/v1/dashboard": {
    total_businesses: leads.length,
    qualified_leads: 2,
    needs_review: 1,
    stale_records: 1,
    territories: 1,
    recent_leads: leads
  },
  "/api/v1/territories": [{
    id: "territory-galway",
    name: "Galway City",
    country_code: "IE",
    administrative_area: "County Galway",
    locality: "Galway",
    created_at: "2026-07-19T00:00:00Z"
  }],
  "/api/v1/query-templates?country_code=IE": [],
  "/api/v1/leads": leads,
  "/api/v1/geography/territory-links": [],
  "/api/v1/geography/coverage": [],
  "/api/v1/geography/artifacts": [{
    schema_version: "1",
    idempotency_key: "saved-view-fixture",
    checksum_sha256: checksum,
    source,
    feature_count: 0
  }],
  [`/api/v1/geography/artifacts/${checksum}`]: {
    schema_version: "1",
    idempotency_key: "saved-view-fixture",
    checksum_sha256: checksum,
    source,
    feature_count: 0,
    boundaries: []
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
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const consoleErrors = [];

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.route("**/api/v1/**", async (route) => {
    const requestUrl = new URL(route.request().url());
    const path = requestUrl.pathname + requestUrl.search;
    const payload = responses[path];
    await route.fulfill({
      status: payload === undefined ? 404 : 200,
      contentType: "application/json",
      body: JSON.stringify(payload ?? { detail: "Not found" })
    });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Businesses$/ }).click();
  await page.getByRole("heading", { name: "Business views" }).waitFor();
  await page.getByLabel("Qualification filter").selectOption("qualified");
  await page.getByLabel("Business sort").selectOption("name_asc");
  await page.getByLabel("Business view name").fill("Qualified alphabetic");
  await page.getByRole("button", { name: "Save as new" }).click();
  await page.getByText("2 of 3 businesses").waitFor();

  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Businesses$/ }).click();
  await page.getByLabel("Saved business view").selectOption({ label: "Qualified alphabetic" });
  await page.getByText("2 of 3 businesses").waitFor();
  const names = await page.locator("tbody tr td:first-child strong").allTextContents();
  if (names.join("|") !== "Alpha Accounting|Zeta Web Studio") {
    throw new Error(`Unexpected saved-view ordering: ${names.join("|")}`);
  }

  const storedBeforeDelete = await page.evaluate(() => localStorage.getItem("leadmap.businessViews.v1"));
  if (!storedBeforeDelete || storedBeforeDelete.includes("Alpha Accounting")) {
    throw new Error("Saved-view storage is missing or contains business record data.");
  }
  await page.getByRole("button", { name: "Delete" }).click();
  const options = await page.getByLabel("Saved business view").locator("option").allTextContents();
  if (options.includes("Qualified alphabetic")) {
    throw new Error("Deleted saved view remains available.");
  }
  const storedAfterDelete = await page.evaluate(() => localStorage.getItem("leadmap.businessViews.v1"));
  if (!storedAfterDelete || JSON.parse(storedAfterDelete).views.length !== 0) {
    throw new Error("Deleted saved view remains in local storage.");
  }

  await page.screenshot({
    path: "artifacts/screenshots/saved-business-views.png",
    fullPage: true
  });
  if (consoleErrors.length > 0) {
    throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
  }
  await browser.close();
} finally {
  server.kill();
}
