import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createDeal, fetchDeals, updateDeal, type Deal, type DealStage } from "./dealApi";
import { TaskCreate } from "./TasksWorkspace";
import "./dealsWorkspace.css";

const stageOptions: Array<{ value: DealStage; label: string }> = [
  { value: "lead", label: "Lead" },
  { value: "discovery", label: "Discovery" },
  { value: "proposal", label: "Proposal" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" }
];

type DealView = "board" | "list";
type DealSort = "updated_desc" | "value_desc" | "business_asc" | "title_asc";

function stageLabel(stage: DealStage): string {
  return stageOptions.find((option) => option.value === stage)?.label ?? stage;
}

function formatMoney(valueEurCents: number | null): string {
  if (valueEurCents === null) {
    return "Value not set";
  }
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2
  }).format(valueEurCents / 100);
}

function formatUpdated(value: string): string {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function BusinessDealCreate({
  businessId,
  qualificationStatus
}: {
  businessId: string;
  qualificationStatus: string;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [stage, setStage] = useState<DealStage>("lead");
  const [valueEur, setValueEur] = useState("");
  const [nextAction, setNextAction] = useState("");
  const mutation = useMutation({
    mutationFn: () => createDeal(businessId, {
      title,
      stage,
      value_eur_cents: valueEur.trim() ? Math.round(Number(valueEur) * 100) : null,
      next_action: nextAction.trim() || null
    }),
    onSuccess: async () => {
      setTitle("");
      setStage("lead");
      setValueEur("");
      setNextAction("");
      await queryClient.invalidateQueries({ queryKey: ["deals"] });
    }
  });
  const numericValue = valueEur.trim() ? Number(valueEur) : 0;
  const canSubmit = qualificationStatus === "qualified"
    && title.trim().length > 0
    && title.trim().length <= 300
    && Number.isFinite(numericValue)
    && numericValue >= 0;

  return qualificationStatus !== "qualified" ? (
    <section className="deal-create locked" aria-label="Create deal">
      <h3>Create deal</h3>
      <p>Qualify this business before creating a commercial opportunity.</p>
    </section>
  ) : (
    <section className="deal-create" aria-label="Create deal">
      <div className="panel-heading">
        <div>
          <h3>Create deal</h3>
          <p>Turn this qualified business into an explicit opportunity.</p>
        </div>
      </div>
      <div className="deal-form-grid">
        <label>
          Title
          <input value={title} maxLength={300} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          Stage
          <select value={stage} onChange={(event) => setStage(event.target.value as DealStage)}>
            {stageOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          Value (€)
          <input
            type="number"
            min="0"
            step="0.01"
            value={valueEur}
            onChange={(event) => setValueEur(event.target.value)}
          />
        </label>
        <label>
          Next action
          <input value={nextAction} maxLength={1000} onChange={(event) => setNextAction(event.target.value)} />
        </label>
      </div>
      <button
        className="primary-action compact"
        disabled={!canSubmit || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "Creating…" : "Create deal"}
      </button>
      {mutation.isSuccess && <div className="notice success" role="status">Deal created.</div>}
      {mutation.isError && (
        <div className="notice error" role="alert">
          Deal could not be created. Your entered values are retained.
        </div>
      )}
    </section>
  );
}

function DealCard({ deal, layout = "board" }: { deal: Deal; layout?: DealView }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [stage, setStage] = useState<DealStage>(deal.stage);
  const [nextAction, setNextAction] = useState(deal.next_action ?? "");
  const mutation = useMutation({
    mutationFn: () => updateDeal(deal.id, { stage, next_action: nextAction.trim() || null }),
    onSuccess: async (updated) => {
      queryClient.setQueryData<Deal[]>(["deals"], (current) =>
        current?.map((item) => item.id === updated.id ? updated : item) ?? [updated]
      );
      setEditing(false);
      await queryClient.invalidateQueries({ queryKey: ["deals"] });
    }
  });

  function cancelEditing() {
    setStage(deal.stage);
    setNextAction(deal.next_action ?? "");
    setEditing(false);
    mutation.reset();
  }

  return (
    <article className={`deal-card ${layout === "list" ? "deal-list-card" : ""}`}>
      <div className="deal-card-summary">
        <div className="deal-card-identity">
          <strong>{deal.title}</strong>
          <p>{deal.business_name}</p>
        </div>
        {layout === "list" && <span className="deal-stage-badge">{stageLabel(deal.stage)}</span>}
        <span>{formatMoney(deal.value_eur_cents)}</span>
        <small>{deal.next_action ?? "No next action"}</small>
        {layout === "list" && <small>Updated {formatUpdated(deal.updated_at)}</small>}
        {!editing && (
          <button className="secondary-action compact" onClick={() => setEditing(true)}>Edit deal</button>
        )}
      </div>
      {editing && (
        <div className="deal-edit" aria-label={`Edit ${deal.title}`}>
          <label>
            Stage
            <select
              value={stage}
              disabled={mutation.isPending}
              onChange={(event) => setStage(event.target.value as DealStage)}
            >
              {stageOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label>
            Next action
            <input
              value={nextAction}
              maxLength={1000}
              disabled={mutation.isPending}
              onChange={(event) => setNextAction(event.target.value)}
            />
          </label>
          <div className="deal-edit-actions">
            <button
              className="primary-action compact"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? "Saving…" : "Save deal"}
            </button>
            <button className="secondary-action compact" disabled={mutation.isPending} onClick={cancelEditing}>
              Cancel
            </button>
          </div>
          {mutation.isError && (
            <div className="notice error" role="alert">
              Deal could not be updated. Your entered values are retained.
            </div>
          )}
        </div>
      )}
      <TaskCreate dealId={deal.id} label={`Create task for ${deal.title}`} />
    </article>
  );
}

function sortDeals(deals: Deal[], sort: DealSort): Deal[] {
  return [...deals].sort((left, right) => {
    if (sort === "value_desc") {
      return (right.value_eur_cents ?? -1) - (left.value_eur_cents ?? -1);
    }
    if (sort === "business_asc") {
      return left.business_name.localeCompare(right.business_name, "en", { sensitivity: "base" });
    }
    if (sort === "title_asc") {
      return left.title.localeCompare(right.title, "en", { sensitivity: "base" });
    }
    return Date.parse(right.updated_at) - Date.parse(left.updated_at);
  });
}

export function DealsWorkspace() {
  const deals = useQuery({ queryKey: ["deals"], queryFn: fetchDeals });
  const [view, setView] = useState<DealView>("board");
  const [stageFilter, setStageFilter] = useState<"all" | DealStage>("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<DealSort>("updated_desc");

  const visibleDeals = useMemo(() => {
    if (!deals.data) return [];
    const term = search.trim().toLocaleLowerCase();
    const filtered = deals.data.filter((deal) => {
      const matchesStage = stageFilter === "all" || deal.stage === stageFilter;
      const matchesText = !term
        || deal.title.toLocaleLowerCase().includes(term)
        || deal.business_name.toLocaleLowerCase().includes(term);
      return matchesStage && matchesText;
    });
    return sortDeals(filtered, sort);
  }, [deals.data, search, sort, stageFilter]);

  if (deals.isPending) return <div className="notice">Loading deals…</div>;
  if (deals.isError) return <div className="notice error">Deals could not be loaded.</div>;

  return (
    <section className="deals-workspace" aria-label="Deals workspace">
      <header className="deals-toolbar">
        <div className="deal-view-switch" role="group" aria-label="Deal view">
          <button className={view === "board" ? "active" : ""} onClick={() => setView("board")}>Board</button>
          <button className={view === "list" ? "active" : ""} onClick={() => setView("list")}>List</button>
        </div>
        {view === "list" && (
          <div className="deal-list-controls">
            <label>
              Search deals
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Business or deal title" />
            </label>
            <label>
              Stage
              <select value={stageFilter} onChange={(event) => setStageFilter(event.target.value as "all" | DealStage)}>
                <option value="all">All stages</option>
                {stageOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label>
              Sort by
              <select value={sort} onChange={(event) => setSort(event.target.value as DealSort)}>
                <option value="updated_desc">Recently updated</option>
                <option value="value_desc">Highest value</option>
                <option value="business_asc">Business name</option>
                <option value="title_asc">Deal title</option>
              </select>
            </label>
          </div>
        )}
      </header>

      {deals.data.length === 0 ? (
        <div className="empty-state">No deals</div>
      ) : view === "board" ? (
        <section className="deal-pipeline" aria-label="Deals pipeline">
          {stageOptions.map((stage) => {
            const stageDeals = deals.data.filter((deal) => deal.stage === stage.value);
            return (
              <section className="deal-column" key={stage.value} aria-label={`${stage.label} deals`}>
                <header><h3>{stage.label}</h3><span>{stageDeals.length}</span></header>
                {stageDeals.map((deal) => <DealCard deal={deal} key={deal.id} />)}
                {stageDeals.length === 0 && <div className="empty-state">No deals</div>}
              </section>
            );
          })}
        </section>
      ) : visibleDeals.length === 0 ? (
        <div className="empty-state">No deals match these filters.</div>
      ) : (
        <section className="deal-list" aria-label="Deal list">
          {visibleDeals.map((deal) => <DealCard deal={deal} layout="list" key={deal.id} />)}
        </section>
      )}
    </section>
  );
}
