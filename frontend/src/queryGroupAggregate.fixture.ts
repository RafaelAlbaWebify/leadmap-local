import type { AssistedSessionReview } from "./types";

export function completedQueryReview(
  review: AssistedSessionReview
): AssistedSessionReview {
  if (!review.traversal_progress?.query_sequence || !review.traversal_progress.query_text.trim()) {
    throw new Error("Completed query reviews require query sequence and query text.");
  }
  return review;
}
