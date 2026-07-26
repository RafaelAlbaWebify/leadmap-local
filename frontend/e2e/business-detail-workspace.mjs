import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";

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
  const browser = await chromium.launch({
    headless: true,
    args: process.platform === "win32"
      ? ["--enable-webgl"]
      : ["--use-gl=swiftshader", "--enable-webgl"]
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
    deviceScaleFactor: 1
  });
  const consoleErrors = [];
  let qualificationStatus = "needs_review";
  const notes = [{
    id: "note-1",
    business_id: "business-1",
    content: "Reviewed public evidence before qualification.",
    created_at: "2026-07-25T12:30:00Z"
  }];
  const deals = [];
  const tasks = [];

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
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
    } else if (url.pathname === "/api/v1/businesses/business-1" && method === "GET") {
      payload = {
        ...detail,
        qualification_status: qualificationStatus,
        updated_at: qualificationStatus === "qualified"
          ? "2026-07-25T13:00:00Z"
          : detail.updated_at
      };
    } else if (
      url.pathname === "/api/v1/businesses/business-1/qualification"
      && method === "PATCH"
    ) {
      const body = JSON.parse(request.postData() ?? "{}");
      if (body.qualification_status !== "qualified") {
        throw new Error("Qualification did not submit the selected state.");
      }
      qualificationStatus = "qualified";
      payload = {
        id: "business-1",
        qualification_status: qualificationStatus,
        updated_at: "2026-07-25T13:00:00Z"
      };
    } else if (
      url.pathname === "/api/v1/businesses/business-1/notes"
      && method === "GET"
    ) {
      payload = notes;
    } else if (
      url.pathname === "/api/v1/businesses/business-1/notes"
      && method === "POST"
    ) {
      const body = JSON.parse(request.postData() ?? "{}");
      if (body.content !== "Call next Tuesday after qualification review.") {
        throw new Error("Business note did not preserve operator-entered text.");
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
      url.pathname === "/api/v1/businesses/business-1/deals"
      && method === "POST"
    ) {
      const body = JSON.parse(request.postData() ?? "{}");
      const expected = {
        title: "Website redesign",
        stage: "proposal",
        value_eur_cents: 350000,
        next_action: "Send proposal"
      };
      if (JSON.stringify(body) !== JSON.stringify(expected)) {
        throw new Error("Deal create did not preserve operator-entered values.");
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
    } else if (url.pathname === "/api/v1/deals" && method === "GET") {
      payload = deals;
    } else if (url.pathname === "/api/v1/deals/deal-1" && method === "PATCH") {
      const body = JSON.parse(request.postData() ?? "{}");
      const expected = { stage: "won", next_action: "Schedule kickoff" };
      if (JSON.stringify(body) !== JSON.stringify(expected)) {
        throw new Error("Deal update did not preserve explicit changes.");
      }
      deals[0] = {
        ...deals[0],
        ...expected,
        updated_at: "2026-07-25T13:20:00Z"
      };
      payload = deals[0];
    } else if (url.pathname === "/api/v1/tasks" && method === "GET") {
      payload = tasks;
    } else if (url.pathname === "/api/v1/tasks" && method === "POST") {
      const body = JSON.parse(request.postData() ?? "{}");
      const parentType = body.business_id ? "business" : "deal";
      const expectedTitle = parentType === "business"
        ? "Call decision maker"
        : "Review signed proposal";
      if (body.title !== expectedTitle || body.due_date !== "2026-07-30") {
        throw new Error("Task create did not preserve operator-entered values.");
      }
      if (parentType === "business" && body.business_id !== "business-1") {
        throw new Error("Business task did not reference its business.");
      }
      if (parentType === "deal" && body.deal_id !== "deal-1") {
        throw new Error("Deal task did not reference its deal.");
      }
      const created = {
        id: `task-${tasks.length + 1}`,
        title: body.title,
        due_date: body.due_date,
        status: "open",
        business_id: body.business_id ?? null,
        deal_id: body.deal_id ?? null,
        parent_type: parentType,
        parent_name: parentType === "business"
          ? "Kildare Accountancy"
          : "Website redesign",
        created_at: `2026-07-25T13:${25 + tasks.length}:00Z`,
        updated_at: `2026-07-25T13:${25 + tasks.length}:00Z`
      };
      tasks.unshift(created);
      payload = created;
      responseStatus = 201;
    } else if (/^\/api\/v1\/tasks\/task-\d+\/complete$/.test(url.pathname) && method === "PATCH") {
      const taskId = url.pathname.split("/")[4];
      const index = tasks.findIndex((task) => task.id === taskId);
      if (index === -1) {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Task not found." })
        });
        return;
      }
      tasks[index] = {
        ...tasks[index],
        status: "completed",
        updated_at: "2026-07-25T13:30:00Z"
      };
      payload = tasks[index];
    } else if (
      url.pathname === "/api/v1/territories"
      || url.pathname === "/api/v1/query-templates"
      || url.pathname.startsWith("/api/v1/geography/")
    ) {
      payload = [];
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
      status: responseStatus,
      contentType: "application/json",
      body: JSON.stringify(payload)
    });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Businesses$/ }).click();
  await page.getByRole("button", { name: "Open" }).click();

  const workspace = page.getByRole("region", { name: "Business detail workspace" });
  await workspace.getByRole("heading", { name: "Kildare Accountancy" }).waitFor();
  await workspace.getByText("Reviewed public evidence before qualification.").waitFor();
  await workspace.getByText("2 persisted discovery observations").waitFor();

  const businessTask = workspace.getByRole("region", {
    name: "Create task for Kildare Accountancy"
  });
  await businessTask.getByLabel("Task title").fill("Call decision maker");
  await businessTask.getByLabel("Due date").fill("2026-07-30");
  await businessTask.getByRole("button", { name: "Create task" }).click();
  await businessTask.getByText("Task created.").waitFor();

  await workspace.getByLabel("Status").selectOption("qualified");
  await workspace.getByRole("button", { name: "Save qualification" }).click();
  await workspace.getByText("Qualification saved as qualified.").waitFor();

  const dealCreate = workspace.getByRole("region", { name: "Create deal" });
  await dealCreate.getByLabel("Title", { exact: true }).fill("Website redesign");
  await dealCreate.getByLabel("Stage", { exact: true }).selectOption("proposal");
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
  const proposal = page.getByRole("region", { name: "Proposal deals" });
  await proposal.getByText("Website redesign").waitFor();
  await proposal.getByText("3500,00 €").waitFor();

  const dealTask = proposal.getByRole("region", {
    name: "Create task for Website redesign"
  });
  await dealTask.getByLabel("Task title").fill("Review signed proposal");
  await dealTask.getByLabel("Due date").fill("2026-07-30");
  await dealTask.getByRole("button", { name: "Create task" }).click();
  await dealTask.getByText("Task created.").waitFor();

  await proposal.getByRole("button", { name: "Edit deal" }).click();
  const editor = proposal.getByLabel("Edit Website redesign");
  await editor.getByLabel("Stage").selectOption("won");
  await editor.getByLabel("Next action").fill("Schedule kickoff");
  await editor.getByRole("button", { name: "Save deal" }).click();

  const won = page.getByRole("region", { name: "Won deals" });
  await won.getByText("Website redesign").waitFor();
  await won.getByText("Schedule kickoff").waitFor();

  await page.getByRole("button", { name: /^Tasks$/ }).click();
  const tasksWorkspace = page.getByRole("region", { name: "Tasks workspace" });
  const openTasks = tasksWorkspace.getByRole("region", { name: "Open tasks" });
  await openTasks.getByText("Call decision maker").waitFor();
  await openTasks.getByText("Review signed proposal").waitFor();

  const businessTaskCard = openTasks.locator(".task-card", {
    hasText: "Call decision maker"
  });
  await businessTaskCard.getByRole("button", { name: "Mark completed" }).click();
  const completedTasks = tasksWorkspace.getByRole("region", { name: "Completed tasks" });
  await completedTasks.getByText("Call decision maker").waitFor();
  await page.screenshot({
    path: "artifacts/screenshots/persisted-follow-up-tasks.png",
    fullPage: true
  });

  if (consoleErrors.length > 0) {
    throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
  }
  await browser.close();
} finally {
  server.kill();
}
