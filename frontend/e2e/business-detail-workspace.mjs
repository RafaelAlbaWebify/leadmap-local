import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";

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

const lead = {
  id: "business-1",
  name: "Kildare Accountancy",
  category: "Accountant",
  locality: "Kildare County",
  postal_area: null,
  website: "https://kildare-accountancy.example",
  phone: "+353 45 000 000",
  first_observed_at: "2026-07-23T12:00:00Z",
  last_observed_at: "2026-07-25T12:00:00Z",
  freshness: "fresh",
  qualification_status: "needs_review"
};

const detail = {
  id: "business-1",
  canonical_name: "Kildare Accountancy",
  normalized_name: "kildare accountancy",
  qualification_status: "needs_review",
  freshness: "fresh",
  created_at: "2026-07-23T12:00:00Z",
  updated_at: "2026-07-25T12:00:00Z",
  locations: [{
    id: "location-1",
    locality: "Kildare County",
    administrative_area: "County Kildare",
    country_code: "IE",
    postal_area: null,
    phone: "+353 45 000 000",
    website: "https://kildare-accountancy.example",
    latitude: "53.16",
    longitude: "-6.91",
    created_at: "2026-07-23T12:00:00Z",
    updated_at: "2026-07-25T12:00:00Z"
  }],
  observations: [
    {
      id: "observation-2",
      location_id: "location-1",
      provider: "google_maps",
      provider_key: "place-1",
      displayed_name: "Kildare Accountancy",
      category: "Tax consultant",
      source_url: "https://maps.example/place-1",
      observed_at: "2026-07-25T12:00:00Z",
      query_text: "tax advisor in Kildare County, IE",
      search_run_status: "completed",
      query_sequence: 2,
      result_rank: 3,
      first_seen_scroll_step: 1,
      candidate_id: "q2-place-1",
      raw_evidence: "Kildare Accountancy · Tax consultant",
      address_text: "Kildare County"
    },
    {
      id: "observation-1",
      location_id: "location-1",
      provider: "google_maps",
      provider_key: "place-1",
      displayed_name: "Kildare Accountancy",
      category: "Accountant",
      source_url: "https://maps.example/place-1",
      observed_at: "2026-07-23T12:00:00Z",
      query_text: "accountant in Kildare County, IE",
      search_run_status: "completed",
      query_sequence: 1,
      result_rank: 2,
      first_seen_scroll_step: 0,
      candidate_id: "q1-place-1",
      raw_evidence: "Kildare Accountancy · Accountant",
      address_text: "Kildare County"
    }
  ]
};

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
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  let qualificationStatus = "needs_review";
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    let payload;
    if (url.pathname === "/api/v1/dashboard") {
      payload = {
        total_businesses: 1,
        qualified_leads: qualificationStatus === "qualified" ? 1 : 0,
        needs_review: qualificationStatus === "needs_review" ? 1 : 0,
        stale_records: 0,
        territories: 1,
        recent_leads: [{ ...lead, qualification_status: qualificationStatus }]
      };
    } else if (url.pathname === "/api/v1/leads") {
      payload = [{ ...lead, qualification_status: qualificationStatus }];
    } else if (
      url.pathname === "/api/v1/businesses/business-1/qualification"
      && request.method() === "PATCH"
    ) {
      const body = JSON.parse(request.postData() ?? "{}");
      if (body.qualification_status !== "qualified") {
        throw new Error("Qualification update did not submit the selected qualified state.");
      }
      qualificationStatus = "qualified";
      payload = {
        id: "business-1",
        qualification_status: qualificationStatus,
        updated_at: "2026-07-25T13:00:00Z"
      };
    } else if (url.pathname === "/api/v1/businesses/business-1") {
      payload = {
        ...detail,
        qualification_status: qualificationStatus,
        updated_at: qualificationStatus === "qualified"
          ? "2026-07-25T13:00:00Z"
          : detail.updated_at
      };
    } else if (url.pathname === "/api/v1/territories" || url.pathname === "/api/v1/query-templates") {
      payload = [];
    } else if (url.pathname.startsWith("/api/v1/geography/")) {
      payload = [];
    }

    if (payload === undefined) {
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Businesses$/ }).click();
  await page.getByRole("button", { name: "Open" }).click();

  const workspace = page.getByRole("region", { name: "Business detail workspace" });
  await workspace.waitFor();
  await workspace.getByRole("heading", { name: "Kildare Accountancy" }).waitFor();
  await workspace.getByText("+353 45 000 000").waitFor();
  await workspace.getByText("53.16, -6.91").waitFor();
  await workspace.getByText("2 persisted discovery observations").waitFor();
  await workspace.getByText("tax advisor in Kildare County, IE").waitFor();
  await workspace.getByText("rank 3").waitFor();
  await workspace.getByText("accountant in Kildare County, IE").waitFor();
  await workspace.getByText("rank 2").waitFor();
  await workspace.getByRole("link", { name: "Open source evidence" }).first().waitFor();

  await workspace.getByLabel("Status").selectOption("qualified");
  await workspace.getByRole("button", { name: "Save qualification" }).click();
  await workspace.getByRole("status").waitFor();
  await workspace.getByText("Qualification saved as qualified.").waitFor();
  await workspace.getByText("qualified", { exact: true }).first().waitFor();
  await workspace.getByText("2 persisted discovery observations").waitFor();
  await page.screenshot({ path: "artifacts/screenshots/business-qualified-workspace.png", fullPage: true });

  if (consoleErrors.length > 0) {
    throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
  }
  await browser.close();
} finally {
  server.kill();
}
