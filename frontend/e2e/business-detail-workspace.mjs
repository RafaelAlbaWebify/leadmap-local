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
  const notes = [{
    id: "note-1",
    business_id: "business-1",
    content: "Reviewed public evidence before qualification.",
    created_at: "2026-07-25T12:30:00Z"
  }];
  const deals = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    let payload;
    let responseStatus = 200;
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
    } else if (
      url.pathname === "/api/v1/businesses/business-1/notes"
      && request.method() === "POST"
    ) {
      const body = JSON.parse(request.postData() ?? "{}");
      if (body.content !== "Call next Tuesday after qualification review.") {
        throw new Error("Business note did not submit the exact operator-entered text.");
      }
      const created = {
        id: "note-2",
        business_id: "business-1",
        content: body.content,
        created_at: "2026-07-25T13:05:00Z"
      };
      notes.unshift(created);
      payload = created;
      responseStatus = 201;
    } else if (
      url.pathname === "/api/v1/businesses/business-1/notes"
      && request.method() === "GET"
    ) {
      payload = notes;
    } else if (
      url.pathname === "/api/v1/businesses/business-1/deals"
      && request.method() === "POST"
    ) {
      const body = JSON.parse(request.postData() ?? "{}");
      const expected = {
        title: "Website redesign",
        stage: "proposal",
        value_eur_cents: 350000,
        next_action: "Send proposal"
      };
      if (JSON.stringify(body) !== JSON.stringify(expected)) {
        throw new Error("Deal create did not submit the exact operator-entered opportunity.");
      }
      const created = {
        id: "deal-1",
        business_id: "business-1",
        business_name: "Kildare Accountancy",
        ...expected,
        created_at: "2026-07-25T13:10:00Z",
        updated_at: "2026-07-25T13:10:00Z"
      };
      deals.unshift(created);
      payload = created;
      responseStatus = 201;
    } else if (
      url.pathname === "/api/v1/deals/deal-1"
      && request.method() === "PATCH"
    ) {
      const body = JSON.parse(request.postData() ?? "{}");
      const expected = { stage: "won", next_action: "Schedule kickoff" };
      if (JSON.stringify(body) !== JSON.stringify(expected)) {
        throw new Error("Deal update did not submit the exact operator-confirmed changes.");
      }
      deals[0] = {
        ...deals[0],
        ...expected,
        updated_at: "2026-07-25T13:20:00Z"
      };
      payload = deals[0];
    } else if (url.pathname === "/api/v1/deals" && request.method() === "GET") {
      payload = deals;
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
    await route.fulfill({ status: responseStatus, contentType: "application/json", body: JSON.stringify(payload) });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Businesses$/ }).click();
  await page.getByRole("button", { name: "Open" }).click();

  const workspace = page.getByRole("region", { name: "Business detail workspace" });
  await workspace.waitFor();
  await workspace.getByRole("heading", { name: "Kildare Accountancy", exact: true }).waitFor();
  await workspace.getByText("+353 45 000 000").waitFor();
  await workspace.getByText("53.16, -6.91").waitFor();
  await workspace.getByText("Reviewed public evidence before qualification.").waitFor();
  await workspace.getByText("2 persisted discovery observations").waitFor();

  await workspace.getByLabel("Status").selectOption("qualified");
  await workspace.getByRole("button", { name: "Save qualification" }).click();
  await workspace.getByText("Qualification saved as qualified.").waitFor();

  const dealCreate = workspace.getByRole("region", { name: "Create deal" });
  await dealCreate.getByLabel("Title", { exact: true }).fill("Website redesign");
  await dealCreate.getByRole("combobox").selectOption("proposal");
  await dealCreate.getByLabel("Value (€)").fill("3500");
  await dealCreate.getByLabel("Next action", { exact: true }).fill("Send proposal");
  await dealCreate.getByRole("button", { name: "Create deal" }).click();
  await dealCreate.getByText("Deal created.").waitFor();

  await workspace.getByLabel("Add a note").fill("Call next Tuesday after qualification review.");
  await workspace.getByRole("button", { name: "Add note" }).click();
  await workspace.getByText("Note added.").waitFor();
  await workspace.getByText("Call next Tuesday after qualification review.").waitFor();
  await workspace.getByText("2 persisted discovery observations").waitFor();

  await page.getByRole("button", { name: /^Deals$/ }).click();
  const pipeline = page.getByRole("region", { name: "Deals pipeline" });
  await pipeline.waitFor();
  const proposal = page.getByRole("region", { name: "Proposal deals" });
  await proposal.getByText("Website redesign").waitFor();
  await proposal.getByText("Kildare Accountancy").waitFor();
  await proposal.getByText("3500,00 €").waitFor();
  await proposal.getByText("Send proposal").waitFor();

  await proposal.getByRole("button", { name: "Edit deal" }).click();
  const editor = proposal.getByLabel("Edit Website redesign");
  await editor.getByLabel("Stage").selectOption("won");
  await editor.getByLabel("Next action").fill("Schedule kickoff");
  await editor.getByRole("button", { name: "Save deal" }).click();

  const won = page.getByRole("region", { name: "Won deals" });
  await won.getByText("Website redesign").waitFor();
  await won.getByText("Kildare Accountancy").waitFor();
  await won.getByText("3500,00 €").waitFor();
  await won.getByText("Schedule kickoff").waitFor();
  await proposal.getByText("Website redesign").waitFor({ state: "detached" });
  await page.screenshot({ path: "artifacts/screenshots/deal-stage-update-workspace.png", fullPage: true });

  if (consoleErrors.length > 0) {
    throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
  }
  await browser.close();
} finally {
  server.kill();
}
