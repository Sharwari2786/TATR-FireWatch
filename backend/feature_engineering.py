import json
import random
import statistics as stats
from clustering import haversine_km, load_and_cluster


def load_facilities(path="data/raw/facilities.json"):
    with open(path) as f:
        return json.load(f)["facilities"]


def nearest_facility(lat, lon, facilities):
    best, best_d = None, float("inf")
    for f in facilities:
        d = haversine_km(lat, lon, f["latitude"], f["longitude"])
        if d < best_d:
            best_d, best = d, f
    return best, best_d


def centroid(points):
    lat = sum(p["latitude"] for p in points) / len(points)
    lon = sum(p["longitude"] for p in points) / len(points)
    return lat, lon


def majority_landcover(points):
    agg = {"builtup": 0.0, "bare": 0.0, "cropland": 0.0, "forest": 0.0}
    for p in points:
        for k, v in p["landcover"].items():
            agg[k] += v
    n = len(points)
    return {k: round(v / n, 3) for k, v in agg.items()}


def majority_label(points):
    counts = {}
    for p in points:
        counts[p["true_label"]] = counts.get(p["true_label"], 0) + 1
    return max(counts, key=counts.get)


def build_cluster_features(clusters, facilities, window_days=30):
    rows = []
    for cid, points in clusters.items():
        lat, lon = centroid(points)
        frps = [p["frp"] for p in points]
        dates = sorted(set(p["acq_date"] for p in points))
        persistence_days = len(dates)
        persistence_ratio = round(persistence_days / window_days, 3)

        day_count = sum(1 for p in points if p["daynight"] == "D")
        night_count = len(points) - day_count
        night_ratio = round(night_count / len(points), 3)

        frp_mean = round(stats.mean(frps), 2)
        frp_std = round(stats.pstdev(frps), 2) if len(frps) > 1 else 0.0
        frp_cv = round(frp_std / frp_mean, 3) if frp_mean > 0 else 0.0

        bright_t31_mean = round(stats.mean(p["bright_t31"] for p in points), 2)
        conf_mean = round(stats.mean(p["confidence"] for p in points), 2)

        nf, dist_km = nearest_facility(lat, lon, facilities)
        landcover = majority_landcover(points)

        # Sensor/geolocation uncertainty and real-world ambiguity: jitter derived
        # features so classes are not perfectly separable, as in real satellite data.
        frp_mean *= random.uniform(0.88, 1.12)
        frp_cv *= random.uniform(0.85, 1.2)
        persistence_ratio = min(1.0, max(0.0, persistence_ratio + random.uniform(-0.07, 0.07)))
        night_ratio = min(1.0, max(0.0, night_ratio + random.uniform(-0.06, 0.06)))
        if majority_label(points) in ("wildfire", "agricultural_burn") and random.random() < 0.18:
            dist_km = max(0.1, dist_km * random.uniform(0.15, 0.5))
        if majority_label(points) == "mining_site" and random.random() < 0.25:
            dist_km *= random.uniform(1.5, 3.0)

        rows.append({
            "cluster_id": cid,
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "n_detections": len(points),
            "persistence_days": persistence_days,
            "persistence_ratio": persistence_ratio,
            "night_ratio": night_ratio,
            "frp_mean": round(frp_mean, 2),
            "frp_std": frp_std,
            "frp_cv": round(frp_cv, 3),
            "bright_t31_mean": bright_t31_mean,
            "confidence_mean": conf_mean,
            "dist_to_nearest_facility_km": round(dist_km, 3),
            "nearest_facility_type": nf["type"] if nf else "none",
            "nearest_facility_name": nf["name"] if nf else "none",
            "builtup_frac": landcover["builtup"],
            "bare_frac": landcover["bare"],
            "cropland_frac": landcover["cropland"],
            "forest_frac": landcover["forest"],
            "true_label": majority_label(points),
        })
    return rows


FEATURE_COLUMNS = [
    "n_detections", "persistence_days", "persistence_ratio", "night_ratio",
    "frp_mean", "frp_std", "frp_cv", "bright_t31_mean", "confidence_mean",
    "dist_to_nearest_facility_km", "builtup_frac", "bare_frac", "cropland_frac", "forest_frac",
]


def main():
    clusters, region = load_and_cluster()
    facilities = load_facilities()
    rows = build_cluster_features(clusters, facilities)
    with open("data/processed/cluster_features.json", "w") as f:
        json.dump({"region": region, "clusters": rows}, f, indent=2)
    print(f"Built features for {len(rows)} candidate hot zones")
    return rows


if __name__ == "__main__":
    main()
