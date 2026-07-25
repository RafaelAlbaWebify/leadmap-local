import { useMutation, useQueryClient } from "@tanstack/react-query";

import { saveAggregateBusinesses } from "./api";
import { aggregateQueryReviews, buildAggregateSavePayload } from "./queryGroupAggregate";
import type { AssistedSessionReview } from "./types";
import "./queryGroupAggregate.css";

function batchIdForReviews(reviews: AssistedSessionReview[]): string {
  const sessionIds = reviews.map((review) => review.session_id).filter(Boolean);
  if (sessionIds.length !== reviews.length) {
    throw new Error("Every completed query review requires a session ID before saving.");
  }
  return `query-group:${sessionIds.join(":")}`;
}

export function QueryGroupReview({ reviews }: { reviews: AssistedSessionReview[] }) {
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: () => {
      const firstReview = reviews[0];
      if (!firstReview.territory_id || !firstReview.query_template_id) {
        throw new Error("Completed reviews require territory and query-template identity.");
      }
      return saveAggregateBusinesses(
        buildAggregateSavePayload(
          reviews,
          batchIdForReviews(reviews),
          firstReview.territory_id,
          firstReview.query_template_id
        )
      );
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["leads"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      ]);
    }
  });

  if (reviews.length < 2) {
    return null;
  }

  const aggregate = aggregateQueryReviews(reviews);

  return (
    <section className="aggregate-review" aria-label="Aggregate business review">
      <div className="panel-heading">
        <div>
          <h3>Aggregate business review</h3>
          <p>Repeated businesses are shown once while every query and rank appearance remains visible.</p>
        </div>
      </div>

      <div className="aggregate-summary" aria-label="Aggregate review summary">
        <article><strong>{aggregate.queryRuns.length}</strong><small>queries completed</small></article>
        <article><strong>{aggregate.totalObservations}</strong><small>observations</small></article>
        <article><strong>{aggregate.uniqueBusinesses}</strong><small>unique businesses</small></article>
        <article><strong>{aggregate.duplicateAppearances}</strong><small>duplicate appearances</small></article>
        <article><strong>{aggregate.includedBusinesses}</strong><small>included businesses</small></article>
      </div>

      <div className="aggregate-business-list">
        {aggregate.businesses.map((business) => (
          <article className="aggregate-business" key={business.identityKey}>
            <header>
              <div>
                <h4>{business.representative.displayed_name}</h4>
                <p>
                  {business.representative.category ?? "Uncategorised"}
                  {business.representative.address_text
                    ? ` · ${business.representative.address_text}`
                    : ""}
                </p>
              </div>
              <span className={`badge ${business.included ? "fresh" : "neutral"}`}>
                {business.included ? "included" : "excluded"}
              </span>
            </header>

            <ul className="aggregate-appearances" aria-label={`${business.representative.displayed_name} appearances`}>
              {business.appearances.map((appearance) => (
                <li key={`${appearance.querySequence}-${appearance.resultRank}-${appearance.candidateId}`}>
                  <strong>Q{appearance.querySequence}</strong>
                  <span>{appearance.queryText}</span>
                  <span>rank {appearance.resultRank}</span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>

      <div className="aggregate-save" aria-label="Aggregate save controls">
        <div>
          <strong>Save approved businesses</strong>
          <p>Only included businesses will be persisted. Repeating this save is idempotent.</p>
        </div>
        <button
          className="primary-action"
          disabled={save.isPending || aggregate.includedBusinesses === 0}
          onClick={() => save.mutate()}
        >
          {save.isPending ? "Saving included businesses…" : "Save included businesses"}
        </button>
      </div>

      {save.data && (
        <div className="notice traversal-summary" aria-label="Aggregate save result">
          <strong>Included businesses saved</strong>
          <p>
            {save.data.businesses_created} created · {save.data.businesses_matched} matched · {save.data.observations_created} observations added · {save.data.observations_skipped} already saved
          </p>
        </div>
      )}
      {save.isError && (
        <div className="notice error" aria-label="Aggregate save error">
          Saving failed. The aggregate review is still available; correct the issue and retry.
        </div>
      )}
    </section>
  );
}
