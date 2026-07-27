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
    const url = new URL(route.request().url());
    let payload;

    if (url.pathname === "/api/v1/dashboard") {
      payload = { total_businesses: 8, qualified_leads: 3, needs_review: 2, stale_records: 1, territories: 4, recent_leads: [] };
    } else if (url.pathname === "/api/v1/deals") {
      payload = [
        {
          id: "deal-1", business_id: "business-1", business_name: "Galway Dental",
          title: "SEO retainer", stage: "proposal", value_eur_cents: 720000,
          next_action: "Send tailored audit", created_at: "2026-07-24T10:00:00Z", updated_at: "2026-07-27T09:00:00Z"
        },
        {
          id: "deal-2", business_id: "business-2", business_name: "Kildare Accountancy",
          title: "Website redesign", stage: "won", value_eur_cents: 350000,
          next_action: null, created_at: "2026-07-25T13:10:00Z", updated_at: "2026-07-25T13:10:00Z"
        }
      ];
    } else if (url.pathname === "/api/v1/tasks") {
      payload = [
        {
          id: "task-1", title: "Prepare SEO audit", due_date: "2026-07-20", status: "open",
          business_id: null, deal_id: "deal-1", parent_type: "deal", parent_name: "SEO retainer",
          created_at: "2026-07-20T09:05:00Z", updated_at: "2026-07-20T09:05:00Z"
        },
        {
          id: "task-2", title: "Call owner", due_date: null, status: "open",
          business_id: "business-2", deal_id: null, parent_type: "business", parent_name: "Kildare Accountancy",
          created_at: "2026-07-21T09:05:00Z", updated_at: "2026-07-21T09:05:00Z"
        },
        {
          id: "task-3", title: "Review notes", due_date: null, status: "completed",
          business_id: "business-1", deal_id: null, parent_type: "business", parent_name: "Galway Dental",
          created_at: "2026-07-19T09:05:00Z", updated_at: "2026-07-22T09:05:00Z"
        }
      ];
    } else if (url.pathname === "/api/v1/leads" || url.pathname === "/api/v1/territories" || url.pathname === "/api/v1/query-templates" || url.pathname.startsWith("/api/v1/geography/")) {
      payload = [];
    }

    await route.fulfill({
      status: payload === undefined ? 404 : 200,
      contentType: "application/json",
      body: JSON.stringify(payload ?? { detail: "Not found" })
    });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Insights$/ }).click();
  const workspace = page.getByRole("region", { name: "Operational insights" });

  await workspace.getByText("10700,00 €", { exact: true }).waitFor();
  await workspace.getByRole("region", { name: "Deal stage distribution" }).getByText("Proposal").waitFor();
  await workspace.getByRole("region", { name: "Open task distribution" }).getByText("Business tasks").waitFor();
  await workspace.getByRole("region", { name: "Attention list" }).getByText("Prepare SEO audit").waitFor();
  await workspace.getByText("Send tailored audit", { exact: true }).waitFor();

  await page.screenshot({ path: "artifacts/screenshots/operational-insights.png", fullPage: true });
  if (consoleErrors.length > 0) throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
  await browser.close();
} finally {
  server.kill();
}
