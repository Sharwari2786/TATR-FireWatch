import json
import random
import math
from datetime import datetime, timedelta

random.seed(42)

DEFAULT_REGION = {
    "lat_min": 18.5, "lat_max": 24.5,
    "lon_min": 72.5, "lon_max": 80.5,
    "name": "Maharashtra Industrial Belt, India"
}

PRESET_REGIONS = {
    "maharashtra": DEFAULT_REGION,
    "jamshedpur": {
        "lat_min": 22.5, "lat_max": 23.1, "lon_min": 85.8, "lon_max": 86.5,
        "name": "Jamshedpur Steel Belt, India",
    },
    "jamnagar": {
        "lat_min": 22.0, "lat_max": 22.7, "lon_min": 69.6, "lon_max": 70.3,
        "name": "Jamnagar-Vadodara Refinery Corridor, India",
    },
    "dhanbad": {
        "lat_min": 23.5, "lat_max": 24.1, "lon_min": 86.1, "lon_max": 86.8,
        "name": "Dhanbad-Jharia Coalfields, India",
    },
    "ncr": {
        "lat_min": 28.2, "lat_max": 28.9, "lon_min": 76.8, "lon_max": 77.6,
        "name": "National Capital Region, India",
    },
}

FACILITY_TYPES = {
    "refinery": {"count": 4, "base_frp_range": (60, 140), "flicker": 0.05},
    "power_plant": {"count": 8, "base_frp_range": (40, 100), "flicker": 0.08},
    "steel_plant": {"count": 5, "base_frp_range": (50, 110), "flicker": 0.10},
    "gas_flare": {"count": 10, "base_frp_range": (15, 45), "flicker": 0.03},
    "mining_site": {"count": 6, "base_frp_range": (10, 35), "flicker": 0.30},
}

WILDFIRE_ZONES = 12
AGRI_ZONES = 15


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
    for ftype, cfg in FACILITY_TYPES.items():
        for _ in range(cfg["count"]):
            lat, lon = rand_point(region)
            facilities.append({
                "facility_id": f"F{fid:04d}",
                "name": f"{ftype.replace('_', ' ').title()} {fid}",
                "type": ftype,
                "latitude": lat,
                "longitude": lon,
                "source": "Global Power Plant DB / Global Gas Flaring Dataset / OSM (synthetic)",
            })
            fid += 1
    return facilities


def generate_natural_zones(region):
    zones = []
    for i in range(WILDFIRE_ZONES):
        lat, lon = rand_point(region)
        zones.append({"zone_id": f"WF{i+1:03d}", "type": "forest", "latitude": lat, "longitude": lon,
                       "landcover": "forest", "radius_km": round(random.uniform(2, 8), 2)})
    for i in range(AGRI_ZONES):
        lat, lon = rand_point(region)
        zones.append({"zone_id": f"AG{i+1:03d}", "type": "cropland", "latitude": lat, "longitude": lon,
                       "landcover": "cropland", "radius_km": round(random.uniform(1, 5), 2)})
    return zones


def frp_series(base_low, base_high, flicker, days, persistent=True):
    base = random.uniform(base_low, base_high)
    series = []
    for d in range(days):
        if persistent:
            val = max(0, base * (1 + random.uniform(-flicker, flicker)))
            active = random.random() > 0.02
        else:
            active = random.random() > 0.6
            val = base * random.uniform(0.7, 1.4) if active else 0
        series.append(round(val, 1) if active else 0.0)
    return series


def generate_firms_detections(facilities, natural_zones, days=30):
    detections = []
    det_id = 1
    start_date = datetime(2026, 8, 1)

    for f in facilities:
        cfg = FACILITY_TYPES[f["type"]]
        series = frp_series(*cfg["base_frp_range"], cfg["flicker"], days, persistent=True)
        for day_idx, frp in enumerate(series):
            if frp <= 0:
                continue
            lat, lon = jitter(f["latitude"], f["longitude"], meters=80)
            detections.append({
                "detection_id": f"D{det_id:05d}",
                "latitude": lat,
                "longitude": lon,
                "acq_date": (start_date + timedelta(days=day_idx)).strftime("%Y-%m-%d"),
                "acq_time": f"{random.randint(0,23):02d}{random.randint(0,59):02d}",
                "satellite": random.choice(["Terra", "Aqua", "NOAA-20", "Suomi-NPP"]),
                "instrument": random.choice(["MODIS", "VIIRS"]),
                "frp": frp,
                "brightness": round(280 + frp * 1.8 + random.uniform(-5, 5), 1),
                "bright_t31": round(270 + frp * 0.6 + random.uniform(-3, 3), 1),
                "confidence": random.randint(75, 100),
                "daynight": random.choice(["D", "N"]),
                "true_label": f["type"],
                "facility_ref": f["facility_id"],
            })
            det_id += 1

    for z in natural_zones:
        is_wildfire = z["type"] == "forest"
        n_events = random.randint(1, 3) if is_wildfire else random.randint(2, 6)
        for _ in range(n_events):
            burst_day = random.randint(0, days - 5)
            burst_len = random.randint(1, 4) if is_wildfire else random.randint(1, 2)
            peak_frp = random.uniform(80, 260) if is_wildfire else random.uniform(20, 70)
            for k in range(burst_len):
                day_idx = burst_day + k
                if day_idx >= days:
                    continue
                decay = math.exp(-0.5 * k)
                lat, lon = jitter(z["latitude"], z["longitude"], meters=z["radius_km"] * 1000 * 0.4)
                frp = round(peak_frp * decay * random.uniform(0.8, 1.2), 1)
                detections.append({
                    "detection_id": f"D{det_id:05d}",
                    "latitude": lat,
                    "longitude": lon,
                    "acq_date": (start_date + timedelta(days=day_idx)).strftime("%Y-%m-%d"),
                    "acq_time": f"{random.randint(0,23):02d}{random.randint(0,59):02d}",
                    "satellite": random.choice(["Terra", "Aqua", "NOAA-20", "Suomi-NPP"]),
                    "instrument": random.choice(["MODIS", "VIIRS"]),
                    "frp": frp,
                    "brightness": round(300 + frp * 1.5 + random.uniform(-8, 8), 1),
                    "bright_t31": round(265 + frp * 0.4 + random.uniform(-4, 4), 1),
                    "confidence": random.randint(60, 100),
                    "daynight": random.choice(["D", "N"]),
                    "true_label": "wildfire" if is_wildfire else "agricultural_burn",
                    "facility_ref": None,
                })
                det_id += 1

    return detections


def generate_landcover_fractions(lat, lon, true_label):
    profiles = {
        "refinery": {"builtup": 0.75, "bare": 0.15, "cropland": 0.05, "forest": 0.05},
        "power_plant": {"builtup": 0.70, "bare": 0.15, "cropland": 0.10, "forest": 0.05},
        "steel_plant": {"builtup": 0.80, "bare": 0.10, "cropland": 0.05, "forest": 0.05},
        "gas_flare": {"builtup": 0.30, "bare": 0.55, "cropland": 0.10, "forest": 0.05},
        "mining_site": {"builtup": 0.10, "bare": 0.75, "cropland": 0.05, "forest": 0.10},
        "wildfire": {"builtup": 0.02, "bare": 0.08, "cropland": 0.10, "forest": 0.80},
        "agricultural_burn": {"builtup": 0.05, "bare": 0.10, "cropland": 0.80, "forest": 0.05},
    }
    base = profiles.get(true_label, {"builtup": 0.25, "bare": 0.25, "cropland": 0.25, "forest": 0.25})
    noisy = {k: max(0, v + random.uniform(-0.05, 0.05)) for k, v in base.items()}
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

    print(f"Region: {region['name']}")
    print(f"Facilities: {len(facilities)}")
    print(f"FIRMS-style detections: {len(detections)}")
    print(f"Natural zones: {len(natural_zones)}")


if __name__ == "__main__":
    main()
