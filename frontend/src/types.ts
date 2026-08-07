export type FreshnessStatus = "fresh" | "ageing" | "stale" | "never_verified";
export type QualificationStatus =
  | "new"
  | "needs_review"
  | "qualified"
  | "shortlisted"
  | "sent_to_veridra"
  | "veridra_reviewed"
  | "approved_for_outreach"
  | "contacted"
  | "responded"
  | "conversation"
  | "proposal"
  | "customer"
  | "unsuitable"
  | "duplicate"
  | "archived";

export interface Lead {
  id: string;
  name: string;
  category: string;
  locality: string;
  postal_area: string | null;
  website: string | null;
  phone: string | null;
  first_observed_at: string;
  last_observed_at: string;
  freshness: FreshnessStatus;
  qualification_status: QualificationStatus;
}

export interface BusinessLocationDetail {
  id: string;
  locality: string;
  administrative_area: string | null;
  country_code: string;
  postal_area: string | null;
  phone: string | null;
  website: string | null;
  latitude: string | null;
  longitude: string | null;
  created_at: string;
  updated_at: string;
}

export interface BusinessObservationDetail {
  id: string;
  location_id: string;
  provider: string;
  provider_key: string;
  displayed_name: string;
  category: string;
  source_url: string | null;
  observed_at: string;
  query_text: string;
  search_run_status: string;
  query_sequence: number | null;
  result_rank: number | null;
  first_seen_scroll_step: number | null;
  candidate_id: string | null;
  raw_evidence: string | null;
  address_text: string | null;
}

export interface BusinessDetail {
  id: string;
  canonical_name: string;
  normalized_name: string;
  qualification_status: QualificationStatus;
  freshness: FreshnessStatus;
  created_at: string;
  updated_at: string;
  locations: BusinessLocationDetail[];
  observations: BusinessObservationDetail[];
}

export interface BusinessQualificationResult {
  id: string;
  qualification_status: QualificationStatus;
  updated_at: string;
}

export interface BusinessNote {
  id: string;
  business_id: string;
  content: string;
  created_at: string;
}

export interface DashboardSummary {
  total_businesses: number;
  qualified_leads: number;
  needs_review: number;
  stale_records: number;
  territories: number;
  recent_leads: Lead[];
}

export interface Territory {
  id: string;
  name: string;
  country_code: string;
  administrative_area: string | null;
  locality: string | null;
  created_at: string;
}

export interface QueryTemplate {
  id: string;
  name: string;
  sector: string;
  countries: string[];
  phrases: string[];
  created_at: string;
}

export interface SeedResult {
  territories_created: number;
  query_templates_created: number;
  total_territories: number;
  total_query_templates: number;
}

export interface PreparedQuery {
  sequence: number;
  phrase: string;
  query_text: string;
}

export interface DiscoveryPlan {
  territory_id: string;
  territory_name: string;
  country_code: string;
  query_template_id: string;
  query_template_name: string;
  sector: string;
  max_results_per_query: number;
  total_planned_queries: number;
  prepared_queries: PreparedQuery[];
  mode: "assisted";
}

export type AssistedSessionState =
  | "idle"
  | "launching"
  | "awaiting_operator"
  | "ready"
  | "capturing"
  | "review"
  | "stopped"
  | "failed";

export type TraversalStopReason =
  | "end_of_list"
  | "no_new_results"
  | "max_cards"
  | "max_scrolls"
  | "timeout"
  | "operator_stop"
  | "provider_error";

export interface TraversalProgress {
  query_text: string;
  query_sequence: number;
  scroll_step: number;
  unique_cards: number;
  stagnant_scrolls: number;
  elapsed_seconds: number;
  stop_reason: TraversalStopReason | null;
}

export interface AssistedSession {
  session_id: string | null;
  state: AssistedSessionState;
  territory_id: string | null;
  query_template_id: string | null;
  start_url: string | null;
  error: string | null;
  traversal_progress?: TraversalProgress | null;
  traversal_stop_reason?: TraversalStopReason | null;
}

export interface VisibleCandidate {
  candidate_id: string;
  provider_key: string;
  displayed_name: string;
  normalized_name: string;
  category: string | null;
  address_text: string | null;
  phone: string | null;
  website: string | null;
  source_url: string | null;
  latitude: string | null;
  longitude: string | null;
  raw_evidence: string | null;
  included: boolean;
  query_text?: string | null;
  query_sequence?: number | null;
  result_rank?: number | null;
  first_seen_scroll_step?: number | null;
  captured_at?: string | null;
}

export interface AssistedSessionReview extends AssistedSession {
  candidates: VisibleCandidate[];
  included_count: number;
  excluded_count: number;
}

export interface AggregateObservationSave {
  query_text: string;
  query_sequence: number;
  result_rank: number;
  first_seen_scroll_step: number;
  captured_at: string;
  source_url: string | null;
  raw_evidence: string | null;
  candidate_id: string;
}

export interface AggregateBusinessSave {
  displayed_name: string;
  normalized_name: string;
  category: string | null;
  address_text: string | null;
  phone: string | null;
  website: string | null;
  latitude: string | null;
  longitude: string | null;
  provider_key: string;
  included: boolean;
  observations: AggregateObservationSave[];
}

export interface AggregateBatchSave {
  batch_id: string;
  territory_id: string;
  query_template_id: string;
  businesses: AggregateBusinessSave[];
}

export interface AggregateSaveResult {
  businesses_created: number;
  businesses_matched: number;
  observations_created: number;
  observations_skipped: number;
  businesses_skipped: number;
}

export interface GeographySource {
  dataset_title: string;
  publisher: string;
  licence: string;
  edition_year: number;
  source_url: string;
  retrieved_at: string;
}

export interface GeographyArtifactSummary {
  schema_version: string;
  idempotency_key: string;
  checksum_sha256: string;
  source: GeographySource;
  feature_count: number;
}

export interface GeographyBoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface GeographyBoundary {
  external_id: string;
  name: string;
  geometry_type: "Polygon" | "MultiPolygon";
  coordinates: unknown;
  bounding_box: GeographyBoundingBox;
}

export interface GeographyArtifact extends GeographyArtifactSummary {
  boundaries: GeographyBoundary[];
}

export interface TerritoryBoundaryLink {
  territory_id: string;
  checksum_sha256: string;
  boundary_external_id: string;
  boundary_name: string;
}

export interface TerritoryCoverage {
  territory_id: string;
  territory_name: string;
  checksum_sha256: string;
  boundary_external_id: string;
  boundary_name: string;
  lead_count: number;
  latest_observed_at: string | null;
  freshness: FreshnessStatus;
}
