# Architecture Notes

## Component responsibilities

- **`data_generator.py`** — the only file that talks to "the outside world." In this build it synthesizes FIRMS/OSM-shaped data; in production it is replaced by real API clients. Everything downstream is agnostic to where `data/raw/*.json` came from.
- **`clustering.py`** — pure function over a list of detections, no I/O side effects beyond the CLI entry point. Easy to unit test and easy to port to a PostGIS `ST_ClusterDBSCAN` call at scale.
- **`feature_engineering.py`** — the only place domain knowledge about *what distinguishes a flare from a wildfire* lives, in `FEATURE_COLUMNS` and the per-feature computation. Extending the model with a new signal (e.g. a CNN patch score) means adding one column here.
- **`classifier.py`** — model training/evaluation/inference is isolated so the model type can be swapped (Random Forest → Gradient Boosting → ensemble with a CNN) without touching `pipeline.py` or the API.
- **`pipeline.py`** — the only orchestrator; it is what a scheduler (cron/Airflow) would call daily in production.
- **`app.py`** — thin Flask layer; all business logic lives below it, so swapping Flask for FastAPI later is a small, contained change.
- **`frontend/`** — no build step, no framework dependency, so it can be dropped onto any static host or served by Flask directly, and is straightforward for a team member unfamiliar with a JS toolchain to modify during a hackathon.

## Scaling path (post-hackathon)

| Concern | Prototype | Production |
|---|---|---|
| Storage | Flat JSON/GeoJSON files | PostGIS (spatial indexes, `ST_DWithin` facility joins) |
| Ingestion | Manual `python pipeline.py` / UI button | Scheduled job (cron/Airflow) polling FIRMS hourly |
| Serving | Flask dev server | Gunicorn/uWSGI behind nginx, or a managed API gateway |
| Auth | None | API keys / OAuth for the `/api/rerun` write endpoint |
| Frontend hosting | Served by Flask | Static hosting (Netlify/S3+CloudFront) calling a separate API host |
| Model | Random Forest retrained on demand | Scheduled retraining job + model registry (versioned `.pkl` or MLflow) |

## Data contracts

Every stage reads/writes a well-defined JSON shape so stages can be developed, tested and replaced independently:

- `data/raw/firms_detections.json` → `{ region, detections: [ {latitude, longitude, acq_date, acq_time, satellite, instrument, frp, brightness, bright_t31, confidence, daynight, landcover, ...} ] }`
- `data/raw/facilities.json` → `{ region, facilities: [ {facility_id, name, type, latitude, longitude} ] }`
- `data/processed/cluster_features.json` → `{ region, clusters: [ {cluster_id, latitude, longitude, ...FEATURE_COLUMNS, true_label} ] }`
- `data/processed/classified_hotzones.geojson` → standard `FeatureCollection`, `properties.predicted_class` + `properties.confidence` per feature
