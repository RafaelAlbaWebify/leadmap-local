import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BusinessDealCreate, DealsWorkspace } from "./DealsWorkspace";

function renderWithClient(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Number.POSITIVE_INFINITY },
      mutations: { retry: false }
    }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("deal workflow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => cleanup());

  it("creates a deal explicitly for a qualified business and clears the form", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        id: "deal-1",
        business_id: "business-1",
        business_name: "Kildare Accountancy",
        title: "Website redesign",
        stage: "proposal",
        value_eur_cents: 350000,
        next_action: "Send proposal",
        created_at: "2026-07-25T14:00:00Z",
        updated_at: "2026-07-25T14:00:00Z"
      }), { status: 201, headers: { "Content-Type": "application/json" } })
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

  it("groups persisted deals by stage", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([
        {
          id: "deal-1",
          business_id: "business-1",
          business_name: "Kildare Accountancy",
          title: "Website redesign",
          stage: "proposal",
          value_eur_cents: 350000,
          next_action: "Send proposal",
          created_at: "2026-07-25T14:00:00Z",
          updated_at: "2026-07-25T14:00:00Z"
        }
      ]), { status: 200, headers: { "Content-Type": "application/json" } })
    );
    renderWithClient(<DealsWorkspace />);

    const proposal = await screen.findByRole("region", { name: "Proposal deals" });
    expect(within(proposal).getByText("Website redesign")).toBeInTheDocument();
    expect(within(proposal).getByText("Kildare Accountancy")).toBeInTheDocument();
    expect(within(proposal).getByText("3500,00 €")).toBeInTheDocument();
    expect(within(proposal).getByText("Send proposal")).toBeInTheDocument();
  });
});
