import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { saveAggregateBusinesses } from "./api";
import { QueryGroupReview } from "./QueryGroupReview";
import type { AssistedSessionReview, VisibleCandidate } from "./types";

vi.mock("./api", () => ({
  saveAggregateBusinesses: vi.fn()
}));

const mockedSave = vi.mocked(saveAggregateBusinesses);

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

function renderReview(reviews: AssistedSessionReview[]) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <QueryGroupReview reviews={reviews} />
    </QueryClientProvider>
  );
}

const completedReviews = [
  review("accountant in Kildare County, IE", 1, 2),
  review("tax advisor in Kildare County, IE", 2, 5)
];

describe("QueryGroupReview", () => {
  beforeEach(() => {
    mockedSave.mockReset();
  });

  it("shows one business with all retained query and rank appearances", () => {
    renderReview(completedReviews);

    expect(screen.getByRole("region", { name: "Aggregate business review" })).toBeInTheDocument();
    const completedMetric = screen.getByText("queries completed").closest("article");
    expect(completedMetric).not.toBeNull();
    expect(within(completedMetric!).getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Kildare Accountancy")).toBeInTheDocument();
    expect(screen.getByText("accountant in Kildare County, IE")).toBeInTheDocument();
    expect(screen.getByText("tax advisor in Kildare County, IE")).toBeInTheDocument();
    expect(screen.getByText("rank 2")).toBeInTheDocument();
    expect(screen.getByText("rank 5")).toBeInTheDocument();
  });

  it("saves included businesses explicitly and shows the persisted result", async () => {
    mockedSave.mockResolvedValue({
      businesses_created: 1,
      businesses_matched: 0,
      observations_created: 2,
      observations_skipped: 0,
      businesses_skipped: 0
    });
    renderReview(completedReviews);

    fireEvent.click(screen.getByRole("button", { name: "Save included businesses" }));

    await waitFor(() => expect(mockedSave).toHaveBeenCalledTimes(1));
    expect(mockedSave.mock.calls[0][0]).toMatchObject({
      batch_id: "query-group:session-1:session-2",
      territory_id: "territory-kildare",
      query_template_id: "template-accountancy"
    });
    expect(screen.getByRole("status", { name: "Aggregate save result" })).toHaveTextContent(
      "1 created · 0 matched · 2 observations added · 0 already saved"
    );
  });

  it("retains the aggregate review after a failed save", async () => {
    mockedSave.mockRejectedValue(new Error("backend unavailable"));
    renderReview(completedReviews);

    fireEvent.click(screen.getByRole("button", { name: "Save included businesses" }));

    expect(await screen.findByLabelText("Aggregate save error")).toBeInTheDocument();
    expect(screen.getByText("Kildare Accountancy")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save included businesses" })).toBeEnabled();
  });

  it("renders nothing before two queries have completed", () => {
    const queryClient = new QueryClient();
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <QueryGroupReview reviews={[]} />
      </QueryClientProvider>
    );
    expect(container).toBeEmptyDOMElement();
  });
});
