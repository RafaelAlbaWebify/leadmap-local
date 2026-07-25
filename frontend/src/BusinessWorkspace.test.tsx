import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createBusinessNote,
  fetchBusinessDetail,
  fetchBusinessNotes,
  updateBusinessQualification
} from "./api";
import { BusinessWorkspace } from "./BusinessWorkspace";
import type { BusinessDetail, Lead } from "./types";

vi.mock("./api", () => ({
  createBusinessNote: vi.fn(),
  fetchBusinessDetail: vi.fn(),
  fetchBusinessNotes: vi.fn(),
  updateBusinessQualification: vi.fn()
}));

const mockedCreateNote = vi.mocked(createBusinessNote);
const mockedFetchDetail = vi.mocked(fetchBusinessDetail);
const mockedFetchNotes = vi.mocked(fetchBusinessNotes);
const mockedUpdateQualification = vi.mocked(updateBusinessQualification);

const leads: Lead[] = [
  {
    id: "business-1",
    name: "Kildare Accountancy",
    category: "Accountant",
    locality: "Kildare County",
    postal_area: null,
    website: "https://kildare-accountancy.example",
    phone: "+353 45 000 000",
    first_observed_at: "2026-07-23T12:00:00Z",
    last_observed_at: "2026-07-25T12:00:00Z",
    freshness: "fresh",
    qualification_status: "needs_review"
  }
];

const detail: BusinessDetail = {
  id: "business-1",
  canonical_name: "Kildare Accountancy",
  normalized_name: "kildare accountancy",
  qualification_status: "needs_review",
  freshness: "fresh",
  created_at: "2026-07-23T12:00:00Z",
  updated_at: "2026-07-25T12:00:00Z",
  locations: [
    {
      id: "location-1",
      locality: "Kildare County",
      administrative_area: "County Kildare",
      country_code: "IE",
      postal_area: null,
      phone: "+353 45 000 000",
      website: "https://kildare-accountancy.example",
      latitude: "53.16",
      longitude: "-6.91",
      created_at: "2026-07-23T12:00:00Z",
      updated_at: "2026-07-25T12:00:00Z"
    }
  ],
  observations: [
    {
      id: "observation-2",
      location_id: "location-1",
      provider: "google_maps",
      provider_key: "place-1",
      displayed_name: "Kildare Accountancy",
      category: "Tax consultant",
      source_url: "https://maps.example/place-1",
      observed_at: "2026-07-25T12:00:00Z",
      query_text: "tax advisor in Kildare County, IE",
      search_run_status: "completed",
      query_sequence: 2,
      result_rank: 3,
      first_seen_scroll_step: 1,
      candidate_id: "q2-place-1",
      raw_evidence: "Kildare Accountancy · Tax consultant",
      address_text: "Kildare County"
    },
    {
      id: "observation-1",
      location_id: "location-1",
      provider: "google_maps",
      provider_key: "place-1",
      displayed_name: "Kildare Accountancy",
      category: "Accountant",
      source_url: "https://maps.example/place-1",
      observed_at: "2026-07-23T12:00:00Z",
      query_text: "accountant in Kildare County, IE",
      search_run_status: "completed",
      query_sequence: 1,
      result_rank: 2,
      first_seen_scroll_step: 0,
      candidate_id: "q1-place-1",
      raw_evidence: "Kildare Accountancy · Accountant",
      address_text: "Kildare County"
    }
  ]
};

function renderWorkspace() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Number.POSITIVE_INFINITY },
      mutations: { retry: false }
    }
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BusinessWorkspace leads={leads} />
    </QueryClientProvider>
  );
}

async function openBusiness() {
  fireEvent.click(screen.getByRole("button", { name: "Open" }));
  return screen.findByRole("region", { name: "Business detail workspace" });
}

describe("BusinessWorkspace", () => {
  beforeEach(() => {
    mockedCreateNote.mockReset();
    mockedFetchDetail.mockReset();
    mockedFetchNotes.mockReset();
    mockedUpdateQualification.mockReset();
    mockedFetchNotes.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it("opens a persisted business and shows location and observation provenance", async () => {
    mockedFetchDetail.mockResolvedValue(detail);
    renderWorkspace();

    const workspace = await openBusiness();

    await waitFor(() => expect(mockedFetchDetail).toHaveBeenCalledWith("business-1"));
    expect(within(workspace).getByRole("heading", { name: "Kildare Accountancy" })).toBeInTheDocument();
    expect(within(workspace).getByText("+353 45 000 000")).toBeInTheDocument();
    expect(within(workspace).getByText("tax advisor in Kildare County, IE")).toBeInTheDocument();
    expect(within(workspace).getByText("rank 3")).toBeInTheDocument();
    expect(within(workspace).getByText("accountant in Kildare County, IE")).toBeInTheDocument();
    expect(within(workspace).getByText("rank 2")).toBeInTheDocument();
    expect(within(workspace).getAllByRole("link", { name: "Open source evidence" })).toHaveLength(2);
  });

  it("adds a note and clears the editor only after success", async () => {
    mockedFetchDetail.mockResolvedValue(detail);
    mockedFetchNotes.mockResolvedValue([
      {
        id: "note-1",
        business_id: "business-1",
        content: "Reviewed before qualification.",
        created_at: "2026-07-25T11:00:00Z"
      }
    ]);
    mockedCreateNote.mockResolvedValue({
      id: "note-2",
      business_id: "business-1",
      content: "Call next Tuesday.",
      created_at: "2026-07-25T13:00:00Z"
    });
    renderWorkspace();
    const workspace = await openBusiness();
    const editor = await within(workspace).findByLabelText("Add a note");

    fireEvent.change(editor, { target: { value: "Call next Tuesday." } });
    fireEvent.click(within(workspace).getByRole("button", { name: "Add note" }));

    await waitFor(() => expect(mockedCreateNote).toHaveBeenCalledWith("business-1", "Call next Tuesday."));
    expect(await within(workspace).findByText("Note added.")).toBeInTheDocument();
    expect(editor).toHaveValue("");
  });

  it("retains note text when creation fails", async () => {
    mockedFetchDetail.mockResolvedValue(detail);
    mockedCreateNote.mockRejectedValue(new Error("save failed"));
    renderWorkspace();
    const workspace = await openBusiness();
    const editor = await within(workspace).findByLabelText("Add a note");

    fireEvent.change(editor, { target: { value: "Keep this text" } });
    fireEvent.click(within(workspace).getByRole("button", { name: "Add note" }));

    expect(await within(workspace).findByRole("alert")).toHaveTextContent(
      "Note could not be added. Your text is retained."
    );
    expect(editor).toHaveValue("Keep this text");
  });

  it("saves an explicit qualification change", async () => {
    mockedFetchDetail.mockResolvedValue(detail);
    mockedUpdateQualification.mockResolvedValue({
      id: "business-1",
      qualification_status: "qualified",
      updated_at: "2026-07-25T13:00:00Z"
    });
    renderWorkspace();
    const workspace = await openBusiness();

    fireEvent.change(within(workspace).getByLabelText("Status"), {
      target: { value: "qualified" }
    });
    fireEvent.click(within(workspace).getByRole("button", { name: "Save qualification" }));

    await waitFor(() =>
      expect(mockedUpdateQualification).toHaveBeenCalledWith("business-1", "qualified")
    );
    expect(await within(workspace).findByRole("status")).toHaveTextContent(
      "Qualification saved as qualified."
    );
  });

  it("retains the selected status when qualification saving fails", async () => {
    mockedFetchDetail.mockResolvedValue(detail);
    mockedUpdateQualification.mockRejectedValue(new Error("save failed"));
    renderWorkspace();
    const workspace = await openBusiness();
    const statusSelect = within(workspace).getByLabelText("Status");

    fireEvent.change(statusSelect, { target: { value: "unsuitable" } });
    fireEvent.click(within(workspace).getByRole("button", { name: "Save qualification" }));

    expect(await within(workspace).findByRole("alert")).toHaveTextContent(
      "Qualification could not be saved. Your selection is retained."
    );
    expect(statusSelect).toHaveValue("unsuitable");
  });

  it("keeps the business list available when detail loading fails", async () => {
    mockedFetchDetail.mockRejectedValue(new Error("not found"));
    renderWorkspace();

    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    expect(await screen.findByText("Business detail could not be loaded.")).toBeInTheDocument();
    expect(screen.getByText("Kildare Accountancy")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open" })).toBeEnabled();
  });

  it("shows a clear empty state when no businesses exist", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BusinessWorkspace leads={[]} />
      </QueryClientProvider>
    );

    expect(screen.getByText("No persisted businesses yet.")).toBeInTheDocument();
  });
});
