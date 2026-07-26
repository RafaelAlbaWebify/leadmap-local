import { useState } from "react";
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

  return (
    <>
      {qualificationStatus !== "qualified" ? (
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
              <input
                value={title}
                maxLength={300}
                onChange={(event) => setTitle(event.target.value)}
              />
            </label>
            <label>
              Stage
              <select
                value={stage}
                onChange={(event) => setStage(event.target.value as DealStage)}
              >
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
              <input
                value={nextAction}
                maxLength={1000}
                onChange={(event) => setNextAction(event.target.value)}
              />
            </label>
          </div>
          <button
            className="primary-action compact"
            disabled={!canSubmit || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Creating…" : "Create deal"}
          </button>
          {mutation.isSuccess && (
            <div className="notice success" role="status">Deal created.</div>
          )}
          {mutation.isError && (
            <div className="notice error" role="alert">
              Deal could not be created. Your entered values are retained.
            </div>
          )}
        </section>
      )}
      <TaskCreate businessId={businessId} label="Create business task" />
    </>
  );
}

function DealCard({ deal }: { deal: Deal }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [stage, setStage] = useState<DealStage>(deal.stage);
  const [nextAction, setNextAction] = useState(deal.next_action ?? "");
  const mutation = useMutation({
    mutationFn: () => updateDeal(deal.id, {
      stage,
      next_action: nextAction.trim() || null
    }),
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
    <article className="deal-card">
      <strong>{deal.title}</strong>
      <p>{deal.business_name}</p>
      <span>{formatMoney(deal.value_eur_cents)}</span>
      {!editing && <small>{deal.next_action ?? "No next action"}</small>}
      {!editing && (
        <button className="secondary-action compact" onClick={() => setEditing(true)}>
          Edit deal
        </button>
      )}
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
            <button
              className="secondary-action compact"
              disabled={mutation.isPending}
              onClick={cancelEditing}
            >
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

export function DealsWorkspace() {
  const deals = useQuery({ queryKey: ["deals"], queryFn: fetchDeals });

  if (deals.isPending) {
    return <div className="notice">Loading deals…</div>;
  }
  if (deals.isError) {
    return <div className="notice error">Deals could not be loaded.</div>;
  }

  return (
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
  );
}
