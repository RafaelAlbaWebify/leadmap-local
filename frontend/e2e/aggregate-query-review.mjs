import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";

const territories = [{
  id: "territory-kildare",
  name: "Kildare County",
  country_code: "IE",
  administrative_area: "County Kildare",
  locality: null,
  created_at: "2026-07-25T08:00:00Z"
}];

const template = {
  id: "template-accountancy",
  name: "Accountancy",
  sector: "Professional Services",
  countries: ["IE"],
  phrases: ["accountant", "tax advisor"],
  created_at: "2026-07-25T08:00:00Z"
};

function queryText(sequence) {
  return sequence === 1
    ? "accountant in Kildare County, IE"
    : "tax advisor in Kildare County, IE";
}

function session(state, sequence) {
  return {
    session_id: state === "stopped" ? "session-aggregate" : "session-aggregate",
    state,
    territory_id: "territory-kildare",
    query_template_id: "template-accountancy",
    start_url: `https://www.google.com/maps/search/${encodeURIComponent(queryText(sequence))}`,
    error: null
  };
}

function candidate({ id, providerKey, name, sequence, rank, category = "Accountant" }) {
  return {
    candidate_id: id,
    provider_key: providerKey,
    displayed_name: name,
    normalized_name: name.toLocaleLowerCase(),
    category,
    address_text: "Kildare County",
    phone: null,
    website: `https://${providerKey}.example`,
    source_url: `https://www.google.com/maps/place/${providerKey}`,
    latitude: null,
    longitude: null,
    raw_evidence: `${name} · ${category}`,
    included: true,
    query_text: queryText(sequence),
    query_sequence: sequence,
    result_rank: rank,
    first_seen_scroll_step: 0,
    captured_at: `2026-07-25T08:0${sequence}:00Z`
  };
}

function boundedReview(sequence) {
  const candidates = sequence === 1
    ? [
        candidate({ id: "q1-place-1", providerKey: "place-1", name: "Kildare Accountancy", sequence, rank: 1 }),
        candidate({ id: "q1-place-2", providerKey: "place-2", name: "County Books", sequence, rank: 2, category: "Bookkeeping service" })
      ]
    : [
        candidate({ id: "q2-place-1", providerKey: "place-1", name: "Kildare Accountancy", sequence, rank: 3 }),
        candidate({ id: "q2-place-3", providerKey: "place-3", name: "Taxwise Kildare", sequence, rank: 1, category: "Tax consultant" })
      ];
  return {
    ...session("review", sequence),
    traversal_progress: {
      query_text: queryText(sequence),
      query_sequence: sequence,
      scroll_step: 4,
      unique_cards: candidates.length,
      stagnant_scrolls: 3,
      elapsed_seconds: 4.2,
      stop_reason: "no_new_results"
    },
    traversal_stop_reason: "no_new_results",
    candidates,
    included_count: candidates.length,
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
  let currentSequence = 1;
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const requestUrl = new URL(request.url());
    const path = requestUrl.pathname + requestUrl.search;
    const method = request.method();
    let payload;

    if (path === "/api/v1/dashboard") {
      payload = { total_businesses: 0, qualified_leads: 0, needs_review: 0, stale_records: 0, territories: 1, recent_leads: [] };
    } else if (path === "/api/v1/territories") {
      payload = territories;
    } else if (path === "/api/v1/query-templates?country_code=IE") {
      payload = [template];
    } else if (path === "/api/v1/leads") {
      payload = [];
    } else if (path === "/api/v1/geography/artifacts" || path === "/api/v1/geography/coverage" || path === "/api/v1/geography/territory-links") {
      payload = [];
    } else if (path === "/api/v1/discovery/prepared-plan" && method === "POST") {
      payload = {
        territory_id: "territory-kildare",
        territory_name: "Kildare County",
        country_code: "IE",
        query_template_id: "template-accountancy",
        query_template_name: "Accountancy",
        sector: "Professional Services",
        max_results_per_query: 20,
        total_planned_queries: 2,
        prepared_queries: [
          { sequence: 1, phrase: "accountant", query_text: queryText(1) },
          { sequence: 2, phrase: "tax advisor", query_text: queryText(2) }
        ],
        mode: "assisted"
      };
    } else if (path === "/api/v1/discovery/prepared-session" && method === "POST") {
      const body = JSON.parse(request.postData() ?? "{}");
      currentSequence = body.query_sequence;
      payload = session("awaiting_operator", currentSequence);
    } else if (path === "/api/v1/discovery/session/session-aggregate/ready" && method === "POST") {
      payload = session("ready", currentSequence);
    } else if (path.startsWith("/api/v1/discovery/session/session-aggregate/collect-bounded?") && method === "POST") {
      payload = boundedReview(currentSequence);
    } else if (path === "/api/v1/discovery/session/session-aggregate" && method === "DELETE") {
      payload = session("stopped", currentSequence);
    }

    if (payload === undefined) {
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });

  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Discover$/ }).click();
  await page.getByLabel("Territory").selectOption("territory-kildare");
  await page.getByLabel("Query group").selectOption("template-accountancy");
  await page.getByRole("button", { name: "Preview search plan" }).click();

  for (const sequence of [1, 2]) {
    await page.getByRole("button", { name: `Launch query ${sequence}` }).click();
    await page.getByText("awaiting operator").waitFor();
    await page.getByRole("button", { name: "Browser is ready" }).click();
    await page.getByRole("button", { name: "Collect bounded results" }).click();
    await page.getByLabel("Traversal summary").waitFor();
    if (sequence === 1) {
      await page.getByRole("button", { name: "Stop assisted session" }).click();
      await page.getByRole("button", { name: "Prepare query 2" }).click();
    }
  }

  const aggregate = page.getByRole("region", { name: "Aggregate business review" });
  await aggregate.waitFor();
  await aggregate.getByText("4", { exact: true }).first().waitFor();
  await aggregate.getByText("3", { exact: true }).first().waitFor();
  await aggregate.getByText("1", { exact: true }).first().waitFor();
  const repeated = aggregate.locator(".aggregate-business").filter({ hasText: "Kildare Accountancy" });
  await repeated.getByText("Q1").waitFor();
  await repeated.getByText("rank 1").waitFor();
  await repeated.getByText("Q2").waitFor();
  await repeated.getByText("rank 3").waitFor();
  await page.screenshot({ path: "artifacts/screenshots/discover-aggregate-query-review.png", fullPage: true });

  if (consoleErrors.length > 0) {
    throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
  }
  await browser.close();
} finally {
  server.kill();
}
