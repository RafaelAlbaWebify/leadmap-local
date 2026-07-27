import type { FreshnessStatus, Lead, QualificationStatus } from "./types";

export const BUSINESS_VIEWS_STORAGE_KEY = "leadmap.businessViews.v1";
export const BUSINESS_VIEWS_SCHEMA_VERSION = 1;

export type BusinessSort = "observed_desc" | "name_asc" | "category_asc" | "qualification_asc";

export interface BusinessViewCriteria {
  text: string;
  qualification: QualificationStatus | "all";
  freshness: FreshnessStatus | "all";
  category: string;
  sort: BusinessSort;
}

export interface SavedBusinessView {
  id: string;
  name: string;
  criteria: BusinessViewCriteria;
}

export interface SavedBusinessViewDocument {
  version: 1;
  views: SavedBusinessView[];
}

export const emptyBusinessViewCriteria: BusinessViewCriteria = {
  text: "",
  qualification: "all",
  freshness: "all",
  category: "all",
  sort: "observed_desc"
};

const qualificationValues = new Set<string>([
  "all",
  "new",
  "needs_review",
  "qualified",
  "unsuitable",
  "duplicate",
  "archived"
]);
const freshnessValues = new Set<string>(["all", "fresh", "ageing", "stale", "never_verified"]);
const sortValues = new Set<string>(["observed_desc", "name_asc", "category_asc", "qualification_asc"]);

function normalize(value: string): string {
  return value.trim().toLocaleLowerCase();
}

export function businessViewId(name: string, existingIds: Iterable<string> = []): string {
  const base = normalize(name)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "view";
  const used = new Set(existingIds);
  if (!used.has(base)) return base;
  let suffix = 2;
  while (used.has(`${base}-${suffix}`)) suffix += 1;
  return `${base}-${suffix}`;
}

function validCriteria(value: unknown): value is BusinessViewCriteria {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.text === "string" &&
    typeof candidate.qualification === "string" &&
    qualificationValues.has(candidate.qualification) &&
    typeof candidate.freshness === "string" &&
    freshnessValues.has(candidate.freshness) &&
    typeof candidate.category === "string" &&
    typeof candidate.sort === "string" &&
    sortValues.has(candidate.sort)
  );
}

export function parseSavedBusinessViews(raw: string | null): SavedBusinessView[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return [];
    const document = parsed as Record<string, unknown>;
    if (document.version !== BUSINESS_VIEWS_SCHEMA_VERSION || !Array.isArray(document.views)) return [];
    const result: SavedBusinessView[] = [];
    const ids = new Set<string>();
    for (const value of document.views) {
      if (!value || typeof value !== "object") return [];
      const candidate = value as Record<string, unknown>;
      if (
        typeof candidate.id !== "string" ||
        !candidate.id ||
        ids.has(candidate.id) ||
        typeof candidate.name !== "string" ||
        !candidate.name.trim() ||
        !validCriteria(candidate.criteria)
      ) return [];
      ids.add(candidate.id);
      result.push({ id: candidate.id, name: candidate.name.trim(), criteria: { ...candidate.criteria } });
    }
    return result;
  } catch {
    return [];
  }
}

export function serializeSavedBusinessViews(views: SavedBusinessView[]): string {
  const document: SavedBusinessViewDocument = { version: BUSINESS_VIEWS_SCHEMA_VERSION, views };
  return JSON.stringify(document);
}

export function applyBusinessView(leads: Lead[], criteria: BusinessViewCriteria): Lead[] {
  const text = normalize(criteria.text);
  return leads
    .filter((lead) => {
      const searchable = normalize([lead.name, lead.category, lead.locality, lead.postal_area ?? "", lead.website ?? ""].join(" "));
      return (
        (!text || searchable.includes(text)) &&
        (criteria.qualification === "all" || lead.qualification_status === criteria.qualification) &&
        (criteria.freshness === "all" || lead.freshness === criteria.freshness) &&
        (criteria.category === "all" || lead.category === criteria.category)
      );
    })
    .sort((left, right) => {
      if (criteria.sort === "name_asc") return left.name.localeCompare(right.name) || left.id.localeCompare(right.id);
      if (criteria.sort === "category_asc") return left.category.localeCompare(right.category) || left.name.localeCompare(right.name);
      if (criteria.sort === "qualification_asc") {
        return left.qualification_status.localeCompare(right.qualification_status) || left.name.localeCompare(right.name);
      }
      return right.last_observed_at.localeCompare(left.last_observed_at) || left.id.localeCompare(right.id);
    });
}
