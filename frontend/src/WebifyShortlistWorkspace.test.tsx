import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { WebifyShortlistWorkspace } from "./WebifyShortlistWorkspace";
import type { Lead } from "./types";

const leads: Lead[] = [
  {
    id: "one",
    name: "Alpha Dental",
    category: "Dentist",
    locality: "Galway",
    postal_area: "H91",
    website: "https://alpha.example",
    phone: null,
    first_observed_at: "2026-08-07T09:00:00Z",
    last_observed_at: "2026-08-07T09:30:00Z",
    freshness: "fresh",
    qualification_status: "shortlisted"
  },
  {
    id: "two",
    name: "Beta Cafe",
    category: "Cafe",
    locality: "Galway",
    postal_area: null,
    website: null,
    phone: null,
    first_observed_at: "2026-08-07T09:00:00Z",
    last_observed_at: "2026-08-07T09:30:00Z",
    freshness: "fresh",
    qualification_status: "qualified"
  },
  {
    id: "three",
    name: "Gamma Shop",
    category: "Retail",
    locality: "Galway",
    postal_area: null,
    website: "https://gamma.example",
    phone: null,
    first_observed_at: "2026-08-07T09:00:00Z",
    last_observed_at: "2026-08-07T09:30:00Z",
    freshness: "fresh",
    qualification_status: "needs_review"
  }
];

describe("WebifyShortlistWorkspace", () => {
  it("shows only commercial-status businesses with websites as eligible", () => {
    render(<WebifyShortlistWorkspace leads={leads} />);

    expect(screen.getByText("Alpha Dental")).toBeInTheDocument();
    expect(screen.queryByText("Gamma Shop")).not.toBeInTheDocument();
    expect(screen.getByText(/1 commercial-status businesses are blocked/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export JSON for Veridra" })).toBeDisabled();
  });

  it("enables handoff export after selecting an eligible prospect", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:handoff");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    render(<WebifyShortlistWorkspace leads={leads} />);

    await user.click(screen.getByLabelText("Select Alpha Dental"));
    await user.click(screen.getByRole("button", { name: "Export JSON for Veridra" }));

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:handoff");
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
    click.mockRestore();
  });
});
