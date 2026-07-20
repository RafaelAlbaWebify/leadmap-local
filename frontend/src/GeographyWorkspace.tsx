import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import { fetchGeographyArtifact, fetchGeographyArtifacts } from "./api";
import type { GeographyArtifact, GeographyBoundary } from "./types";

const EMPTY_STYLE = {
  version: 8 as const,
  sources: {},
  layers: [{ id: "background", type: "background" as const, paint: { "background-color": "#f3f5f7" } }]
};

function asFeatureCollection(artifact: GeographyArtifact): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: artifact.boundaries.map((boundary) => ({
      type: "Feature",
      id: boundary.external_id,
      properties: { external_id: boundary.external_id, name: boundary.name },
      geometry: { type: boundary.geometry_type, coordinates: boundary.coordinates } as GeoJSON.Geometry
    }))
  };
}

function collectionBounds(boundaries: GeographyBoundary[]): maplibregl.LngLatBoundsLike | null {
  if (boundaries.length === 0) return null;
  return boundaries.reduce(
    (bounds, boundary) => [
      [Math.min(bounds[0][0], boundary.bounding_box.west), Math.min(bounds[0][1], boundary.bounding_box.south)],
      [Math.max(bounds[1][0], boundary.bounding_box.east), Math.max(bounds[1][1], boundary.bounding_box.north)]
    ],
    [
      [boundaries[0].bounding_box.west, boundaries[0].bounding_box.south],
      [boundaries[0].bounding_box.east, boundaries[0].bounding_box.north]
    ]
  );
}

export function GeographyWorkspace() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [selectedBoundary, setSelectedBoundary] = useState<GeographyBoundary | null>(null);
  const catalog = useQuery({ queryKey: ["geography-artifacts"], queryFn: fetchGeographyArtifacts });
  const selectedArtifact = catalog.data?.[0];
  const artifact = useQuery({
    queryKey: ["geography-artifact", selectedArtifact?.checksum_sha256],
    queryFn: () => fetchGeographyArtifact(selectedArtifact!.checksum_sha256),
    enabled: Boolean(selectedArtifact)
  });

  const featureCollection = useMemo(
    () => (artifact.data ? asFeatureCollection(artifact.data) : null),
    [artifact.data]
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = new maplibregl.Map({
      container: containerRef.current,
      style: EMPTY_STYLE,
      center: [-8, 53.4],
      zoom: 5.4,
      attributionControl: false
    });
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !featureCollection || !artifact.data) return;

    const render = () => {
      const source = map.getSource("boundaries") as GeoJSONSource | undefined;
      if (source) source.setData(featureCollection);
      else {
        map.addSource("boundaries", { type: "geojson", data: featureCollection });
        map.addLayer({
          id: "boundary-fill",
          type: "fill",
          source: "boundaries",
          paint: { "fill-color": "#6f8899", "fill-opacity": 0.28 }
        });
        map.addLayer({
          id: "boundary-line",
          type: "line",
          source: "boundaries",
          paint: { "line-color": "#435867", "line-width": 1.2 }
        });
        map.on("click", "boundary-fill", (event) => {
          const id = String(event.features?.[0]?.properties?.external_id ?? "");
          setSelectedBoundary(artifact.data?.boundaries.find((item) => item.external_id === id) ?? null);
        });
        map.on("mouseenter", "boundary-fill", () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", "boundary-fill", () => { map.getCanvas().style.cursor = ""; });
      }
      const bounds = collectionBounds(artifact.data.boundaries);
      if (bounds) map.fitBounds(bounds, { padding: 28, duration: 0 });
    };

    if (map.loaded()) render();
    else map.once("load", render);
  }, [artifact.data, featureCollection]);

  if (catalog.isLoading) return <div className="map-state">Loading geographic catalog…</div>;
  if (catalog.isError) return <div className="map-state error">The geographic catalog could not be loaded.</div>;
  if (!selectedArtifact) return <div className="map-state">No geographic artifacts are available yet.</div>;
  if (artifact.isError) return <div className="map-state error">The selected geographic artifact is invalid or unavailable.</div>;

  return (
    <div className="geography-workspace">
      <div className="geography-map" ref={containerRef} aria-label="Ireland local authority map" />
      <aside className="geography-detail">
        <span className="badge neutral">{selectedArtifact.source.edition_year}</span>
        <h3>{selectedBoundary?.name ?? selectedArtifact.source.dataset_title}</h3>
        <p>{selectedBoundary ? "Selected local authority" : `${selectedArtifact.feature_count} validated boundaries`}</p>
        <dl>
          <div><dt>Publisher</dt><dd>{selectedArtifact.source.publisher}</dd></div>
          <div><dt>Licence</dt><dd>{selectedArtifact.source.licence}</dd></div>
          <div><dt>Retrieved</dt><dd>{new Date(selectedArtifact.source.retrieved_at).toLocaleDateString()}</dd></div>
        </dl>
        <small>Map data © {selectedArtifact.source.publisher}. Select a boundary to inspect it.</small>
      </aside>
    </div>
  );
}
