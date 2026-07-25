import { describe, expect, it } from "vitest";

import { completedQueryReview } from "./queryGroupAggregate.fixture";
import type { AssistedSessionReview } from "./types";

const baseReview: AssistedSessionReview = {
  session_id: "session-1",
  state: "review",
  territory_id: "territory-kildare",
  query_template_id: "template-accountancy",
  start_url: null,
  error: null,
  traversal_progress: {
    query_text: "accountant in Kildare County, IE",
    query_sequence: 1,
    scroll_step: 1,
    unique_cards: 0,
    stagnant_scrolls: 0,
    elapsed_seconds: 1,
    stop_reason: "end_of_list"
  },
  traversal_stop_reason: "end_of_list",
  candidates: [],
  included_count: 0,
  excluded_count: 0
};

describe("completedQueryReview", () => {
  it("accepts a completed review with canonical provenance", () => {
    expect(completedQueryReview(baseReview)).toBe(baseReview);
  });

  it("rejects a review without query provenance", () => {
    expect(() => completedQueryReview({ ...baseReview, traversal_progress: null })).toThrow(
      "Completed query reviews require query sequence and query text."
    );
  });
});
