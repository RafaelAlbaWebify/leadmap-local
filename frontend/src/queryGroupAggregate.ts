import type {
  AggregateBatchSave,
  AssistedSessionReview,
  TraversalStopReason,
  VisibleCandidate
} from "./types";

export interface QueryAppearance {
  queryText: string;
  querySequence: number;
  resultRank: number;
  firstSeenScrollStep: number;
  capturedAt: string;
  included: boolean;
  candidateId: string;
  sourceUrl: string | null;
  rawEvidence: string | null;
}

export interface AggregateBusinessReview {
  identityKey: string;
  representative: VisibleCandidate;
  appearances: QueryAppearance[];
  firstSeenOrder: number;
  included: boolean;
}

export interface AggregateQueryRun {
  queryText: string;
  querySequence: number;
  observationCount: number;
  uniqueBusinessesAdded: number;
  stopReason: TraversalStopReason | null;
}

export interface QueryGroupReview {
  businesses: AggregateBusinessReview[];
  queryRuns: AggregateQueryRun[];
  totalObservations: number;
  uniqueBusinesses: number;
  duplicateAppearances: number;
  includedBusinesses: number;
  excludedBusinesses: number;
}

export function aggregateQueryReviews(reviews: AssistedSessionReview[]): QueryGroupReview {
  const orderedReviews = [...reviews].sort(
    (left, right) => requiredQuerySequence(left) - requiredQuerySequence(right)
  );
  const seenSequences = new Set<number>();
  const businesses: AggregateBusinessReview[] = [];
  const indexes = new Map<string, number>();
  const queryRuns: AggregateQueryRun[] = [];
  let totalObservations = 0;

  for (const review of orderedReviews) {
    const querySequence = requiredQuerySequence(review);
    if (seenSequences.has(querySequence)) {
      throw new Error(`Query sequence ${querySequence} has already been aggregated.`);
    }
    seenSequences.add(querySequence);

    const queryText = review.traversal_progress?.query_text.trim();
    if (!queryText) {
      throw new Error(`Query sequence ${querySequence} is missing query text.`);
    }

    let uniqueBusinessesAdded = 0;
    for (const candidate of review.candidates) {
      const appearance = toAppearance(candidate, queryText, querySequence);
      const identityKey = businessIdentity(candidate);
      const existingIndex = indexes.get(identityKey);

      if (existingIndex === undefined) {
        indexes.set(identityKey, businesses.length);
        businesses.push({
          identityKey,
          representative: candidate,
          appearances: [appearance],
          firstSeenOrder: businesses.length + 1,
          included: candidate.included
        });
        uniqueBusinessesAdded += 1;
      } else {
        const existing = businesses[existingIndex];
        businesses[existingIndex] = {
          ...existing,
          appearances: [...existing.appearances, appearance],
          included: existing.included || candidate.included
        };
      }
      totalObservations += 1;
    }

    queryRuns.push({
      queryText,
      querySequence,
      observationCount: review.candidates.length,
      uniqueBusinessesAdded,
      stopReason: review.traversal_stop_reason ?? review.traversal_progress?.stop_reason ?? null
    });
  }

  const includedBusinesses = businesses.filter((business) => business.included).length;
  return {
    businesses,
    queryRuns,
    totalObservations,
    uniqueBusinesses: businesses.length,
    duplicateAppearances: totalObservations - businesses.length,
    includedBusinesses,
    excludedBusinesses: businesses.length - includedBusinesses
  };
}

export function buildAggregateSavePayload(
  reviews: AssistedSessionReview[],
  batchId: string,
  territoryId: string,
  queryTemplateId: string
): AggregateBatchSave {
  const aggregate = aggregateQueryReviews(reviews);
  if (!batchId.trim() || !territoryId.trim() || !queryTemplateId.trim()) {
    throw new Error("Aggregate persistence requires a batch, territory, and query template.");
  }
  return {
    batch_id: batchId,
    territory_id: territoryId,
    query_template_id: queryTemplateId,
    businesses: aggregate.businesses.map((business) => ({
      displayed_name: business.representative.displayed_name,
      normalized_name: business.representative.normalized_name,
      category: business.representative.category,
      address_text: business.representative.address_text,
      phone: business.representative.phone,
      website: business.representative.website,
      latitude: business.representative.latitude,
      longitude: business.representative.longitude,
      provider_key: business.representative.provider_key,
      included: business.included,
      observations: business.appearances.map((appearance) => ({
        query_text: appearance.queryText,
        query_sequence: appearance.querySequence,
        result_rank: appearance.resultRank,
        first_seen_scroll_step: appearance.firstSeenScrollStep,
        captured_at: appearance.capturedAt,
        source_url: appearance.sourceUrl,
        raw_evidence: appearance.rawEvidence,
        candidate_id: appearance.candidateId
      }))
    }))
  };
}

function requiredQuerySequence(review: AssistedSessionReview): number {
  const sequence = review.traversal_progress?.query_sequence;
  if (!sequence || sequence < 1) {
    throw new Error("A completed query review requires a positive query sequence.");
  }
  return sequence;
}

function toAppearance(
  candidate: VisibleCandidate,
  queryText: string,
  querySequence: number
): QueryAppearance {
  if (candidate.query_sequence !== querySequence) {
    throw new Error("Candidate query sequence does not match its completed review.");
  }
  if (!candidate.result_rank || candidate.result_rank < 1) {
    throw new Error("Candidate result rank must be a positive number.");
  }
  if (candidate.first_seen_scroll_step === null || candidate.first_seen_scroll_step === undefined) {
    throw new Error("Candidate first-seen scroll step is required for persistence.");
  }
  if (!candidate.captured_at) {
    throw new Error("Candidate capture timestamp is required for persistence.");
  }
  return {
    queryText: candidate.query_text?.trim() || queryText,
    querySequence,
    resultRank: candidate.result_rank,
    firstSeenScrollStep: candidate.first_seen_scroll_step,
    capturedAt: candidate.captured_at,
    included: candidate.included,
    candidateId: candidate.candidate_id,
    sourceUrl: candidate.source_url,
    rawEvidence: candidate.raw_evidence
  };
}

function businessIdentity(candidate: VisibleCandidate): string {
  const providerKey = candidate.provider_key.trim();
  if (providerKey) {
    return `provider:${providerKey}`;
  }

  const normalizedName = candidate.normalized_name.trim();
  const discriminator =
    candidate.phone?.trim() ||
    candidate.website?.trim().toLocaleLowerCase() ||
    candidate.address_text?.trim().toLocaleLowerCase();
  if (!normalizedName || !discriminator) {
    throw new Error("A business requires a provider key or a stable fallback identity.");
  }
  return `fallback:${normalizedName}|${discriminator}`;
}
