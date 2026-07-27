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
  qualification_status: "qualified"
};

const detail = {
  id: "business-1",
  canonical_name: "Kildare Accountancy",
  normalized_name: "kildare accountancy",
  qualification_status: "qualified",
  freshness: "fresh",
  created_at: "2026-07-23T12:00:00Z",
  updated_at: "2026-07-25T12:00:00Z",
  locations: [],
  observations: []
};

const deal = {
  id: "deal-1",
  business_id: "business-1",
  business_name: "Kildare Accountancy",
  title: "Website redesign",
  stage: "proposal",
  value_eur_cents: 350000,
  next_action: "Send proposal",
  created_at: "2026-07-25T13:10:00Z",
  updated_at: "2026-07-25T13:10:00Z"
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
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const consoleErrors = [];
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
        qualified_leads: 1,
        needs_review: 0,
        stale_records: 0,
        territories: 1,
        recent_leads: [lead]
      };
    } else if (url.pathname === "/api/v1/leads") {
      payload = [lead];
    } else if (url.pathname === "/api/v1/businesses/business-1" && method === "GET") {
      payload = detail;
    } else if (
      url.pathname === "/api/v1/businesses/business-1/notes"
      && method === "GET"
    ) {
      payload = [];
    } else if (url.pathname === "/api/v1/deals" && method === "GET") {
      payload = [deal];
    } else if (url.pathname === "/api/v1/tasks" && method === "GET") {
      payload = tasks;
    } else if (url.pathname === "/api/v1/tasks" && method === "POST") {
      const body = JSON.parse(request.postData() ?? "{}");
      const parentType = body.business_id ? "business" : "deal";
      const expectedTitle = parentType === "business"
        ? "Call decision maker"
        : "Review signed proposal";
      if (body.title !== expectedTitle || body.due_date !== "2026-07-30") {
        throw new Error("Task creation did not preserve operator-entered values.");
      }
      if (parentType === "business" && body.business_id !== "business-1") {
        throw new Error("Business task did not reference the selected business.");
      }
      if (parentType === "deal" && body.deal_id !== "deal-1") {
        throw new Error("Deal task did not reference the selected deal.");
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
        payload = { detail: "Task not found." };
        responseStatus = 404;
      } else {
        tasks[index] = {
          ...tasks[index],
          status: "completed",
          updated_at: "2026-07-25T13:30:00Z"
        };
        payload = tasks[index];
      }
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
  const businessTask = workspace.getByRole("region", {
    name: "Create task for Kildare Accountancy"
  });
  await businessTask.getByLabel("Task title").fill("Call decision maker");
  await businessTask.getByLabel("Due date").fill("2026-07-30");
  await businessTask.getByRole("button", { name: "Create task" }).click();
  await businessTask.getByText("Task created.").waitFor();

  await page.getByRole("button", { name: /^Deals$/ }).click();
  const proposal = page.getByRole("region", { name: "Proposal deals" });
  const dealTask = proposal.getByRole("region", {
    name: "Create task for Website redesign"
  });
  await dealTask.getByLabel("Task title").fill("Review signed proposal");
  await dealTask.getByLabel("Due date").fill("2026-07-30");
  await dealTask.getByRole("button", { name: "Create task" }).click();
  await dealTask.getByText("Task created.").waitFor();

  await page.getByRole("button", { name: /^Tasks$/ }).click();
  const taskWorkspace = page.getByRole("region", { name: "Tasks workspace" });
  const openTasks = taskWorkspace.getByRole("region", { name: "Open tasks" });
  await openTasks.getByText("Call decision maker").waitFor();
  await openTasks.getByText("Review signed proposal").waitFor();

  const businessTaskCard = openTasks.locator(".task-card", {
    hasText: "Call decision maker"
  });
  await businessTaskCard.getByRole("button", { name: "Mark completed" }).click();
  const completedTasks = taskWorkspace.getByRole("region", { name: "Completed tasks" });
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
