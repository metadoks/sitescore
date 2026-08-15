# Checkpoint 3.3-7 — Vehicle Road Network + Drive Reachability

Scope: pinned road-network source + Valhalla auto isochrone execution + precomputed measurement evidence -> frozen RoadAccessSnapshot. No parking, ECDF, normalization, app/core integration.

Official verification (2026-08-13):
- Valhalla Isochrone API: https://valhalla.github.io/valhalla/api/isochrone/
- Valhalla routing overview/data sources: https://valhalla.github.io/valhalla/api/turn-by-turn/overview/
- Valhalla speed/traffic semantics: https://valhalla.github.io/valhalla/concepts/speeds/
- Valhalla status semantics: https://valhalla.github.io/valhalla/api/status/
- Valhalla releases: https://github.com/valhalla/valhalla/releases (3.8.3 released 2026-07-24; deployment must still pin exact engine version)
- OpenStreetMap copyright/license: https://www.openstreetmap.org/copyright

V1 decisions:
- provider choice OSM/Valhalla is an initial prior, not structural.
- network, graph, engine/profile, execution policy and binding are separately versioned.
- graph_artifact_ref is replay/provenance only and excluded from semantic compatibility/request hashes.
- canonical profile is Valhalla `auto`.
- RoadTrafficPolicy is `static_graph_no_datetime`; request body omits `date_time`, preventing hidden current/predicted traffic-time semantics from becoming canonical road accessibility.
- drive budgets are explicit seconds; Valhalla contour requests convert seconds to minutes at request boundary.
- execution max_contours/max_time_contour are checked before network.
- any Valhalla warning is preserved and rejects canonical AVAILABLE V1 output.
- unresolved snap is not zero road accessibility.
- WGS84 GeoJSON Polygon/MultiPolygon geometry is canonicalized for serialization order only; no GIS topology engine.
- numeric road metrics are caller/precomputed RoadScaleMeasurementEvidence bound to exact returned contour geometry and versioned area/network-measurement methods. No degree-squared area calculation.
- network artifact bytes are re-read from ArtifactStore and hashed against RoadNetworkManifest.network_content_hash.
- runtime graph-content proof is a trusted deployment/config attestation via RoadRoutingExecutionBinding, not a claim that Valhalla /status returns exact graph SHA-256.
