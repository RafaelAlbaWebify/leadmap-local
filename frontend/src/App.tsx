import { useState } from "react";
import {
  Activity,
  Database,
  Download,
  Globe2,
  LayoutDashboard,
  Map as MapIcon,
  Search,
  Settings,
  Target
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDiscoveryPlan,
  fetchDashboard,
  fetchLeads,
  fetchQueryTemplates,
  fetchTerritories,
  seedIreland
} from "./api";
import { GeographyWorkspace } from "./GeographyWorkspace";
import type { Lead } from "./types";

type View = "Overview" | "Territories" | "Discovery" | "Leads" | "Exports";

const navigation: Array<[View | "Coverage" | "Data quality" | "Activity", typeof MapIcon]> = [
  ["Overview", LayoutDashboard],
  ["Territories", MapIcon],
  ["Discovery", Search],
  ["Leads", Target],
  ["Coverage", Globe2],
  ["Data quality", Database],
  ["Exports", Download],
  ["Activity", Activity]
];

function MetricCard({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <article className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-hint">{hint}</div>
    </article>
  );
}

function LeadTable({ leads }: { leads: Lead[] }) {
  return (
    <div className="table-scroll">
      <table>
        <thead><tr><th>Business</th><th>Category</th><th>Area</th><th>Observed</th><th>Freshness</th><th>Status</th></tr></thead>
        <tbody>
          {leads.map((lead) => (
            <tr key={`${lead.id}-${lead.last_observed_at}`}>
              <td><strong>{lead.name}</strong><small>{lead.website ?? "No website captured"}</small></td>
              <td>{lead.category}</td>
              <td>{lead.locality}{lead.postal_area ? ` · ${lead.postal_area}` : ""}</td>
              <td>{new Date(lead.last_observed_at).toLocaleDateString()}</td>
              <td><span className={`badge ${lead.freshness}`}>{lead.freshness.replace("_", " ")}</span></td>
              <td><span className="badge neutral">{lead.qualification_status.replace("_", " ")}</span></td>
            </tr>
          ))}
          {leads.length === 0 && <tr><td colSpan={6} className="empty-state">No persisted leads yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export function App() {
  const [view, setView] = useState<View>("Overview");
  const [territoryId, setTerritoryId] = useState("");
  const [templateId, setTemplateId] = useState("");
  const queryClient = useQueryClient();
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: fetchDashboard });
  const territories = useQuery({ queryKey: ["territories"], queryFn: fetchTerritories });
  const templates = useQuery({ queryKey: ["query-templates"], queryFn: fetchQueryTemplates });
  const leads = useQuery({ queryKey: ["leads"], queryFn: fetchLeads });

  const seed = useMutation({
    mutationFn: seedIreland,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["territories"] }),
        queryClient.invalidateQueries({ queryKey: ["query-templates"] })
      ]);
    }
  });
  const plan = useMutation({ mutationFn: () => createDiscoveryPlan(territoryId, templateId) });
  const groupedTemplates = new Map<string, NonNullable<typeof templates.data>>();
  for (const item of templates.data ?? []) groupedTemplates.set(item.sector, [...(groupedTemplates.get(item.sector) ?? []), item]);

  const pageDescription = {
    Overview: "Plan searches, review captured businesses and keep territory data current.",
    Territories: "Inspect validated geographic boundaries and configured discovery areas.",
    Discovery: "Prepare a bounded, user-approved assisted search plan.",
    Leads: "Review persisted business observations and freshness metadata.",
    Exports: "Download stable CSV or JSON records for CRM and related applications."
  }[view];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">LM</span> LeadMap</div>
        <nav>
          {navigation.map(([label, Icon]) => {
            const enabled = ["Overview", "Territories", "Discovery", "Leads", "Exports"].includes(label);
            return (
              <button className={view === label ? "nav-item active" : "nav-item"} key={label} disabled={!enabled} onClick={() => enabled && setView(label as View)}>
                <Icon size={17} /> {label}{!enabled && <span className="nav-soon">soon</span>}
              </button>
            );
          })}
        </nav>
        <button className="nav-item settings" disabled><Settings size={17} /> Settings <span className="nav-soon">soon</span></button>
      </aside>

      <main>
        <header className="page-header">
          <div><p className="eyebrow">IRELAND / TERRITORY INTELLIGENCE</p><h1>{view}</h1><p>{pageDescription}</p></div>
          {view === "Overview" && <button className="primary-action" onClick={() => setView("Discovery")}><Search size={16} /> Start discovery</button>}
        </header>

        {view === "Overview" && dashboard.data && (
          <>
            <section className="metrics">
              <MetricCard label="TOTAL BUSINESSES" value={dashboard.data.total_businesses} hint="across all territories" />
              <MetricCard label="QUALIFIED" value={dashboard.data.qualified_leads} hint="ready for export" />
              <MetricCard label="NEEDS REVIEW" value={dashboard.data.needs_review} hint="unresolved candidates" />
              <MetricCard label="STALE RECORDS" value={dashboard.data.stale_records} hint="verification due" />
              <MetricCard label="TERRITORIES" value={dashboard.data.territories} hint="configured areas" />
            </section>
            <section className="workspace-grid">
              <article className="panel map-panel">
                <div className="panel-heading"><div><h2>Territory workspace</h2><p>Latest validated local-authority artifact</p></div><button className="secondary-action" onClick={() => setView("Territories")}>Manage</button></div>
                <GeographyWorkspace />
              </article>
              <article className="panel intelligence">
                <div className="panel-heading"><div><h2>Workspace setup</h2><p>Persistent database status</p></div></div>
                <p className="body-copy">Load the Ireland starter library to create Galway City and five reusable query groups.</p>
                <button className="primary-action full" onClick={() => seed.mutate()} disabled={seed.isPending}>{seed.isPending ? "Loading…" : "Load Ireland starter data"}</button>
                {seed.data && <p className="success-text">Starter data ready: {seed.data.total_query_templates} query groups.</p>}
              </article>
            </section>
            <section className="panel table-panel"><div className="panel-heading"><div><h2>Recently observed businesses</h2><p>Acquisition date and freshness are retained.</p></div></div><LeadTable leads={dashboard.data.recent_leads} /></section>
          </>
        )}

        {view === "Territories" && (
          <section className="panel page-panel">
            <div className="panel-heading"><div><h2>Geographic workspace</h2><p>Validated boundaries and configured discovery areas</p></div><button className="secondary-action" onClick={() => seed.mutate()}>Load Ireland starter</button></div>
            <GeographyWorkspace />
            <div className="card-grid territory-cards">
              {(territories.data ?? []).map((item) => <article className="record-card" key={item.id}><span className="badge neutral">{item.country_code}</span><h3>{item.name}</h3><p>{item.administrative_area ?? "No administrative area"}</p><small>{item.locality ?? "No locality"}</small></article>)}
              {(territories.data ?? []).length === 0 && <div className="empty-state">No configured discovery territories.</div>}
            </div>
          </section>
        )}

        {view === "Discovery" && (
          <section className="discovery-layout">
            <article className="panel page-panel">
              <div className="panel-heading"><div><h2>Prepare assisted session</h2><p>No browser opens until you approve a later capture step.</p></div></div>
              <label>Territory<select value={territoryId} onChange={(event) => setTerritoryId(event.target.value)}><option value="">Select territory</option>{(territories.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
              <label>Query group<select value={templateId} onChange={(event) => setTemplateId(event.target.value)}><option value="">Select query group</option>{Array.from(groupedTemplates.entries()).map(([sector, items]) => <optgroup key={sector} label={sector}>{items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>)}</select></label>
              <button className="primary-action" disabled={!territoryId || !templateId || plan.isPending} onClick={() => plan.mutate()}>Preview search plan</button>
            </article>
            <article className="panel page-panel">
              <div className="panel-heading"><div><h2>Plan preview</h2><p>Bounded and user-controlled</p></div></div>
              {!plan.data && <div className="empty-state">Select a territory and query group.</div>}
              {plan.data && <><h3>{plan.data.query_template_name} in {plan.data.territory_name}</h3><p className="body-copy">{plan.data.total_planned_queries} prepared queries · maximum {plan.data.max_results_per_query} visible results each</p><div className="query-chips">{plan.data.phrases.map((phrase) => <span key={phrase}>{phrase}</span>)}</div><div className="notice">Browser capture remains disabled until the Playwright session state machine is implemented and fixture-tested.</div></>}
            </article>
          </section>
        )}

        {view === "Leads" && <section className="panel page-panel"><div className="panel-heading"><div><h2>Lead database</h2><p>{leads.data?.length ?? 0} persisted observations</p></div></div><LeadTable leads={leads.data ?? []} /></section>}
        {view === "Exports" && <section className="panel page-panel"><div className="panel-heading"><div><h2>Export records</h2><p>Versioned contracts for CRM and other local tools</p></div></div><div className="export-grid"><a className="export-card" href="/api/v1/exports/leads.csv"><Download size={22} /><strong>CSV export</strong><span>Tabular CRM import</span></a><a className="export-card" href="/api/v1/exports/leads.json"><Download size={22} /><strong>JSON export</strong><span>Versioned machine-readable package</span></a></div></section>}
        {(dashboard.isError || territories.isError || templates.isError || leads.isError) && <div className="notice error">The backend is unavailable or returned an invalid response.</div>}
      </main>
    </div>
  );
}
