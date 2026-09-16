import json
import math
from sklearn.cluster import DBSCAN
import numpy as np


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def cluster_detections(detections, eps_km=1.5, min_samples=2):
    coords = np.radians([[d["latitude"], d["longitude"]] for d in detections])
    eps_rad = eps_km / 6371.0
    db = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine")
    labels = db.fit_predict(coords)

    for d, lab in zip(detections, labels):
        d["cluster_id"] = int(lab)

    clusters = {}
    for d in detections:
        cid = d["cluster_id"]
        if cid == -1:
            continue
        clusters.setdefault(cid, []).append(d)

    return clusters


def load_and_cluster(path="data/raw/firms_detections.json", eps_km=1.5, min_samples=2):
    with open(path) as f:
        payload = json.load(f)
    detections = payload["detections"]
    clusters = cluster_detections(detections, eps_km=eps_km, min_samples=min_samples)
    return clusters, payload["region"]


if __name__ == "__main__":
    clusters, region = load_and_cluster()
    print(f"Formed {len(clusters)} candidate hot zones from detections")
    sizes = sorted([len(v) for v in clusters.values()], reverse=True)
    print("Top cluster sizes:", sizes[:10])
