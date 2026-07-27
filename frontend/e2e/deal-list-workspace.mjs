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

let deals = [
  {
    id: "deal-1", business_id: "business-1", business_name: "Kildare Accountancy",
    title: "Website redesign", stage: "proposal", value_eur_cents: 350000,
    next_action: "Send proposal", created_at: "2026-07-25T13:10:00Z", updated_at: "2026-07-25T13:10:00Z"
  },
  {
    id: "deal-2", business_id: "business-2", business_name: "Galway Dental",
    title: "SEO retainer", stage: "discovery", value_eur_cents: 720000,
    next_action: "Confirm scope", created_at: "2026-07-24T10:00:00Z", updated_at: "2026-07-26T10:00:00Z"
  }
];

const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1"], {
  stdio: "inherit",
  shell: process.platform === "win32"
});

try {
  await waitForServer("http://127.0.0.1:5173");
  await mkdir("artifacts/screenshots", { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    args: process.platform === "win32" ? ["--enable-webgl"] : ["--use-gl=swiftshader", "--enable-webgl"]
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    let payload;
    let status = 200;

    if (url.pathname === "/api/v1/dashboard") {
      payload = { total_businesses: 2, qualified_leads: 2, needs_review: 0, stale_records: 0, territories: 1, recent_leads: [] };
    } else if (url.pathname === "/api/v1/leads") {
      payload = [];
    } else if (url.pathname === "/api/v1/deals" && method === "GET") {
      payload = deals;
    } else if (url.pathname === "/api/v1/deals/deal-2" && method === "PATCH") {
      const body = JSON.parse(request.postData() ?? "{}");
      if (body.stage !== "proposal" || body.next_action !== "Send tailored audit") {
        throw new Error("List edit did not submit exact operator changes.");
      }
      deals = deals.map((deal) => deal.id === "deal-2"
        ? { ...deal, ...body, updated_at: "2026-07-27T09:00:00Z" }
        : deal);
      payload = deals.find((deal) => deal.id === "deal-2");
    } else if (url.pathname === "/api/v1/tasks" && method === "POST") {
      const body = JSON.parse(request.postData() ?? "{}");
      if (body.deal_id !== "deal-2" || body.title !== "Prepare SEO audit") {
        throw new Error("List task did not reference the exact deal.");
      }
      payload = {
        id: "task-1", title: body.title, due_date: body.due_date, status: "open",
        business_id: null, deal_id: "deal-2", parent_type: "deal", parent_name: "SEO retainer",
        created_at: "2026-07-27T09:05:00Z", updated_at: "2026-07-27T09:05:00Z"
      };
      status = 201;
    } else if (url.pathname === "/api/v1/tasks" && method === "GET") {
      payload = [];
    } else if (url.pathname === "/api/v1/territories" || url.pathname === "/api/v1/query-templates" || url.pathname.startsWith("/api/v1/geography/")) {
      payload = [];
    }

    await route.fulfill({
      status: payload === undefined ? 404 : status,
      contentType: "application/json",
      body: JSON.stringify(payload ?? { detail: "Not found" })
    });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Deals$/ }).click();
  const workspace = page.getByRole("region", { name: "Deals workspace" });
  await workspace.getByRole("button", { name: "List" }).click();
  const list = workspace.getByRole("region", { name: "Deal list" });

  await workspace.getByLabel("Sort by").selectOption("value_desc");
  const rows = list.locator(".deal-card");
  if ((await rows.first().innerText()).includes("SEO retainer") === false) {
    throw new Error("Highest-value deal was not sorted first.");
  }

  await workspace.getByLabel("Search deals").fill("Galway");
  await list.getByText("SEO retainer", { exact: true }).waitFor();
  if (await list.getByText("Website redesign", { exact: true }).count()) {
    throw new Error("Text filter retained a non-matching deal.");
  }
  await workspace.getByLabel("Stage").selectOption("discovery");

  const row = rows.filter({ hasText: "SEO retainer" });
  await row.getByRole("button", { name: "Edit deal" }).click();
  const editor = row.getByLabel("Edit SEO retainer");
  await editor.getByLabel("Stage").selectOption("proposal");
  await editor.getByLabel("Next action").fill("Send tailored audit");
  await editor.getByRole("button", { name: "Save deal" }).click();

  await workspace.getByLabel("Stage").selectOption("all");
  await row.getByText("Send tailored audit").waitFor();

  const task = row.getByRole("region", { name: "Create task for SEO retainer" });
  await task.getByLabel("Task title").fill("Prepare SEO audit");
  await task.getByLabel("Due date").fill("2026-07-31");
  await task.getByRole("button", { name: "Create task" }).click();
  await task.getByText("Task created.").waitFor();

  await workspace.getByLabel("Search deals").fill("");
  await page.screenshot({ path: "artifacts/screenshots/deal-list-workspace.png", fullPage: true });

  if (consoleErrors.length > 0) throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
  await browser.close();
} finally {
  server.kill();
}
