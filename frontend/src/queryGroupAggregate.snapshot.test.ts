import { describe, expect, it } from "vitest";

import { aggregateQueryReviews } from "./queryGroupAggregate";

describe("aggregate query summaries", () => {
  it("returns an empty deterministic snapshot", () => {
    expect(aggregateQueryReviews([])).toEqual({
      businesses: [],
      queryRuns: [],
      totalObservations: 0,
      uniqueBusinesses: 0,
      duplicateAppearances: 0,
      includedBusinesses: 0,
      excludedBusinesses: 0
    });
  });
});
