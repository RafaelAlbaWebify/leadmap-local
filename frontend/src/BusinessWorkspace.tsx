import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchBusinessDetail } from "./api";
import type { BusinessDetail, Lead } from "./types";
import "./businessWorkspace.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function BusinessDetailPanel({ detail }: { detail: BusinessDetail }) {
  return (
    <section className="business-detail" aria-label="Business detail workspace">
      <div className="business-detail-header">
        <div>
          <p className="eyebrow">PERSISTED BUSINESS</p>
          <h3>{detail.canonical_name}</h3>
          <p>{detail.normalized_name}</p>
        </div>
        <div className="business-detail-badges">
          <span className={`badge ${detail.freshness}`}>{detail.freshness.replace("_", " ")}</span>
          <span className="badge neutral">{detail.qualification_status.replace("_", " ")}</span>
        </div>
      </div>

      <div className="business-detail-grid">
        {detail.locations.map((location) => (
          <article className="business-location-card" key={location.id}>
            <h4>{location.locality}</h4>
            <p>
              {[location.administrative_area, location.postal_area, location.country_code]
                .filter(Boolean)
                .join(" · ")}
            </p>
            <dl>
              <div><dt>Phone</dt><dd>{location.phone ?? "Not captured"}</dd></div>
              <div>
                <dt>Website</dt>
                <dd>
                  {location.website ? (
                    <a href={location.website} target="_blank" rel="noreferrer">Open website</a>
                  ) : "Not captured"}
                </dd>
              </div>
              <div><dt>Coordinates</dt><dd>{location.latitude && location.longitude ? `${location.latitude}, ${location.longitude}` : "Not captured"}</dd></div>
            </dl>
          </article>
        ))}
      </div>

      <div className="business-observations">
        <div className="panel-heading">
          <div>
            <h3>Observation history</h3>
            <p>{detail.observations.length} persisted discovery observations</p>
          </div>
        </div>
        {detail.observations.length === 0 && (
          <div className="empty-state">No persisted observations are linked to this business.</div>
        )}
        {detail.observations.map((observation) => (
          <article className="business-observation" key={observation.id}>
            <header>
              <div>
                <strong>{observation.category}</strong>
                <small>{formatDate(observation.observed_at)}</small>
              </div>
              <span className="badge neutral">{observation.provider}</span>
            </header>
            <p className="business-observation-query">{observation.query_text}</p>
            <div className="business-observation-meta">
              <span>Q{observation.query_sequence ?? "?"}</span>
              <span>rank {observation.result_rank ?? "unknown"}</span>
              <span>scroll {observation.first_seen_scroll_step ?? "unknown"}</span>
              <span>{observation.search_run_status}</span>
            </div>
            {observation.raw_evidence && <p>{observation.raw_evidence}</p>}
            {observation.source_url && (
              <a href={observation.source_url} target="_blank" rel="noreferrer">Open source evidence</a>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

export function BusinessWorkspace({ leads }: { leads: Lead[] }) {
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);
  const detail = useQuery({
    queryKey: ["business-detail", selectedBusinessId],
    queryFn: () => fetchBusinessDetail(selectedBusinessId!),
    enabled: selectedBusinessId !== null
  });

  return (
    <div className="business-workspace">
      <div className="table-scroll">
        <table>
          <thead>
            <tr><th>Business</th><th>Category</th><th>Area</th><th>Observed</th><th>Freshness</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={`${lead.id}-${lead.last_observed_at}`}>
                <td><strong>{lead.name}</strong><small>{lead.website ?? "No website captured"}</small></td>
                <td>{lead.category}</td>
                <td>{lead.locality}{lead.postal_area ? ` · ${lead.postal_area}` : ""}</td>
                <td>{new Date(lead.last_observed_at).toLocaleDateString()}</td>
                <td><span className={`badge ${lead.freshness}`}>{lead.freshness.replace("_", " ")}</span></td>
                <td><span className="badge neutral">{lead.qualification_status.replace("_", " ")}</span></td>
                <td>
                  <button className="secondary-action compact" onClick={() => setSelectedBusinessId(lead.id)}>
                    Open
                  </button>
                </td>
              </tr>
            ))}
            {leads.length === 0 && <tr><td colSpan={7} className="empty-state">No persisted businesses yet.</td></tr>}
          </tbody>
        </table>
      </div>

      {selectedBusinessId === null && leads.length > 0 && (
        <div className="empty-state business-detail-placeholder">Open a persisted business to inspect its evidence history.</div>
      )}
      {detail.isPending && selectedBusinessId !== null && <div className="notice">Loading business detail…</div>}
      {detail.isError && <div className="notice error">Business detail could not be loaded.</div>}
      {detail.data && <BusinessDetailPanel detail={detail.data} />}
    </div>
  );
}
