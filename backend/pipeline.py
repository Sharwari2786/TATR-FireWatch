import json
import os
import data_generator
from clustering import load_and_cluster
from feature_engineering import load_facilities, build_cluster_features
from classifier import train, predict_rows, load_model

CLASS_COLORS = {
    "Industrial Fire": "#FF6B35",
    "Flare": "#4FD1C5",
    "Mining Activity": "#C9A227",
    "Agricultural Burn": "#7CB342",
    "Wildfire": "#FF3B30",
}


def ensure_raw_data(region=None, force=False):
    if force or not os.path.exists("data/raw/firms_detections.json"):
        data_generator.main(region=region)


def run_pipeline(retrain=True, region=None, force_regenerate=False):
    ensure_raw_data(region=region, force=(region is not None or force_regenerate))

    clusters, region = load_and_cluster()
    facilities = load_facilities()
    rows = build_cluster_features(clusters, facilities)

    with open("data/processed/cluster_features.json", "w") as f:
        json.dump({"region": region, "clusters": rows}, f, indent=2)

    if retrain or not os.path.exists("model/classifier.pkl"):
        clf, le, metrics = train(rows)
    else:
        clf, le = load_model()
        with open("model/metrics.json") as f:
            metrics = json.load(f)

    predicted = predict_rows(rows, clf, le)

    features = []
    for r in predicted:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["longitude"], r["latitude"]]},
            "properties": {
                "cluster_id": r["cluster_id"],
                "predicted_class": r["predicted_class"],
                "confidence": r["prediction_confidence"],
                "color": CLASS_COLORS.get(r["predicted_class"], "#999999"),
                "n_detections": r["n_detections"],
                "persistence_days": r["persistence_days"],
                "frp_mean": r["frp_mean"],
                "night_ratio": r["night_ratio"],
                "nearest_facility_type": r["nearest_facility_type"],
                "nearest_facility_name": r["nearest_facility_name"],
                "dist_to_nearest_facility_km": r["dist_to_nearest_facility_km"],
                "true_label_for_demo": r["true_label"],
            },
        })

    geojson = {"type": "FeatureCollection", "region": region, "features": features}
    with open("data/processed/classified_hotzones.geojson", "w") as f:
        json.dump(geojson, f, indent=2)

    with open("data/raw/facilities.json") as f:
        fac_payload = json.load(f)
    facility_features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [fa["longitude"], fa["latitude"]]},
        "properties": {"name": fa["name"], "type": fa["type"], "facility_id": fa["facility_id"]},
    } for fa in fac_payload["facilities"]]
    with open("data/processed/facilities.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": facility_features}, f, indent=2)

    class_counts = {}
    for r in predicted:
        class_counts[r["predicted_class"]] = class_counts.get(r["predicted_class"], 0) + 1

    summary = {
        "region": region,
        "n_hot_zones": len(predicted),
        "n_raw_detections": sum(r["n_detections"] for r in predicted),
        "class_counts": class_counts,
        "model_metrics": {
            "cv_accuracy_mean": metrics["cv_accuracy_mean"],
            "cv_accuracy_std": metrics["cv_accuracy_std"],
            "test_accuracy": metrics["test_accuracy"],
        },
    }
    with open("data/processed/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    return geojson, summary


if __name__ == "__main__":
    run_pipeline(retrain=True)
