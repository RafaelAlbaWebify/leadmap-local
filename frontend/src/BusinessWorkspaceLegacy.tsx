import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createBusinessNote,
  fetchBusinessDetail,
  fetchBusinessNotes,
  updateBusinessQualification
} from "./api";
import { BusinessDealCreate } from "./DealsWorkspace";
import { TaskCreate } from "./TasksWorkspace";
import type { BusinessDetail, BusinessNote, Lead, QualificationStatus } from "./types";
import { qualificationOptions } from "./qualificationOptions";
import "./businessWorkspace.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function BusinessNotes({ businessId }: { businessId: string }) {
  const queryClient = useQueryClient();
  const [content, setContent] = useState("");
  const notes = useQuery({
    queryKey: ["business-notes", businessId],
    queryFn: () => fetchBusinessNotes(businessId)
  });
  const createNote = useMutation({
    mutationFn: () => createBusinessNote(businessId, content),
    onSuccess: async (created) => {
      queryClient.setQueryData<BusinessNote[]>(["business-notes", businessId], (current) => [
        created,
        ...(current ?? [])
      ]);
      setContent("");
      await queryClient.invalidateQueries({ queryKey: ["business-notes", businessId] });
    }
  });
  const canSubmit = content.trim().length > 0 && content.trim().length <= 4000;

  return (
    <section className="business-notes" aria-label="Business notes">
      <div className="panel-heading">
        <div>
          <h3>Business notes</h3>
          <p>Manual context for qualification and follow-up. Discovery evidence remains separate below.</p>
        </div>
      </div>
      <div className="business-note-editor">
        <label htmlFor="business-note-content">Add a note</label>
        <textarea
          id="business-note-content"
          value={content}
          maxLength={4000}
          disabled={createNote.isPending}
          placeholder="Record why this business was qualified, deferred, rejected or archived."
          onChange={(event) => setContent(event.target.value)}
        />
        <span>{content.length} / 4000 characters</span>
      </div>
      <button
        className="primary-action compact"
        disabled={createNote.isPending || !canSubmit}
        onClick={() => createNote.mutate()}
      >
        {createNote.isPending ? "Adding…" : "Add note"}
      </button>
      {createNote.isSuccess && <div className="notice success" role="status">Note added.</div>}
      {createNote.isError && (
        <div className="notice error" role="alert">Business notes could not be saved.</div>
      )}
      <div className="business-note-list">
        {notes.data?.map((note) => (
          <article className="business-note" key={note.id}>
            <p>{note.content}</p>
            <small>{formatDate(note.created_at)}</small>
          </article>
        ))}
        {notes.data?.length === 0 && <div className="empty-state">No notes yet.</div>}
      </div>
    </section>
  );
}

function BusinessDetailPanel({ detail }: { detail: BusinessDetail }) {
  const queryClient = useQueryClient();
  const [selectedStatus, setSelectedStatus] = useState<QualificationStatus>(detail.qualification_status);
  useEffect(() => setSelectedStatus(detail.qualification_status), [detail.qualification_status]);

  const qualification = useMutation({
    mutationFn: () => updateBusinessQualification(detail.id, selectedStatus),
    onSuccess: async (result) => {
      queryClient.setQueryData<BusinessDetail>(["business-detail", detail.id], (current) =>
        current
          ? {
              ...current,
              qualification_status: result.qualification_status,
              updated_at: result.updated_at
            }
          : current
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["business-detail", detail.id] }),
        queryClient.invalidateQueries({ queryKey: ["leads"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      ]);
    }
  });

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

      <div className="business-qualification" aria-label="Business qualification">
        <div>
          <h4>Qualification</h4>
          <p>Change this only after reviewing the persisted evidence below.</p>
        </div>
        <label>
          Status
          <select
            value={selectedStatus}
            disabled={qualification.isPending}
            onChange={(event) => setSelectedStatus(event.target.value as QualificationStatus)}
          >
            {qualificationOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <button
          className="primary-action compact"
          disabled={qualification.isPending || selectedStatus === detail.qualification_status}
          onClick={() => qualification.mutate()}
        >
          {qualification.isPending ? "Saving…" : "Save qualification"}
        </button>
        {qualification.isSuccess && (
          <div className="notice success" role="status">Qualification saved as {selectedStatus.replace("_", " ")}.</div>
        )}
        {qualification.isError && (
          <div className="notice error" role="alert">Qualification could not be saved. Your selection is retained.</div>
        )}
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

      <TaskCreate
        businessId={detail.id}
        label={`Create task for ${detail.canonical_name}`}
      />

      <BusinessDealCreate
        businessId={detail.id}
        qualificationStatus={detail.qualification_status}
      />

      <BusinessNotes businessId={detail.id} />

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
              <span className="badge neutral">{observation.provider.replaceAll("_", " ")}</span>
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
