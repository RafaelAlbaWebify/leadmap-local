import { describe, expect, it } from "vitest";

import { aggregateQueryReviews } from "./queryGroupAggregate";
import type { AssistedSessionReview, VisibleCandidate } from "./types";

function candidate(
  providerKey: string,
  name: string,
  queryText: string,
  querySequence: number,
  rank: number,
  included = true
): VisibleCandidate {
  return {
    candidate_id: `${querySequence}-${rank}`,
    provider_key: providerKey,
    displayed_name: name,
    normalized_name: name.toLocaleLowerCase(),
    category: "Accountant",
    address_text: "Kildare County",
    phone: null,
    website: `https://${name.toLocaleLowerCase().replaceAll(" ", "-")}.example`,
    source_url: `https://maps.example/${providerKey || `${querySequence}-${rank}`}`,
    latitude: null,
    longitude: null,
    raw_evidence: name,
    included,
    query_text: queryText,
    query_sequence: querySequence,
    result_rank: rank,
    first_seen_scroll_step: 0,
    captured_at: "2026-07-25T08:00:00Z"
  };
}

function review(
  queryText: string,
  querySequence: number,
  candidates: VisibleCandidate[]
): AssistedSessionReview {
  return {
    session_id: `session-${querySequence}`,
    state: "review",
    territory_id: "territory-kildare",
    query_template_id: "template-accountancy",
    start_url: null,
    error: null,
    traversal_progress: {
      query_text: queryText,
      query_sequence: querySequence,
      scroll_step: 4,
      unique_cards: candidates.length,
      stagnant_scrolls: 3,
      elapsed_seconds: 4.2,
      stop_reason: "no_new_results"
    },
    traversal_stop_reason: "no_new_results",
    candidates,
    included_count: candidates.filter((item) => item.included).length,
    excluded_count: candidates.filter((item) => !item.included).length
  };
}

describe("aggregateQueryReviews", () => {
  it("retains every query and rank appearance while deduplicating businesses", () => {
    const firstQuery = "accountant in Kildare County, IE";
    const secondQuery = "tax advisor in Kildare County, IE";

    const result = aggregateQueryReviews([
      review(firstQuery, 1, [candidate("place-1", "Kildare Accountancy", firstQuery, 1, 2)]),
      review(secondQuery, 2, [candidate("place-1", "Kildare Accountancy", secondQuery, 2, 5)])
    ]);

    expect(result.totalObservations).toBe(2);
    expect(result.uniqueBusinesses).toBe(1);
    expect(result.duplicateAppearances).toBe(1);
    expect(result.businesses[0].appearances).toEqual([
      expect.objectContaining({ querySequence: 1, resultRank: 2 }),
      expect.objectContaining({ querySequence: 2, resultRank: 5 })
    ]);
  });

  it("preserves deterministic first-seen order across query runs", () => {
    const firstQuery = "accountant in Kildare County, IE";
    const secondQuery = "bookkeeper in Kildare County, IE";

    const result = aggregateQueryReviews([
      review(firstQuery, 1, [
        candidate("alpha", "Alpha", firstQuery, 1, 1),
        candidate("beta", "Beta", firstQuery, 1, 2)
      ]),
      review(secondQuery, 2, [candidate("gamma", "Gamma", secondQuery, 2, 1)])
    ]);

    expect(result.businesses.map((item) => item.representative.displayed_name)).toEqual([
      "Alpha",
      "Beta",
      "Gamma"
    ]);
    expect(result.businesses.map((item) => item.firstSeenOrder)).toEqual([1, 2, 3]);
  });

  it("uses any included appearance as the default aggregate inclusion", () => {
    const firstQuery = "accountant in Kildare County, IE";
    const secondQuery = "tax advisor in Kildare County, IE";

    const result = aggregateQueryReviews([
      review(firstQuery, 1, [candidate("place-1", "Alpha", firstQuery, 1, 1, false)]),
      review(secondQuery, 2, [candidate("place-1", "Alpha", secondQuery, 2, 3, true)])
    ]);

    expect(result.includedBusinesses).toBe(1);
    expect(result.excludedBusinesses).toBe(0);
    expect(result.businesses[0].included).toBe(true);
  });

  it("rejects duplicate query sequences and incomplete provenance", () => {
    const queryText = "accountant in Kildare County, IE";
    const completed = review(queryText, 1, [candidate("place-1", "Alpha", queryText, 1, 1)]);

    expect(() => aggregateQueryReviews([completed, completed])).toThrow(
      "Query sequence 1 has already been aggregated."
    );

    const missingRank = review(queryText, 1, [
      { ...candidate("place-1", "Alpha", queryText, 1, 1), result_rank: null }
    ]);
    expect(() => aggregateQueryReviews([missingRank])).toThrow(
      "Candidate result rank must be a positive number."
    );
  });
});
