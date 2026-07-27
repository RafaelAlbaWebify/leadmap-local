import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BusinessDealCreate, DealsWorkspace } from "./DealsWorkspace";

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Number.POSITIVE_INFINITY },
      mutations: { retry: false }
    }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const proposalDeal = {
  id: "deal-1",
  business_id: "business-1",
  business_name: "Kildare Accountancy",
  title: "Website redesign",
  stage: "proposal",
  value_eur_cents: 350000,
  next_action: "Send proposal",
  created_at: "2026-07-25T14:00:00Z",
  updated_at: "2026-07-25T14:00:00Z"
};

const leadDeal = {
  id: "deal-2",
  business_id: "business-2",
  business_name: "Alpha Legal",
  title: "Support retainer",
  stage: "lead",
  value_eur_cents: 800000,
  next_action: "Book discovery call",
  created_at: "2026-07-24T14:00:00Z",
  updated_at: "2026-07-24T14:00:00Z"
};

describe("deal workflow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => cleanup());

  it("creates a deal explicitly for a qualified business and clears the form", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(proposalDeal), {
        status: 201,
        headers: { "Content-Type": "application/json" }
      })
    );
    renderWithClient(
      <BusinessDealCreate businessId="business-1" qualificationStatus="qualified" />
    );

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Website redesign" } });
    fireEvent.change(screen.getByLabelText("Stage"), { target: { value: "proposal" } });
    fireEvent.change(screen.getByLabelText("Value (€)"), { target: { value: "3500" } });
    fireEvent.change(screen.getByLabelText("Next action"), { target: { value: "Send proposal" } });
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(String(init?.body))).toEqual({
      title: "Website redesign",
      stage: "proposal",
      value_eur_cents: 350000,
      next_action: "Send proposal"
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Deal created.");
    expect(screen.getByLabelText("Title")).toHaveValue("");
  });

  it("retains entered deal values after a failed create", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("failed", { status: 500 }));
    renderWithClient(
      <BusinessDealCreate businessId="business-1" qualificationStatus="qualified" />
    );

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Retained title" } });
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Deal could not be created. Your entered values are retained."
    );
    expect(screen.getByLabelText("Title")).toHaveValue("Retained title");
  });

  it("shows a locked create panel for non-qualified businesses", () => {
    renderWithClient(
      <BusinessDealCreate businessId="business-1" qualificationStatus="needs_review" />
    );

    expect(screen.getByText("Qualify this business before creating a commercial opportunity."))
      .toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create deal" })).not.toBeInTheDocument();
  });

  it("moves an explicitly updated deal to its new stage", async () => {
    const updated = {
      ...proposalDeal,
      stage: "won",
      next_action: "Schedule kickoff",
      updated_at: "2026-07-25T15:00:00Z"
    };
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([proposalDeal]), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify(updated), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }))
      .mockResolvedValue(new Response(JSON.stringify([updated]), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }));
    renderWithClient(<DealsWorkspace />);

    const proposal = await screen.findByRole("region", { name: "Proposal deals" });
    fireEvent.click(within(proposal).getByRole("button", { name: "Edit deal" }));
    const editor = within(proposal).getByLabelText("Edit Website redesign");
    fireEvent.change(within(editor).getByLabelText("Stage"), { target: { value: "won" } });
    fireEvent.change(within(editor).getByLabelText("Next action"), {
      target: { value: "Schedule kickoff" }
    });
    fireEvent.click(within(editor).getByRole("button", { name: "Save deal" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const [, init] = fetchMock.mock.calls[1];
    expect(JSON.parse(String(init?.body))).toEqual({
      stage: "won",
      next_action: "Schedule kickoff"
    });
    const won = await screen.findByRole("region", { name: "Won deals" });
    expect(within(won).getByText("Website redesign", { exact: true })).toBeInTheDocument();
    expect(within(won).getByText("Schedule kickoff")).toBeInTheDocument();
    expect(within(proposal).queryByText("Website redesign", { exact: true })).not.toBeInTheDocument();
  });

  it("retains deal edits after a failed update", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([proposalDeal]), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }))
      .mockResolvedValueOnce(new Response("failed", { status: 500 }));
    renderWithClient(<DealsWorkspace />);

    const proposal = await screen.findByRole("region", { name: "Proposal deals" });
    fireEvent.click(within(proposal).getByRole("button", { name: "Edit deal" }));
    const editor = within(proposal).getByLabelText("Edit Website redesign");
    fireEvent.change(within(editor).getByLabelText("Stage"), { target: { value: "won" } });
    fireEvent.change(within(editor).getByLabelText("Next action"), {
      target: { value: "Retained next action" }
    });
    fireEvent.click(within(editor).getByRole("button", { name: "Save deal" }));

    expect(await within(editor).findByRole("alert")).toHaveTextContent(
      "Deal could not be updated. Your entered values are retained."
    );
    expect(within(editor).getByLabelText("Stage")).toHaveValue("won");
    expect(within(editor).getByLabelText("Next action")).toHaveValue("Retained next action");
  });

  it("groups persisted deals by stage", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([proposalDeal]), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    renderWithClient(<DealsWorkspace />);

    const proposal = await screen.findByRole("region", { name: "Proposal deals" });
    expect(within(proposal).getByText("Website redesign", { exact: true })).toBeInTheDocument();
    expect(within(proposal).getByText("Kildare Accountancy")).toBeInTheDocument();
    expect(within(proposal).getByText("3500,00 €")).toBeInTheDocument();
    expect(within(proposal).getByText("Send proposal")).toBeInTheDocument();
  });

  it("switches to list view and filters persisted deals", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([proposalDeal, leadDeal]), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    renderWithClient(<DealsWorkspace />);

    fireEvent.click(await screen.findByRole("button", { name: "List" }));
    const list = screen.getByRole("region", { name: "Deal list" });
    expect(within(list).getByText("Website redesign", { exact: true })).toBeInTheDocument();
    expect(within(list).getByText("Support retainer", { exact: true })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search deals"), { target: { value: "alpha" } });
    expect(within(list).queryByText("Website redesign", { exact: true })).not.toBeInTheDocument();
    expect(within(list).getByText("Support retainer", { exact: true })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search deals"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Stage"), { target: { value: "proposal" } });
    expect(within(list).getByText("Website redesign", { exact: true })).toBeInTheDocument();
    expect(within(list).queryByText("Support retainer", { exact: true })).not.toBeInTheDocument();
  });

  it("sorts list deals by highest value", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([proposalDeal, leadDeal]), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    renderWithClient(<DealsWorkspace />);

    fireEvent.click(await screen.findByRole("button", { name: "List" }));
    fireEvent.change(screen.getByLabelText("Sort by"), { target: { value: "value_desc" } });

    const cards = within(screen.getByRole("region", { name: "Deal list" })).getAllByRole("article");
    expect(within(cards[0]).getByText("Support retainer", { exact: true })).toBeInTheDocument();
    expect(within(cards[1]).getByText("Website redesign", { exact: true })).toBeInTheDocument();
  });
});
