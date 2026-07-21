export type FreshnessStatus = "fresh" | "ageing" | "stale" | "never_verified";

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
  qualification_status: string;
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

export interface DiscoveryPlan {
  territory_id: string;
  territory_name: string;
  country_code: string;
  query_template_id: string;
  query_template_name: string;
  sector: string;
  phrases: string[];
  max_results_per_query: number;
  total_planned_queries: number;
  mode: "assisted";
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
