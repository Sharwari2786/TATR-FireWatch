# Methodology

## 1. From raw detections to hot zones

A single physical source (a flare stack, a forest fire) produces many separate FIRMS/VIIRS detections over days — one row per satellite overpass. Classifying each row independently would throw away the temporal pattern that is the strongest signal for telling sources apart. So the first step is spatio-temporal clustering:

- **Algorithm**: DBSCAN with the haversine metric directly on (lat, lon) in radians, `eps = 1.5 km`, `min_samples = 2`.
- **Why DBSCAN over k-means**: the number of true hot zones in a region is unknown ahead of time, and hot zones are irregular in shape/density. DBSCAN discovers the number of clusters itself and naturally marks isolated single detections as noise (`-1`), which is exactly the "not enough evidence yet" behavior we want at the edge of a scan.

## 2. Feature engineering — one row per hot zone

| Feature | Rationale |
|---|---|
| `n_detections`, `persistence_days`, `persistence_ratio` | A flare or a refinery burns continuously — persistence over the observation window is the single strongest industrial-vs-natural signal (this is exactly the pattern called out in the original research brief: *"a hotspot that blinks on only seasonally... is likely a wildfire, whereas a continuously active hotspot... is a gas flare"*). |
| `night_ratio` | Flares and industrial stacks are visible both day and night at a stable rate; forest fires and agricultural burns are more time-of-day dependent (burns are often lit during the day; wildfire spread also varies with diurnal humidity/wind cycles). |
| `frp_mean`, `frp_std`, `frp_cv` | Fire Radiative Power indicates intensity; its coefficient of variation captures whether the source is a steady low-intensity burn (flare) or an erratic high-intensity event (wildfire). |
| `bright_t31_mean` | Brightness temperature in the mid-infrared channel — a standard FIRMS/MODIS field used operationally to separate hot, compact sources from diffuse ones. |
| `confidence_mean` | Passed through from the FIRMS/VIIRS confidence field. |
| `dist_to_nearest_facility_km` | Directly operationalizes the OSM/Global Power Plant Database/Global Gas Flaring Dataset overlay from the brief — if a hot zone sits on a registered facility, that is strong evidence it is an industrial source, not a wildfire. |
| `builtup_frac`, `bare_frac`, `cropland_frac`, `forest_frac` | Land-cover mix around the zone (the WorldCover/CGLS layer from the brief) — industrial zones sit on built-up/bare land, wildfires in forest, agricultural burns in cropland. |

## 3. Classifier

- **Model**: `RandomForestClassifier` (300 trees, `max_depth=8`, `class_weight="balanced"`).
- **Why Random Forest for the prototype**: it handles the mixed-scale tabular features above without scaling, is robust to the modest sample size a hackathon-scale dataset provides, trains in well under a second so the "Re-run classification" button in the UI can retrain live during a demo, and — critically for a judged prototype — exposes feature importances that let you explain *why* a hot zone got its label instead of presenting a black box.
- **Validation**: 5-fold cross-validation on the full feature table, plus a held-out 25% test split for a final classification report and confusion matrix (`backend/model/metrics.json`, exposed via `/api/metrics`).
- **Class imbalance**: `class_weight="balanced"` compensates for the fact that flares/mining sites are naturally rarer than industrial fires or wildfires in the generated scenario.

## 4. Where a CNN would fit (future work)

The original brief also proposes feeding multispectral image patches around each anomaly into a CNN trained on labeled fire-vs-flare imagery (e.g. Sentinel-2/Landsat SWIR+thermal bands). That path needs downloading and tiling raw satellite scenes per hot zone, which is a heavier data-engineering job best done once real FIRMS coordinates and a Sentinel Hub/Earth Engine credential are available. The current tabular pipeline is designed so a CNN's output (a class probability vector per patch) could be added as one more feature column to `feature_engineering.py` without changing anything else — an ensemble of "tabular Random Forest + patch CNN" would be the natural next iteration.

## 5. GIS layer & visualization

Classified hot zones and the facility registry are exported as GeoJSON (`data/processed/classified_hotzones.geojson`, `facilities.geojson`) — the standard interchange format for GIS tools (QGIS, Mapbox, Leaflet, PostGIS `ST_GeomFromGeoJSON`). The frontend consumes these through the Flask API and renders them on a Leaflet map with class-colored markers, a legend/filter panel, a facility overlay toggle, and a detail drawer showing the full feature readout for any selected hot zone — fulfilling the "overlay visualization on a GIS-based system" deliverable from the problem statement.
