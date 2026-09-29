# THERMOSCAN

Live Prototype: [Click Here](https://thermo-scan.onrender.com/)

### AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources

A working prototype built for Smart India Hackathon, addressing the problem statement:
> *"AI-Enabled Geospatial System integrating NASA FIRMS thermal data, OSM/industrial databases and satellite-derived land cover to automatically identify, classify and monitor industrial fires and persistent thermal sources — separating them from wildfires, agricultural burns and mining activity."*

---

## 1. What this prototype does

1. **Ingests** thermal hotspot detections (FIRMS/VIIRS-style: lat, lon, FRP, brightness temperature, acquisition time, day/night flag).
2. **Clusters** raw detections into candidate *hot zones* using spatio-temporal DBSCAN, so repeated detections at the same physical source collapse into one object instead of hundreds of loose points.
3. **Enriches** each hot zone with land-cover fractions (built-up / bare / cropland / forest) and distance to the nearest known industrial facility (power plant, refinery, steel plant, gas flare, mining site) — the OSM / Global Power Plant Database / Global Gas Flaring Dataset layer.
4. **Classifies** each hot zone with a Random Forest trained on these features into one of five classes: **Industrial Fire, Flare, Mining Activity, Agricultural Burn, Wildfire.**
5. **Publishes** the classified hot zones as a GeoJSON GIS layer and serves it through a Flask API.
6. **Visualizes** the result on an interactive, dark-themed map console (Leaflet.js) with filtering by class, a live legend, facility overlay, and a detail drawer per hot zone — usable on desktop, tablet and mobile.

This directly satisfies both deliverables in the PS:
- **(i)** Classification/segregation of industrial fires from forest fires and other natural fires — done by the clustering + Random Forest pipeline.
- **(ii)** GIS-based storage and visualization as a map overlay — done by the GeoJSON export + Leaflet console.

---

## 2. Why the data is synthetic in this build

NASA FIRMS, OSM Overpass, the Global Power Plant Database and the Global Gas Flaring Dataset are all live external services that require outbound internet access and, in FIRMS' case, a personal API key. This development environment cannot reach those endpoints, so `backend/data_generator.py` produces a **schema-faithful synthetic dataset**: it creates realistic facility locations (refineries, power plants, steel plants, gas flares, mining sites), realistic wildfire/agricultural-burn zones, and 30 days of FIRMS-style detections with the actual field names, units and value ranges FIRMS/VIIRS output. The rest of the pipeline (clustering → features → classifier → GIS layer) runs completely unmodified whether the input came from the generator or from the real APIs. **Section 7** explains exactly what to change to point the pipeline at live data.

Because the synthetic classes are cleanly separated by design, the demo classifier reports very high cross-validated accuracy. Treat that number as evidence the *pipeline is wired correctly*, not as a real-world accuracy claim — real FIRMS/VIIRS data will have far more class overlap (e.g. a flare during a low-activity night looks a lot like a small agricultural burn), and the model would need retraining on real, hand-labeled events before deployment. This caveat is worth stating upfront to the judges — it shows engineering maturity rather than an inflated number.

---

## 3. Architecture

```
NASA FIRMS/VIIRS ─┐
OSM industrial pts─┼──▶ data_generator.py  (swap for live API clients)
Land cover source ─┘         │
                              ▼
                    data/raw/*.json  (FIRMS-schema detections,
                                       facility registry, natural zones)
                              │
                              ▼
                     clustering.py  (haversine DBSCAN)
                              │  candidate hot zones
                              ▼
               feature_engineering.py  (persistence, FRP stats,
                                         night ratio, land cover mix,
                                         distance to nearest facility)
                              │  feature table
                              ▼
                      classifier.py  (Random Forest, 5-fold CV,
                                       class_weight="balanced")
                              │  predicted class + confidence
                              ▼
                       pipeline.py  (orchestrates the above,
                                      writes GeoJSON + summary)
                              │
                              ▼
                        backend/app.py  (Flask REST API)
                              │  /api/hotzones  /api/facilities
                              │  /api/summary   /api/metrics
                              │  /api/rerun (POST)
                              ▼
                    frontend/ (Leaflet console)
                    index.html + style.css + app.js
```

### Tech stack

| Layer               | Choice                                             |
|---------------------|-----------------------------------------------------|
| Clustering           | scikit-learn `DBSCAN` (haversine metric)            |
| Classification        | scikit-learn `RandomForestClassifier`               |
| Backend API          | Flask + Flask-CORS                                   |
| Geospatial storage    | GeoJSON files (swap-in ready for PostGIS/GeoPackage) |
| Frontend map          | Leaflet.js + CARTO dark basemap tiles                |
| Frontend UI           | Vanilla HTML/CSS/JS (no build step — runs anywhere)  |

---

## 4. Project structure

```
industrial-fire-detection/
├── README.md
├── requirements.txt
├── run.sh                     # one-command setup + launch (Linux/macOS)
├── run.bat                    # one-command setup + launch (Windows)
├── .gitignore
├── backend/
│   ├── data_generator.py      # synthetic FIRMS/OSM/GPPD/flaring data (swap for live APIs)
│   ├── clustering.py          # spatio-temporal DBSCAN
│   ├── feature_engineering.py # cluster -> feature vector
│   ├── classifier.py          # train/evaluate/predict Random Forest
│   ├── pipeline.py            # end-to-end orchestrator, GeoJSON export
│   ├── app.py                 # Flask REST API
│   ├── data/
│   │   ├── raw/                # generated FIRMS-style detections, facilities
│   │   └── processed/          # cluster features, classified GeoJSON, summary
│   └── model/                  # trained classifier.pkl, label_encoder.pkl, metrics.json
├── frontend/
│   ├── index.html              # dashboard shell
│   ├── style.css                # dark ops-console theme, responsive
│   └── app.js                   # fetches API, renders map, filters, drawer
└── docs/
    ├── architecture.md
    └── methodology.md
```

---

## 5. How to run it

### Requirements
- Python 3.10+
- A modern browser
- No internet access required to run the demo (Leaflet/tile requests need internet for the basemap only; the app logic itself works offline against localhost)

### Quick start (Linux/macOS)
```bash
git clone <your-repo-url> industrial-fire-detection
cd industrial-fire-detection
./run.sh
```

### Quick start (Windows)
```bat
git clone <your-repo-url> industrial-fire-detection
cd industrial-fire-detection
run.bat
```

### Manual setup (any OS)
```bash
python3 -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt

cd backend
mkdir -p data/raw data/processed model
python3 pipeline.py              # generates data, clusters, trains, exports GeoJSON
python3 app.py                   # starts the Flask server on http://localhost:5000
```

Then open **http://localhost:5000** in your browser. The Flask app serves the frontend and the API from the same origin, so nothing else needs to run.

### Region switching (built into the app)
The sidebar's **Region** panel lets you switch the whole monitoring area from the UI — no file editing needed:
- Pick one of the built-in presets (Maharashtra, Jamshedpur Steel Belt, Jamnagar-Vadodara Refinery Corridor, Dhanbad-Jharia Coalfields, National Capital Region), **or**
- Choose "Custom bounds…" and enter your own lat/lon box and a name.

Hitting **Apply region** calls `POST /api/region`, which regenerates the synthetic dataset inside those bounds, retrains the classifier, and refreshes the map — the same live-pipeline behavior as "Re-run classification," just scoped to wherever you point it. New presets can be added in `backend/data_generator.py`'s `PRESET_REGIONS` dict.

### Re-running the pipeline from the UI
The sidebar has a **"Re-run classification"** button that calls `POST /api/rerun`, which regenerates hot zones, retrains the classifier and refreshes the map — useful for demoing that the system is a live pipeline, not a static picture.

### API reference

| Endpoint          | Method | Returns                                             |
|--------------------|--------|------------------------------------------------------|
| `/api/hotzones`     | GET    | GeoJSON FeatureCollection of classified hot zones     |
| `/api/facilities`   | GET    | GeoJSON FeatureCollection of industrial facilities    |
| `/api/summary`      | GET    | Region info, class counts, headline model metrics     |
| `/api/metrics`      | GET    | Full classification report, confusion matrix, feature importances |
| `/api/rerun`        | POST   | Re-runs the full pipeline and returns the new summary  |
| `/api/regions`      | GET    | List of built-in region presets                        |
| `/api/region`       | POST   | Switches the monitoring region (`{"preset": "jamshedpur"}` or `{"lat_min","lat_max","lon_min","lon_max","name"}`), regenerates data, retrains, returns the new summary |

---

## 6. Evaluation approach

- **Cross-validation**: 5-fold CV accuracy reported in the sidebar and `/api/metrics`.
- **Held-out test split**: 25% of hot zones withheld from training for a final check.
- **Confusion matrix & per-class precision/recall/F1**: in `backend/model/metrics.json` after any pipeline run.
- **Feature importances**: exposed via `/api/metrics`, so you can explain to judges *why* the model made a call (e.g. persistence ratio and distance-to-facility dominate the industrial vs. wildfire split — which matches the domain reasoning in the original research brief).

See `docs/methodology.md` for the full reasoning behind each feature and modeling choice.

---

## 7. Wiring in real data (post-hackathon / production path)

Replace the calls inside `backend/data_generator.py` with real API clients, keeping the exact output schema in `data/raw/*.json` unchanged so nothing downstream needs to change:

1. **NASA FIRMS** — register for a MAP_KEY at `firms.modaps.eosdis.nasa.gov/api`, pull the CSV/JSON hotspot feed for your AOI and date range.
2. **OSM industrial facilities** — query the Overpass API for `man_made=works`, `landuse=industrial`, `power=plant`, etc.
3. **Global Power Plant Database** — WRI's public CSV, filtered to your region.
4. **Global Gas Flaring Dataset** — NOAA/Colorado School of Mines VIIRS Nightfire flare locations.
5. **Land cover** — ESA WorldCover or Copernicus Global Land Cover, sampled per hot-zone buffer.
6. Point `clustering.py` / `feature_engineering.py` at PostGIS instead of flat JSON once volumes grow — the SQL equivalents of the current haversine/DBSCAN and distance joins are straightforward (`ST_DWithin`, `ST_Distance`).
7. Add a scheduler (cron / Airflow) to call `pipeline.run_pipeline()` daily against the fresh FIRMS feed, matching the "operational, updating daily" goal in the original research brief.

---

## 8. Known limitations of this prototype

- Trained and evaluated only on synthetic data (see Section 2) — needs retraining on a hand-labeled real-world dataset before any operational claim.
- No authentication/rate limiting on the API — fine for a demo, not for production.
- GeoJSON files stand in for PostGIS; adequate at hackathon scale (tens of thousands of points), not at national scale.
- CNN-on-multispectral-patches (mentioned as an option in the original brief) is not implemented here — the tabular Random Forest was chosen for the prototype because it is fast to train, interpretable for judges, and does not require downloading large raw satellite imagery tiles in this environment. `docs/methodology.md` outlines how the CNN path would slot in later.
