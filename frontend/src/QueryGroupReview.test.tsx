import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { QueryGroupReview } from "./QueryGroupReview";
import type { AssistedSessionReview, VisibleCandidate } from "./types";

function candidate(
  providerKey: string,
  queryText: string,
  querySequence: number,
  resultRank: number
): VisibleCandidate {
  return {
    candidate_id: `${providerKey}-${querySequence}`,
    provider_key: providerKey,
    displayed_name: "Kildare Accountancy",
    normalized_name: "kildare accountancy",
    category: "Accountant",
    address_text: "Kildare County",
    phone: null,
    website: "https://kildare-accountancy.example",
    source_url: `https://maps.example/${providerKey}`,
    latitude: null,
    longitude: null,
    raw_evidence: "Kildare Accountancy · Accountant",
    included: true,
    query_text: queryText,
    query_sequence: querySequence,
    result_rank: resultRank,
    first_seen_scroll_step: 0,
    captured_at: "2026-07-25T08:00:00Z"
  };
}

function review(
  queryText: string,
  querySequence: number,
  resultRank: number
): AssistedSessionReview {
  const item = candidate("place-1", queryText, querySequence, resultRank);
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
      unique_cards: 1,
      stagnant_scrolls: 3,
      elapsed_seconds: 4.2,
      stop_reason: "no_new_results"
    },
    traversal_stop_reason: "no_new_results",
    candidates: [item],
    included_count: 1,
    excluded_count: 0
  };
}

describe("QueryGroupReview", () => {
  it("shows one business with all retained query and rank appearances", () => {
    render(
      <QueryGroupReview
        reviews={[
          review("accountant in Kildare County, IE", 1, 2),
          review("tax advisor in Kildare County, IE", 2, 5)
        ]}
      />
    );

    expect(screen.getByRole("region", { name: "Aggregate business review" })).toBeInTheDocument();
    expect(screen.getByText("2", { selector: ".aggregate-summary strong" })).toBeInTheDocument();
    expect(screen.getByText("Kildare Accountancy")).toBeInTheDocument();
    expect(screen.getByText("accountant in Kildare County, IE")).toBeInTheDocument();
    expect(screen.getByText("tax advisor in Kildare County, IE")).toBeInTheDocument();
    expect(screen.getByText("rank 2")).toBeInTheDocument();
    expect(screen.getByText("rank 5")).toBeInTheDocument();
  });

  it("renders nothing before a query has completed", () => {
    const { container } = render(<QueryGroupReview reviews={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
