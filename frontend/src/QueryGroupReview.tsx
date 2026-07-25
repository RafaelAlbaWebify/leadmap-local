import { aggregateQueryReviews } from "./queryGroupAggregate";
import type { AssistedSessionReview } from "./types";
import "./queryGroupAggregate.css";

export function QueryGroupReview({ reviews }: { reviews: AssistedSessionReview[] }) {
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
    </section>
  );
}
