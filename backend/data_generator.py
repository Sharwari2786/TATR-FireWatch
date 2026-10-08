import json
import random
import math
from datetime import datetime, timedelta

random.seed(42)

# Centered on Tadoba Andhari Tiger Reserve (TATR Core & Buffer Zone), Chandrapur, Maharashtra
DEFAULT_REGION = {
    "lat_min": 20.08, "lat_max": 20.48,
    "lon_min": 79.18, "lon_max": 79.62,
    "name": "Tadoba Andhari Tiger Reserve (TATR) & Buffer Zone"
}

PRESET_REGIONS = {
    "tatr_reserve": DEFAULT_REGION,
    "tatr_moharli_range": {
        "lat_min": 20.10, "lat_max": 20.25,
        "lon_min": 79.25, "lon_max": 79.40,
        "name": "TATR Moharli Southern Range",
    },
    "tatr_kolara_range": {
        "lat_min": 20.20, "lat_max": 20.40,
        "lon_min": 79.40, "lon_max": 79.60,
        "name": "TATR Kolara & Kolsa Eastern Corridor",
    },
    "chandrapur_belt": {
        "lat_min": 19.90, "lat_max": 20.45,
        "lon_min": 79.10, "lon_max": 79.65,
        "name": "Chandrapur District & Reserve Fringe",
    }
}

TATR_FACILITY_TYPES = {
    "ranger_hq": {"count": 2, "base_frp_range": (0, 0), "flicker": 0.0},
    "beat_outpost": {"count": 6, "base_frp_range": (0, 0), "flicker": 0.0},
    "watchtower": {"count": 4, "base_frp_range": (0, 0), "flicker": 0.0},
    "water_hole": {"count": 6, "base_frp_range": (0, 0), "flicker": 0.0},
    "fringe_mining_site": {"count": 2, "base_frp_range": (15, 35), "flicker": 0.25},
}

FOREST_CORE_ZONES = 8
BUFFER_ZONES = 10
AGRI_FRINGE_ZONES = 12


def rand_point(region):
    lat = random.uniform(region["lat_min"], region["lat_max"])
    lon = random.uniform(region["lon_min"], region["lon_max"])
    return round(lat, 5), round(lon, 5)


def jitter(lat, lon, meters=150):
    d = meters / 111320
    return round(lat + random.uniform(-d, d), 5), round(lon + random.uniform(-d, d), 5)


def generate_facilities(region):
    facilities = []
    fid = 1

    fixed_posts = [
        {"name": "Moharli Gate & Range HQ", "type": "ranger_hq", "lat": 20.1800, "lon": 79.3100},
        {"name": "Kolara Gate & Beat Post", "type": "beat_outpost", "lat": 20.1900, "lon": 79.4800},
        {"name": "Navegaon Gate Outpost", "type": "beat_outpost", "lat": 20.2580, "lon": 79.3830},
        {"name": "Khutwanda Beat Post", "type": "beat_outpost", "lat": 20.3100, "lon": 79.3500},
        {"name": "Kolsa Range Office", "type": "ranger_hq", "lat": 20.1200, "lon": 79.5200},
        {"name": "Tadoba Lake Main Watchtower", "type": "watchtower", "lat": 20.2450, "lon": 79.3900},
        {"name": "Erai Reservoir Observation Point", "type": "watchtower", "lat": 20.1350, "lon": 79.2300},
    ]

    for p in fixed_posts:
        facilities.append({
            "facility_id": f"F{fid:04d}",
            "name": p["name"],
            "type": p["type"],
            "latitude": p["lat"],
            "longitude": p["lon"],
            "source": "TATR Field Survey (synthetic)",
        })
        fid += 1

    for ftype, cfg in TATR_FACILITY_TYPES.items():
        if ftype in ["ranger_hq", "beat_outpost", "watchtower"]:
            continue
        for _ in range(cfg["count"]):
            lat, lon = rand_point(region)
            facilities.append({
                "facility_id": f"F{fid:04d}",
                "name": f"{ftype.replace('_', ' ').title()} {fid}",
                "type": ftype,
                "latitude": lat,
                "longitude": lon,
                "source": "Chandrapur Fringe Survey (synthetic)",
            })
            fid += 1
    return facilities


def generate_natural_zones(region):
    zones = []
    zid = 1

    for _ in range(FOREST_CORE_ZONES):
        lat, lon = rand_point(region)
        zones.append({
            "zone_id": f"FC{zid:03d}",
            "type": "core_forest",
            "latitude": lat,
            "longitude": lon,
            "landcover": "dense_forest",
            "radius_km": round(random.uniform(2, 5), 2)
        })
        zid += 1

    for _ in range(BUFFER_ZONES):
        lat, lon = rand_point(region)
        zones.append({
            "zone_id": f"BZ{zid:03d}",
            "type": "buffer_forest",
            "latitude": lat,
            "longitude": lon,
            "landcover": "dry_forest",
            "radius_km": round(random.uniform(1.5, 4), 2)
        })
        zid += 1

    for _ in range(AGRI_FRINGE_ZONES):
        lat, lon = rand_point(region)
        zones.append({
            "zone_id": f"AG{zid:03d}",
            "type": "cropland",
            "latitude": lat,
            "longitude": lon,
            "landcover": "cropland",
            "radius_km": round(random.uniform(1, 3), 2)
        })
        zid += 1

    return zones


def generate_firms_detections(facilities, natural_zones, days=30):
    detections = []
    det_id = 1
    start_date = datetime(2026, 8, 1)

    for f in facilities:
        if f["type"] == "fringe_mining_site":
            for day_idx in range(days):
                if random.random() > 0.4:
                    continue
                frp = round(random.uniform(15, 40), 1)
                lat, lon = jitter(f["latitude"], f["longitude"], meters=120)
                detections.append({
                    "detection_id": f"D{det_id:05d}",
                    "latitude": lat,
                    "longitude": lon,
                    "acq_date": (start_date + timedelta(days=day_idx)).strftime("%Y-%m-%d"),
                    "acq_time": f"{random.randint(0,23):02d}{random.randint(0,59):02d}",
                    "satellite": random.choice(["Terra", "Aqua", "NOAA-20", "Suomi-NPP"]),
                    "instrument": random.choice(["MODIS", "VIIRS"]),
                    "frp": frp,
                    "brightness": round(290 + frp * 1.4 + random.uniform(-4, 4), 1),
                    "bright_t31": round(272 + frp * 0.5 + random.uniform(-2, 2), 1),
                    "confidence": random.randint(70, 95),
                    "daynight": random.choice(["D", "N"]),
                    "true_label": "mining_site",
                    "facility_ref": f["facility_id"],
                })
                det_id += 1

    for z in natural_zones:
        zone_type = z["type"]
        if zone_type == "core_forest":
            n_events = random.randint(1, 3)
            peak_frp_range = (90, 280)
            true_label = "wildfire"
            spread_days = (2, 5)
        elif zone_type == "buffer_forest":
            n_events = random.randint(1, 4)
            peak_frp_range = (45, 140)
            true_label = "buffer_fire"
            spread_days = (1, 3)
        else:
            n_events = random.randint(2, 5)
            peak_frp_range = (15, 60)
            true_label = "agricultural_burn"
            spread_days = (1, 2)

        for _ in range(n_events):
            burst_day = random.randint(0, days - 6)
            burst_len = random.randint(*spread_days)
            peak_frp = random.uniform(*peak_frp_range)
            for k in range(burst_len):
                day_idx = burst_day + k
                if day_idx >= days:
                    continue
                decay = math.exp(-0.35 * k)
                lat, lon = jitter(z["latitude"], z["longitude"], meters=z["radius_km"] * 1000 * 0.4)
                frp = round(peak_frp * decay * random.uniform(0.8, 1.25), 1)

                detections.append({
                    "detection_id": f"D{det_id:05d}",
                    "latitude": lat,
                    "longitude": lon,
                    "acq_date": (start_date + timedelta(days=day_idx)).strftime("%Y-%m-%d"),
                    "acq_time": f"{random.randint(0,23):02d}{random.randint(0,59):02d}",
                    "satellite": random.choice(["Terra", "Aqua", "NOAA-20", "Suomi-NPP"]),
                    "instrument": random.choice(["MODIS", "VIIRS"]),
                    "frp": frp,
                    "brightness": round(300 + frp * 1.5 + random.uniform(-6, 6), 1),
                    "bright_t31": round(268 + frp * 0.4 + random.uniform(-3, 3), 1),
                    "confidence": random.randint(70, 100),
                    "daynight": random.choice(["D", "N"]),
                    "true_label": true_label,
                    "facility_ref": None,
                })
                det_id += 1

    return detections


def generate_landcover_fractions(lat, lon, true_label):
    profiles = {
        "wildfire": {"forest": 0.85, "bare": 0.08, "cropland": 0.05, "builtup": 0.02},
        "buffer_fire": {"forest": 0.65, "bare": 0.15, "cropland": 0.15, "builtup": 0.05},
        "agricultural_burn": {"cropland": 0.82, "forest": 0.08, "bare": 0.06, "builtup": 0.04},
        "mining_site": {"bare": 0.70, "builtup": 0.18, "forest": 0.08, "cropland": 0.04},
    }
    base = profiles.get(true_label, {"forest": 0.50, "bare": 0.20, "cropland": 0.20, "builtup": 0.10})
    noisy = {k: max(0, v + random.uniform(-0.04, 0.04)) for k, v in base.items()}
    total = sum(noisy.values())
    return {k: round(v / total, 3) for k, v in noisy.items()}


def main(region=None):
    region = region or DEFAULT_REGION
    facilities = generate_facilities(region)
    natural_zones = generate_natural_zones(region)
    detections = generate_firms_detections(facilities, natural_zones, days=30)

    for d in detections:
        d["landcover"] = generate_landcover_fractions(d["latitude"], d["longitude"], d["true_label"])

    with open("data/raw/facilities.json", "w") as f:
        json.dump({"region": region, "facilities": facilities}, f, indent=2)

    with open("data/raw/firms_detections.json", "w") as f:
        json.dump({"region": region, "detections": detections}, f, indent=2)

    with open("data/raw/natural_zones.json", "w") as f:
        json.dump({"zones": natural_zones}, f, indent=2)

    print(f"Monitoring Region: {region['name']}")
    print(f"TATR Outposts & Strategic Assets: {len(facilities)}")
    print(f"FIRMS Hotspot Detections: {len(detections)}")


if __name__ == "__main__":
    main()