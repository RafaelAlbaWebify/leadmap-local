import { useMemo, useState } from "react";

import type { Lead } from "./types";

const shortlistStatuses = new Set([
  "qualified",
  "shortlisted",
  "sent_to_veridra",
  "veridra_reviewed",
  "approved_for_outreach",
  "contacted",
  "responded",
  "conversation",
  "proposal",
  "customer"
]);

function csvCell(value: string | null): string {
  const safe = value ?? "";
  return `"${safe.replaceAll('"', '""')}"`;
}

function downloadText(filename: string, mimeType: string, content: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function hasWebsite(lead: Lead): boolean {
  return Boolean(lead.website?.trim());
}

function evidenceSummary(lead: Lead): string {
  const website = lead.website ? `Website captured: ${lead.website}.` : "No website captured.";
  return `${website} Category: ${lead.category}. Area: ${lead.locality}${lead.postal_area ? `, ${lead.postal_area}` : ""}. Last observed: ${lead.last_observed_at}. Current status: ${lead.qualification_status.replaceAll("_", " ")}.`;
}

function qualificationReason(lead: Lead): string {
  if (!hasWebsite(lead)) return "Not ready for Veridra because no website/domain is captured.";
  if (lead.qualification_status === "qualified") return "Qualified business with a captured website/domain; ready for human shortlist review.";
  if (lead.qualification_status === "shortlisted") return "Human-shortlisted Webify prospect with a captured website/domain.";
  if (lead.qualification_status === "sent_to_veridra") return "Already selected for Veridra assessment.";
  return `Commercial state is ${lead.qualification_status.replaceAll("_", " ")}; review before outreach.`;
}

function exportRows(leads: Lead[]) {
  return leads.map((lead) => ({
    business_name: lead.name,
    website_domain: lead.website ?? "",
    sector_category: lead.category,
    territory_location: [lead.locality, lead.postal_area].filter(Boolean).join(" · "),
    commercial_status: lead.qualification_status,
    qualification_reason: qualificationReason(lead),
    evidence_summary: evidenceSummary(lead),
    last_observed_at: lead.last_observed_at
  }));
}

export function WebifyShortlistWorkspace({ leads }: { leads: Lead[] }) {
  const eligible = useMemo(
    () => leads.filter((lead) => shortlistStatuses.has(lead.qualification_status) && hasWebsite(lead)),
    [leads]
  );
  const blocked = useMemo(
    () => leads.filter((lead) => shortlistStatuses.has(lead.qualification_status) && !hasWebsite(lead)),
    [leads]
  );
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const selected = eligible.filter((lead) => selectedIds.has(lead.id));

  function toggle(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll() {
    setSelectedIds(new Set(eligible.map((lead) => lead.id)));
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  function exportJson() {
    const payload = {
      export_type: "webify_veridra_handoff",
      generated_at: new Date().toISOString(),
      selected_count: selected.length,
      prospects: exportRows(selected)
    };
    downloadText("webify-veridra-handoff.json", "application/json", JSON.stringify(payload, null, 2));
  }

  function exportCsv() {
    const rows = exportRows(selected);
    const headers = [
      "business_name",
      "website_domain",
      "sector_category",
      "territory_location",
      "commercial_status",
      "qualification_reason",
      "evidence_summary",
      "last_observed_at"
    ];
    const csv = [
      headers.join(","),
      ...rows.map((row) => headers.map((header) => csvCell(row[header as keyof typeof row])).join(","))
    ].join("\n");
    downloadText("webify-veridra-handoff.csv", "text/csv", csv);
  }

  return (
    <section className="panel page-panel" aria-labelledby="webify-shortlist-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">WEBIFY COMMERCIAL SYSTEM</p>
          <h2 id="webify-shortlist-heading">Shortlist & Veridra handoff</h2>
          <p>Select real SMB prospects with captured websites/domains and export a human-reviewable handoff for Veridra.</p>
        </div>
      </div>

      <section className="metrics compact-metrics" aria-label="Commercial shortlist metrics">
        <article className="metric-card"><div className="metric-label">DISCOVERED</div><div className="metric-value">{leads.length}</div><div className="metric-hint">persisted businesses</div></article>
        <article className="metric-card"><div className="metric-label">WEBSITES</div><div className="metric-value">{leads.filter(hasWebsite).length}</div><div className="metric-hint">captured domains</div></article>
        <article className="metric-card"><div className="metric-label">ELIGIBLE</div><div className="metric-value">{eligible.length}</div><div className="metric-hint">shortlist-ready</div></article>
        <article className="metric-card"><div className="metric-label">SELECTED</div><div className="metric-value">{selected.length}</div><div className="metric-hint">for handoff export</div></article>
      </section>

      <div className="business-view-actions">
        <button className="secondary-action compact" disabled={eligible.length === 0} onClick={selectAll}>Select all eligible</button>
        <button className="secondary-action compact" disabled={selected.length === 0} onClick={clearSelection}>Clear selection</button>
        <button className="primary-action compact" disabled={selected.length === 0} onClick={exportJson}>Export JSON for Veridra</button>
        <button className="secondary-action compact" disabled={selected.length === 0} onClick={exportCsv}>Export CSV</button>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr><th>Select</th><th>Business</th><th>Website/domain</th><th>Sector</th><th>Territory</th><th>Status</th><th>Why it may matter</th></tr>
          </thead>
          <tbody>
            {eligible.map((lead) => (
              <tr key={lead.id}>
                <td><input aria-label={`Select ${lead.name}`} type="checkbox" checked={selectedIds.has(lead.id)} onChange={() => toggle(lead.id)} /></td>
                <td><strong>{lead.name}</strong><small>Observed {new Date(lead.last_observed_at).toLocaleDateString()}</small></td>
                <td>{lead.website ? <a href={lead.website} target="_blank" rel="noreferrer">{lead.website}</a> : "No website"}</td>
                <td>{lead.category}</td>
                <td>{lead.locality}{lead.postal_area ? ` · ${lead.postal_area}` : ""}</td>
                <td><span className="badge neutral">{lead.qualification_status.replaceAll("_", " ")}</span></td>
                <td>{qualificationReason(lead)}</td>
              </tr>
            ))}
            {eligible.length === 0 && <tr><td colSpan={7} className="empty-state">No eligible Webify prospects yet. Mark businesses as qualified or shortlisted after reviewing their evidence, and make sure they have captured websites/domains.</td></tr>}
          </tbody>
        </table>
      </div>

      {blocked.length > 0 && (
        <section className="notice" aria-label="Blocked Veridra handoff prospects">
          <strong>{blocked.length} commercial-status businesses are blocked from Veridra handoff.</strong>
          <p>They are qualified/shortlisted but have no captured website/domain. Revisit discovery evidence before exporting them.</p>
        </section>
      )}
    </section>
  );
}
