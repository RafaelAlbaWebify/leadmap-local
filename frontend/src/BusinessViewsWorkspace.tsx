import { useMemo, useState } from "react";

import { BusinessWorkspace, qualificationOptions } from "./BusinessWorkspaceLegacy";
import {
  applyBusinessView,
  BUSINESS_VIEWS_STORAGE_KEY,
  businessViewId,
  emptyBusinessViewCriteria,
  parseSavedBusinessViews,
  serializeSavedBusinessViews,
  type BusinessViewCriteria,
  type SavedBusinessView
} from "./businessViewsModel";
import type { Lead } from "./types";
import "./businessViewsWorkspace.css";

function loadViews(): SavedBusinessView[] {
  if (typeof window === "undefined") return [];
  return parseSavedBusinessViews(window.localStorage.getItem(BUSINESS_VIEWS_STORAGE_KEY));
}

export function BusinessViewsWorkspace({ leads }: { leads: Lead[] }) {
  const [criteria, setCriteria] = useState<BusinessViewCriteria>(emptyBusinessViewCriteria);
  const [savedViews, setSavedViews] = useState<SavedBusinessView[]>(loadViews);
  const [selectedViewId, setSelectedViewId] = useState("");
  const [viewName, setViewName] = useState("");
  const categories = useMemo(
    () => [...new Set(leads.map((lead) => lead.category))].sort((left, right) => left.localeCompare(right)),
    [leads]
  );
  const visibleLeads = useMemo(() => applyBusinessView(leads, criteria), [criteria, leads]);

  function persist(next: SavedBusinessView[]) {
    setSavedViews(next);
    window.localStorage.setItem(BUSINESS_VIEWS_STORAGE_KEY, serializeSavedBusinessViews(next));
  }

  function saveView() {
    const name = viewName.trim();
    if (!name) return;
    const id = businessViewId(name, savedViews.map((view) => view.id));
    const next = [...savedViews, { id, name, criteria: { ...criteria } }];
    persist(next);
    setSelectedViewId(id);
    setViewName("");
  }

  function applyView(id: string) {
    setSelectedViewId(id);
    const view = savedViews.find((item) => item.id === id);
    if (view) setCriteria({ ...view.criteria });
  }

  function renameView() {
    const name = viewName.trim();
    if (!selectedViewId || !name) return;
    persist(savedViews.map((view) => (view.id === selectedViewId ? { ...view, name } : view)));
    setViewName("");
  }

  function deleteView() {
    if (!selectedViewId) return;
    persist(savedViews.filter((view) => view.id !== selectedViewId));
    setSelectedViewId("");
  }

  function updateCriteria(patch: Partial<BusinessViewCriteria>) {
    setCriteria((current) => ({ ...current, ...patch }));
    setSelectedViewId("");
  }

  return (
    <div className="business-views-workspace">
      <section className="business-view-controls" aria-label="Business filters and saved views">
        <div className="business-view-heading">
          <div>
            <p className="eyebrow">SMART LISTS</p>
            <h3>Business views</h3>
            <p>Saved locally on this workstation. Business records and evidence are not copied.</p>
          </div>
          <strong>{visibleLeads.length} of {leads.length} businesses</strong>
        </div>

        <div className="business-view-filter-grid">
          <label>
            Search
            <input
              aria-label="Search businesses"
              value={criteria.text}
              placeholder="Name, category, area or website"
              onChange={(event) => updateCriteria({ text: event.target.value })}
            />
          </label>
          <label>
            Status
            <select
              aria-label="Qualification filter"
              value={criteria.qualification}
              onChange={(event) => updateCriteria({ qualification: event.target.value as BusinessViewCriteria["qualification"] })}
            >
              <option value="all">All</option>
              {qualificationOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label>
            Freshness
            <select
              aria-label="Freshness filter"
              value={criteria.freshness}
              onChange={(event) => updateCriteria({ freshness: event.target.value as BusinessViewCriteria["freshness"] })}
            >
              <option value="all">All</option>
              <option value="fresh">Fresh</option>
              <option value="ageing">Ageing</option>
              <option value="stale">Stale</option>
              <option value="never_verified">Never verified</option>
            </select>
          </label>
          <label>
            Category
            <select aria-label="Category filter" value={criteria.category} onChange={(event) => updateCriteria({ category: event.target.value })}>
              <option value="all">All</option>
              {categories.map((category) => <option key={category} value={category}>{category}</option>)}
            </select>
          </label>
          <label>
            Sort
            <select
              aria-label="Business sort"
              value={criteria.sort}
              onChange={(event) => updateCriteria({ sort: event.target.value as BusinessViewCriteria["sort"] })}
            >
              <option value="observed_desc">Recently observed</option>
              <option value="name_asc">Business name</option>
              <option value="category_asc">Category</option>
              <option value="qualification_asc">Status</option>
            </select>
          </label>
        </div>

        <div className="business-view-actions">
          <label>
            Saved view
            <select aria-label="Saved business view" value={selectedViewId} onChange={(event) => applyView(event.target.value)}>
              <option value="">Current unsaved view</option>
              {savedViews.map((view) => <option key={view.id} value={view.id}>{view.name}</option>)}
            </select>
          </label>
          <label>
            View name
            <input aria-label="Business view name" value={viewName} maxLength={80} onChange={(event) => setViewName(event.target.value)} />
          </label>
          <button className="primary-action compact" disabled={!viewName.trim()} onClick={saveView}>Save as new</button>
          <button className="secondary-action compact" disabled={!selectedViewId || !viewName.trim()} onClick={renameView}>Rename</button>
          <button className="secondary-action compact" disabled={!selectedViewId} onClick={deleteView}>Delete</button>
          <button
            className="secondary-action compact"
            onClick={() => {
              setCriteria(emptyBusinessViewCriteria);
              setSelectedViewId("");
            }}
          >
            Clear filters
          </button>
        </div>
      </section>

      <BusinessWorkspace leads={visibleLeads} />
    </div>
  );
}
