import type { AssistedSessionReview } from "./types";

interface CandidateReviewProps {
  review: AssistedSessionReview;
  busyCandidateId: string | null;
  onToggle: (candidateId: string, included: boolean) => void;
}

export function CandidateReview({ review, busyCandidateId, onToggle }: CandidateReviewProps) {
  return (
    <section className="candidate-review" aria-label="Candidate review queue">
      <div className="panel-heading">
        <div>
          <h3>Candidate review</h3>
          <p>
            {review.included_count} included · {review.excluded_count} excluded · no records saved yet
          </p>
        </div>
      </div>
      {review.candidates.length === 0 && (
        <div className="empty-state">No visible candidate cards were captured.</div>
      )}
      <div className="card-grid">
        {review.candidates.map((candidate) => (
          <article className="record-card" key={candidate.candidate_id}>
            <div className="candidate-card-heading">
              <div>
                <span className="badge neutral">{candidate.category ?? "Unclassified"}</span>
                <h3>{candidate.displayed_name}</h3>
              </div>
              <label className="candidate-toggle">
                <input
                  type="checkbox"
                  checked={candidate.included}
                  disabled={busyCandidateId === candidate.candidate_id}
                  onChange={(event) => onToggle(candidate.candidate_id, event.target.checked)}
                />
                Include
              </label>
            </div>
            <p>{candidate.address_text ?? "No address captured"}</p>
            <small>{candidate.phone ?? "No phone captured"}</small>
            {candidate.website && (
              <a href={candidate.website} target="_blank" rel="noreferrer">
                Website
              </a>
            )}
            {candidate.source_url && (
              <a href={candidate.source_url} target="_blank" rel="noreferrer">
                Source evidence
              </a>
            )}
          </article>
        ))}
      </div>
      <div className="notice">
        Review decisions remain temporary. Saving approved candidates is intentionally disabled until the persistence slice is implemented.
      </div>
    </section>
  );
}
