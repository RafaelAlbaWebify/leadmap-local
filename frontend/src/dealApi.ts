export type DealStage = "lead" | "discovery" | "proposal" | "won" | "lost";

export interface Deal {
  id: string;
  business_id: string;
  business_name: string;
  title: string;
  stage: DealStage;
  value_eur_cents: number | null;
  next_action: string | null;
  created_at: string;
  updated_at: string;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchDeals(): Promise<Deal[]> {
  return requestJson("/api/v1/deals");
}

export function createDeal(
  businessId: string,
  payload: {
    title: string;
    stage: DealStage;
    value_eur_cents: number | null;
    next_action: string | null;
  }
): Promise<Deal> {
  return requestJson(`/api/v1/businesses/${businessId}/deals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}
