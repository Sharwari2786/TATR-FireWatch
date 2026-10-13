


# TATR FireWatch

AI-Enabled Forest Fire Early Detection, Geospatial Zoning & Ranger Dispatch System  
**Target Area:** Tadoba-Andhari Tiger Reserve (TATR), Maharashtra, India  
**Hackathon Prototype:** Smart India Hackathon

---


Live Prototype: [Click Here](https://thermo-scan.onrender.com/)

---
## 1. Overview

TATR FireWatch is an operational geospatial decision-support dashboard designed to detect and combat wildfire outbreaks across fragile tiger habitats. It processes satellite thermal detections, clusters contiguous fire fronts, classifies risk using machine learning, and coordinates real-time tactical dispatches to the nearest forest rangers.

### Core Capabilities
* **Satellite Thermal Ingestion:** Ingests NASA FIRMS (VIIRS/MODIS) thermal telemetry (FRP, brightness temperature, coordinates, acquisition time).
* **Spatio-Temporal DBSCAN Clustering:** Aggregates sparse hotspot pixels into coherent incident perimeters.
* **Geospatial Zoning:** Overlays fires with official TATR Core vs. Buffer boundary polygons and forest beat infrastructure (ranger HQs, outposts, watchtowers).
* **ML Risk Classification:** Random Forest classifier categorizes incidents into Deep Core Forest Fire, Buffer Zone Surface Fire, Agricultural Fringe Burn, and Mining Edge anomalies.
* **Fire Spread Trajectories:** Computes 3-hour vector projections along seasonal dry-season wind corridors.
* **Tactical Ranger Dispatch:** Automatically triages severe incidents and calculates geodesic response distances to deploy forest guards.
* **GIS Interoperability:** Exports incident intelligence as GeoJSON perimeters and tabular CSV reports.

---

## 2. Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Clustering** | Scikit-Learn `DBSCAN` (Haversine metric) |
| **Machine Learning** | Scikit-Learn `RandomForestClassifier` (Balanced class weighting) |
| **Backend Service** | Flask, Flask-CORS, Gunicorn |
| **Frontend Console** | Leaflet.js, OpenStreetMap, Vanilla JavaScript, CSS3 |
| **Data Formats** | GeoJSON, NASA FIRMS Schema |

---

## 3. Repository Structure

```text
TATR-FireWatch/
├── backend/
│   ├── app.py                  # Flask REST API and static frontend router
│   ├── clustering.py           # Haversine spatio-temporal DBSCAN
│   ├── feature_engineering.py  # Incident feature matrix construction
│   ├── classifier.py           # Random Forest evaluation and inference
│   ├── data_generator.py       # FIRMS-format data generator scoped to TATR
│   ├── pipeline.py             # Orchestration and GeoJSON exporter
│   ├── Procfile                # Gunicorn deployment configuration
│   ├── requirements.txt        # Backend dependencies
│   ├── data/
│   │   ├── raw/                # Detections and facility spatial registries
│   │   └── processed/          # Classified GeoJSON files and metrics
│   └── model/                  # Serialized classifier model (.pkl)
├── frontend/
│   ├── index.html              # Dispatch console interface
│   ├── style.css               # Operations center stylesheet (dark mode)
│   └── app.js                  # Map interactions, spread vectors, alert queue
└── README.md
