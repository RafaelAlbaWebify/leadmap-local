import type {
  AggregateBatchSave,
  AggregateSaveResult,
  AssistedSession,
  AssistedSessionReview,
  BusinessDetail,
  DashboardSummary,
  DiscoveryPlan,
  GeographyArtifact,
  GeographyArtifactSummary,
  Lead,
  QueryTemplate,
  SeedResult,
  Territory,
  TerritoryBoundaryLink,
  TerritoryCoverage
} from "./types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchDashboard(): Promise<DashboardSummary> {
  return requestJson("/api/v1/dashboard");
}

export function fetchTerritories(): Promise<Territory[]> {
  return requestJson("/api/v1/territories");
}

export function fetchQueryTemplates(): Promise<QueryTemplate[]> {
  return requestJson("/api/v1/query-templates?country_code=IE");
}

export function fetchLeads(): Promise<Lead[]> {
  return requestJson("/api/v1/leads");
}

export function fetchBusinessDetail(businessId: string): Promise<BusinessDetail> {
  return requestJson(`/api/v1/businesses/${businessId}`);
}

export function fetchGeographyArtifacts(): Promise<GeographyArtifactSummary[]> {
  return requestJson("/api/v1/geography/artifacts");
}

export function fetchGeographyArtifact(checksumSha256: string): Promise<GeographyArtifact> {
  return requestJson(`/api/v1/geography/artifacts/${checksumSha256}`);
}

export function fetchTerritoryBoundaryLinks(): Promise<TerritoryBoundaryLink[]> {
  return requestJson("/api/v1/geography/territory-links");
}

export function fetchGeographyCoverage(): Promise<TerritoryCoverage[]> {
  return requestJson("/api/v1/geography/coverage");
}

export function saveTerritoryBoundaryLink(
  territoryId: string,
  checksumSha256: string,
  boundaryExternalId: string
): Promise<TerritoryBoundaryLink> {
  return requestJson(`/api/v1/geography/territory-links/${territoryId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      checksum_sha256: checksumSha256,
      boundary_external_id: boundaryExternalId
    })
  });
}

export function seedIreland(): Promise<SeedResult> {
  return requestJson("/api/v1/seed/ireland", { method: "POST" });
}

export function createDiscoveryPlan(
  territoryId: string,
  queryTemplateId: string
): Promise<DiscoveryPlan> {
  return requestJson("/api/v1/discovery/prepared-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      territory_id: territoryId,
      query_template_id: queryTemplateId,
      max_results_per_query: 20
    })
  });
}

export function launchAssistedSession(
  territoryId: string,
  queryTemplateId: string,
  querySequence: number
): Promise<AssistedSession> {
  return requestJson("/api/v1/discovery/prepared-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      territory_id: territoryId,
      query_template_id: queryTemplateId,
      max_results_per_query: 20,
      query_sequence: querySequence
    })
  });
}

export function markAssistedSessionReady(sessionId: string): Promise<AssistedSession> {
  return requestJson(`/api/v1/discovery/session/${sessionId}/ready`, { method: "POST" });
}

export function captureVisibleCandidates(sessionId: string): Promise<AssistedSessionReview> {
  return requestJson(`/api/v1/discovery/session/${sessionId}/capture-visible`, {
    method: "POST"
  });
}

export function collectBoundedCandidates(
  sessionId: string,
  queryText: string,
  querySequence = 1
): Promise<AssistedSessionReview> {
  const query = new URLSearchParams({
    query_text: queryText,
    query_sequence: String(querySequence)
  });
  return requestJson(`/api/v1/discovery/session/${sessionId}/collect-bounded?${query}`, {
    method: "POST"
  });
}

export function updateCandidateReview(
  sessionId: string,
  candidateId: string,
  included: boolean
): Promise<AssistedSessionReview> {
  return requestJson(`/api/v1/discovery/session/${sessionId}/candidates/${candidateId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ included })
  });
}

export function stopAssistedSession(sessionId: string): Promise<AssistedSession> {
  return requestJson(`/api/v1/discovery/session/${sessionId}`, { method: "DELETE" });
}

export function saveAggregateBusinesses(payload: AggregateBatchSave): Promise<AggregateSaveResult> {
  return requestJson("/api/v1/discovery/aggregate-businesses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}
