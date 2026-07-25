import { useMemo, useState } from "react";
import {
  Activity,
  Database,
  Globe2,
  LayoutDashboard,
  Map as MapIcon,
  Search,
  Settings,
  Target
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  captureVisibleCandidates,
  collectBoundedCandidates,
  createDiscoveryPlan,
  fetchDashboard,
  fetchLeads,
  fetchQueryTemplates,
  fetchTerritories,
  launchAssistedSession,
  markAssistedSessionReady,
  seedIreland,
  stopAssistedSession,
  updateCandidateReview
} from "./api";
import { CandidateReview } from "./CandidateReview";
import { GeographyWorkspace } from "./GeographyWorkspace";
import { QueryGroupReview } from "./QueryGroupReview";
import type { AssistedSession, AssistedSessionReview, Lead } from "./types";

type View = "Markets" | "Discover" | "Businesses" | "Deals" | "Tasks" | "Insights" | "Territories";

type Recommendation = {
  territoryId: string;
  territoryName: string;
  score: number;
  reasons: string[];
};

const navigation: Array<[View, typeof MapIcon]> = [
  ["Markets", Globe2],
  ["Discover", Search],
  ["Businesses", Target],
  ["Deals", LayoutDashboard],
  ["Tasks", Activity],
  ["Insights", Database],
  ["Territories", MapIcon]
];

const pageDescription: Record<View, string> = {
  Markets: "Choose where to prospect before spending time collecting businesses.",
  Discover: "Run a bounded, user-approved business discovery session.",
  Businesses: "Review persisted business observations and qualification evidence.",
  Deals: "Track commercial opportunities created from qualified businesses.",
  Tasks: "Keep research, outreach and follow-up work visible.",
  Insights: "Understand which markets and prospecting activity are producing results.",
  Territories: "Inspect validated boundaries and configured Irish discovery areas."
};

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
        <thead>
          <tr><th>Business</th><th>Category</th><th>Area</th><th>Observed</th><th>Freshness</th><th>Status</th></tr>
        </thead>
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
          {leads.length === 0 && <tr><td colSpan={6} className="empty-state">No persisted businesses yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <section className="panel page-panel empty-module">
      <span className="badge neutral">Planned module</span>
      <h2>{title}</h2>
      <p>{description}</p>
      <div className="empty-state">The application shell is ready. Persistent records and actions arrive in the next vertical slice.</div>
    </section>
  );
}

export function App() {
  const [view, setView] = useState<View>("Markets");
  const [territoryId, setTerritoryId] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [marketRegion, setMarketRegion] = useState("all");
  const [marketGoal, setMarketGoal] = useState("best-opportunities");
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [approvedQueryText, setApprovedQueryText] = useState("");
  const [currentQuerySequence, setCurrentQuerySequence] = useState(1);
  const [completedQuerySequences, setCompletedQuerySequences] = useState<number[]>([]);
  const [completedReviews, setCompletedReviews] = useState<AssistedSessionReview[]>([]);
  const [assistedSession, setAssistedSession] = useState<AssistedSession | null>(null);
  const [review, setReview] = useState<AssistedSessionReview | null>(null);
  const [busyCandidateId, setBusyCandidateId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: fetchDashboard });
  const territories = useQuery({ queryKey: ["territories"], queryFn: fetchTerritories });
  const templates = useQuery({ queryKey: ["query-templates"], queryFn: fetchQueryTemplates });
  const leads = useQuery({ queryKey: ["leads"], queryFn: fetchLeads });

  function retainCompletedReview(result: AssistedSessionReview) {
    const sequence = result.traversal_progress?.query_sequence;
    if (!sequence || !result.traversal_progress?.query_text.trim()) {
      return;
    }
    setCompletedReviews((completed) => [
      ...completed.filter((item) => item.traversal_progress?.query_sequence !== sequence),
      result
    ].sort((left, right) =>
      (left.traversal_progress?.query_sequence ?? 0) - (right.traversal_progress?.query_sequence ?? 0)
    ));
  }

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
  const plan = useMutation({
    mutationFn: () => createDiscoveryPlan(territoryId, templateId),
    onSuccess: (result) => {
      const firstQuery = result.prepared_queries[0];
      setCurrentQuerySequence(firstQuery.sequence);
      setApprovedQueryText(firstQuery.query_text);
      setCompletedQuerySequences([]);
      setCompletedReviews([]);
      setAssistedSession(null);
      setReview(null);
    }
  });
  const launchSession = useMutation({
    mutationFn: () => launchAssistedSession(territoryId, templateId, currentQuerySequence),
    onSuccess: setAssistedSession
  });
  const readySession = useMutation({
    mutationFn: (sessionId: string) => markAssistedSessionReady(sessionId),
    onSuccess: setAssistedSession
  });
  const captureSession = useMutation({
    mutationFn: (sessionId: string) => captureVisibleCandidates(sessionId),
    onSuccess: (result) => {
      setAssistedSession(result);
      setReview(result);
    }
  });
  const collectSession = useMutation({
    mutationFn: (sessionId: string) => collectBoundedCandidates(sessionId, approvedQueryText, currentQuerySequence),
    onSuccess: (result) => {
      setAssistedSession(result);
      setReview(result);
      retainCompletedReview(result);
      setCompletedQuerySequences((completed) =>
        completed.includes(currentQuerySequence) ? completed : [...completed, currentQuerySequence]
      );
    }
  });
  const candidateReview = useMutation({
    mutationFn: ({ sessionId, candidateId, included }: { sessionId: string; candidateId: string; included: boolean }) =>
      updateCandidateReview(sessionId, candidateId, included),
    onMutate: ({ candidateId }) => setBusyCandidateId(candidateId),
    onSuccess: (result) => {
      setAssistedSession(result);
      setReview(result);
      retainCompletedReview(result);
    },
    onSettled: () => setBusyCandidateId(null)
  });
  const stopSession = useMutation({
    mutationFn: (sessionId: string) => stopAssistedSession(sessionId),
    onSuccess: setAssistedSession
  });

  const groupedTemplates = new Map<string, NonNullable<typeof templates.data>>();
  for (const item of templates.data ?? []) {
    groupedTemplates.set(item.sector, [...(groupedTemplates.get(item.sector) ?? []), item]);
  }

  const recommendations = useMemo<Recommendation[]>(() => {
    const all = territories.data ?? [];
    const selected = marketRegion === "all" ? all : all.filter((item) => item.id === marketRegion);
    const preferredNames = ["Kildare County", "Wicklow County", "Galway County"];
    const ordered = [
      ...preferredNames.map((name) => selected.find((item) => item.name === name)).filter((item) => item !== undefined),
      ...selected.filter((item) => !preferredNames.includes(item.name))
    ].slice(0, 3);
    return ordered.map((item, index) => ({
      territoryId: item.id,
      territoryName: item.name,
      score: 82 - index * 6,
      reasons: ["Good prospect volume", "Useful local-business density", "Suitable for structured discovery"]
    }));
  }, [marketRegion, territories.data]);

  const sessionActive = assistedSession !== null && ["awaiting_operator", "ready", "capturing", "review"].includes(assistedSession.state);
  const currentPreparedQuery = plan.data?.prepared_queries.find((item) => item.sequence === currentQuerySequence);
  const nextPreparedQuery = plan.data?.prepared_queries.find((item) => item.sequence === currentQuerySequence + 1);

  function researchMarket(recommendation: Recommendation) {
    setTerritoryId(recommendation.territoryId);
    setView("Discover");
    plan.reset();
    setCurrentQuerySequence(1);
    setCompletedQuerySequences([]);
    setCompletedReviews([]);
    setAssistedSession(null);
    setReview(null);
  }

  function prepareNextQuery() {
    if (!nextPreparedQuery || assistedSession?.state !== "stopped") {
      return;
    }
    setCurrentQuerySequence(nextPreparedQuery.sequence);
    setApprovedQueryText(nextPreparedQuery.query_text);
    setAssistedSession(null);
    setReview(null);
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">LD</span><span><strong>LEADS</strong><small>Webify workspace</small></span></div>
        <nav aria-label="Primary navigation">
          {navigation.map(([label, Icon]) => (
            <button className={view === label ? "nav-item active" : "nav-item"} key={label} onClick={() => setView(label)}>
              <Icon size={17} /> {label}
            </button>
          ))}
        </nav>
        <button className="nav-item settings" disabled><Settings size={17} /> Settings <span className="nav-soon">soon</span></button>
      </aside>

      <main>
        <header className="page-header">
          <div><p className="eyebrow">WEBIFY / LOCAL BUSINESS GROWTH</p><h1>{view}</h1><p>{pageDescription[view]}</p></div>
          {view === "Markets" && <button className="primary-action" onClick={() => setView("Discover")}><Search size={16} /> Start discovery</button>}
        </header>

        {view === "Markets" && (
          <>
            <section className="market-hero">
              <div>
                <span className="badge neutral">Guided prospecting</span>
                <h2>Find the best markets before collecting businesses.</h2>
                <p>Choose a sector, region and commercial goal. LEADS will turn the selected market into a prepared discovery workflow.</p>
              </div>
              <div className="market-form panel">
                <label>Sector
                  <select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
                    <option value="">Select sector</option>
                    {(templates.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
                <label>Region
                  <select value={marketRegion} onChange={(event) => setMarketRegion(event.target.value)}>
                    <option value="all">All Ireland</option>
                    {(territories.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
                <label>Goal
                  <select value={marketGoal} onChange={(event) => setMarketGoal(event.target.value)}>
                    <option value="best-opportunities">Best Webify opportunities</option>
                    <option value="largest-market">Largest reachable market</option>
                    <option value="focused-research">Focused territory research</option>
                  </select>
                </label>
                <button className="primary-action full" disabled={!templateId} onClick={() => setShowRecommendations(true)}>Recommend markets</button>
                {!templateId && <small className="form-hint">Select a sector to generate the first guided recommendations.</small>}
              </div>
            </section>

            {dashboard.data && (
              <section className="metrics compact-metrics">
                <MetricCard label="BUSINESSES" value={dashboard.data.total_businesses} hint="persisted observations" />
                <MetricCard label="QUALIFIED" value={dashboard.data.qualified_leads} hint="ready for action" />
                <MetricCard label="NEEDS REVIEW" value={dashboard.data.needs_review} hint="research queue" />
                <MetricCard label="TERRITORIES" value={dashboard.data.territories} hint="Ireland coverage" />
              </section>
            )}

            {showRecommendations && (
              <section className="panel recommendation-panel">
                <div className="panel-heading"><div><h2>Recommended markets</h2><p>Demonstration scores until the public-data ingestion layer is implemented.</p></div><span className="badge ageing">Demo data</span></div>
                <div className="recommendation-grid">
                  {recommendations.map((item) => (
                    <article className="recommendation-card" key={item.territoryId}>
                      <div className="recommendation-score"><strong>{item.score}</strong><small>/100</small></div>
                      <h3>{item.territoryName}</h3>
                      <ul>{item.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                      <button className="secondary-action full" onClick={() => researchMarket(item)}>Research this market</button>
                    </article>
                  ))}
                  {recommendations.length === 0 && <div className="empty-state">Load the Ireland territory library to create recommendations.</div>}
                </div>
              </section>
            )}

            <section className="panel page-panel">
              <div className="panel-heading"><div><h2>Market coverage</h2><p>Validated Irish local-authority boundaries</p></div><button className="secondary-action" onClick={() => setView("Territories")}>Manage territories</button></div>
              <GeographyWorkspace />
            </section>
          </>
        )}

        {view === "Territories" && (
          <section className="panel page-panel">
            <div className="panel-heading"><div><h2>Geographic workspace</h2><p>Validated boundaries and configured discovery areas</p></div><button className="secondary-action" onClick={() => seed.mutate()}>Load Ireland territories</button></div>
            <GeographyWorkspace />
            <div className="card-grid territory-cards">
              {(territories.data ?? []).map((item) => <article className="record-card" key={item.id}><span className="badge neutral">{item.country_code}</span><h3>{item.name}</h3><p>{item.administrative_area ?? "No administrative area"}</p><small>{item.locality ?? "County-wide territory"}</small></article>)}
              {(territories.data ?? []).length === 0 && <div className="empty-state">No configured discovery territories.</div>}
            </div>
          </section>
        )}

        {view === "Discover" && (
          <>
            <section className="discovery-layout">
              <article className="panel page-panel">
                <div className="panel-heading"><div><h2>Prepare assisted session</h2><p>The visible browser opens only after explicit approval.</p></div></div>
                <label>Territory<select value={territoryId} disabled={sessionActive} onChange={(event) => setTerritoryId(event.target.value)}><option value="">Select territory</option>{(territories.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
                <label>Query group<select value={templateId} disabled={sessionActive} onChange={(event) => setTemplateId(event.target.value)}><option value="">Select query group</option>{Array.from(groupedTemplates.entries()).map(([sector, items]) => <optgroup key={sector} label={sector}>{items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>)}</select></label>
                <button className="primary-action" disabled={!territoryId || !templateId || plan.isPending || sessionActive} onClick={() => plan.mutate()}>Preview search plan</button>
              </article>
              <article className="panel page-panel">
                <div className="panel-heading"><div><h2>Plan preview</h2><p>Bounded and user-controlled</p></div></div>
                {!plan.data && <div className="empty-state">Select a territory and query group.</div>}
                {plan.data && <>
                  <h3>{plan.data.query_template_name} in {plan.data.territory_name}</h3>
                  <p className="body-copy">{plan.data.total_planned_queries} prepared queries · bounded result-panel traversal</p>
                  <ol className="query-checklist" aria-label="Prepared query checklist">
                    {plan.data.prepared_queries.map((query) => {
                      const state = completedQuerySequences.includes(query.sequence)
                        ? "completed"
                        : query.sequence === currentQuerySequence
                          ? "current"
                          : "pending";
                      return <li className={state} key={query.sequence}><span>{query.sequence}</span><div><strong>{query.phrase}</strong><small>{state}</small></div></li>;
                    })}
                  </ol>
                  <label>Current approved query
                    <input value={approvedQueryText} disabled={assistedSession?.state === "capturing" || assistedSession?.state === "review"} onChange={(event) => setApprovedQueryText(event.target.value)} />
                  </label>
                  {currentPreparedQuery && <small className="form-hint">Query {currentPreparedQuery.sequence} of {plan.data.total_planned_queries}. Each query requires a separate operator-approved session.</small>}
                  {!assistedSession && <button className="primary-action full" disabled={launchSession.isPending} onClick={() => launchSession.mutate()}>{launchSession.isPending ? "Launching visible browser…" : `Launch query ${currentQuerySequence}`}</button>}
                  {assistedSession && <div className="notice">Session status: <strong>{assistedSession.state.replace("_", " ")}</strong>{assistedSession.state === "awaiting_operator" && <p>Use the visible browser to sign in or adjust the approved query, then confirm readiness here.</p>}</div>}
                  {assistedSession?.state === "awaiting_operator" && assistedSession.session_id && <button className="primary-action full" disabled={readySession.isPending} onClick={() => readySession.mutate(assistedSession.session_id!)}>Browser is ready</button>}
                  {assistedSession?.state === "ready" && assistedSession.session_id && <>
                    <button className="primary-action full" disabled={!approvedQueryText.trim() || collectSession.isPending} onClick={() => collectSession.mutate(assistedSession.session_id!)}>{collectSession.isPending ? "Collecting bounded results…" : "Collect bounded results"}</button>
                    <button className="secondary-action full" disabled={captureSession.isPending} onClick={() => captureSession.mutate(assistedSession.session_id!)}>{captureSession.isPending ? "Capturing visible results…" : "Capture currently visible only"}</button>
                  </>}
                  {review?.traversal_progress && <div className="notice traversal-summary" aria-label="Traversal summary">
                    <strong>{review.traversal_progress.unique_cards} unique cards collected</strong>
                    <p>{review.traversal_progress.scroll_step} scroll steps · {review.traversal_progress.elapsed_seconds.toFixed(1)} seconds · stopped: {review.traversal_progress.stop_reason?.replaceAll("_", " ") ?? "unknown"}</p>
                  </div>}
                  {sessionActive && assistedSession?.session_id && <button className="secondary-action full" disabled={stopSession.isPending} onClick={() => stopSession.mutate(assistedSession.session_id!)}>Stop assisted session</button>}
                  {assistedSession?.state === "stopped" && nextPreparedQuery && <button className="primary-action full" onClick={prepareNextQuery}>Prepare query {nextPreparedQuery.sequence}</button>}
                  {assistedSession?.state === "stopped" && !nextPreparedQuery && completedQuerySequences.length === plan.data.total_planned_queries && <div className="notice traversal-summary"><strong>Query group complete</strong><p>All prepared queries were collected with explicit operator approval.</p></div>}
                  {review && assistedSession?.state === "review" && assistedSession.session_id && <CandidateReview review={review} busyCandidateId={busyCandidateId} onToggle={(candidateId, included) => candidateReview.mutate({ sessionId: assistedSession.session_id!, candidateId, included })} />}
                  {(launchSession.isError || readySession.isError || captureSession.isError || collectSession.isError || candidateReview.isError || stopSession.isError) && <div className="notice error">The assisted session action failed. Review the backend message and retry.</div>}
                </>}
              </article>
            </section>
            <QueryGroupReview reviews={completedReviews} />
          </>
        )}

        {view === "Businesses" && <section className="panel page-panel"><div className="panel-heading"><div><h2>Business database</h2><p>{leads.data?.length ?? 0} persisted observations</p></div></div><LeadTable leads={leads.data ?? []} /></section>}
        {view === "Deals" && <PlaceholderPage title="Deals pipeline" description="Qualified businesses will become commercial opportunities with stages, value, owner and next action." />}
        {view === "Tasks" && <PlaceholderPage title="Tasks and follow-up" description="Research, outreach and proposal tasks will be linked to businesses and deals." />}
        {view === "Insights" && <PlaceholderPage title="Market and pipeline insights" description="Territory, sector, discovery and conversion metrics will share one reporting model." />}

        {(dashboard.isError || territories.isError || templates.isError || leads.isError) && <div className="notice error">The backend is unavailable or returned an invalid response.</div>}
      </main>
    </div>
  );
}
