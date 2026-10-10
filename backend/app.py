import json
import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import pipeline
from data_generator import PRESET_REGIONS, DEFAULT_REGION

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

DATA_DIR = "data/processed"


def read_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        pipeline.run_pipeline(retrain=True)
    with open(path) as f:
        return json.load(f)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/hotzones")
def hotzones():
    return jsonify(read_json("classified_hotzones.geojson"))


@app.route("/api/facilities")
def facilities():
    return jsonify(read_json("facilities.geojson"))

@app.route("/api/boundaries", methods=["GET"])
def get_boundaries():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "data", "raw", "tatr_boundary.json"),
        os.path.join(base_dir, "..", "backend", "data", "raw", "tatr_boundary.json"),
        "data/raw/tatr_boundary.json",
        "backend/data/raw/tatr_boundary.json"
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r") as f:
                return jsonify(json.load(f))
    return jsonify({"type": "FeatureCollection", "features": []}), 200


@app.route("/api/summary")
def summary():
    return jsonify(read_json("summary.json"))


@app.route("/api/metrics")
def metrics():
    with open("model/metrics.json") as f:
        return jsonify(json.load(f))


@app.route("/api/rerun", methods=["POST"])
def rerun():
    geojson, summary_data = pipeline.run_pipeline(retrain=True)
    return jsonify({"status": "ok", "summary": summary_data})


@app.route("/api/regions")
def regions():
    return jsonify({
        "presets": [{"key": k, "name": v["name"], **v} for k, v in PRESET_REGIONS.items()],
    })


@app.route("/api/region", methods=["POST"])
def set_region():
    body = request.get_json(force=True, silent=True) or {}
    preset_key = body.get("preset")

    if preset_key:
        if preset_key not in PRESET_REGIONS:
            return jsonify({"status": "error", "message": f"Unknown preset '{preset_key}'"}), 400
        region = PRESET_REGIONS[preset_key]
    else:
        try:
            region = {
                "lat_min": float(body["lat_min"]),
                "lat_max": float(body["lat_max"]),
                "lon_min": float(body["lon_min"]),
                "lon_max": float(body["lon_max"]),
                "name": body.get("name") or "Custom region",
            }
        except (KeyError, TypeError, ValueError):
            return jsonify({"status": "error", "message": "Provide lat_min, lat_max, lon_min, lon_max (numbers) or a preset key."}), 400

        if region["lat_min"] >= region["lat_max"] or region["lon_min"] >= region["lon_max"]:
            return jsonify({"status": "error", "message": "lat_min/lon_min must be less than lat_max/lon_max."}), 400

    geojson, summary_data = pipeline.run_pipeline(retrain=True, region=region)
    return jsonify({"status": "ok", "summary": summary_data})


if __name__ == "__main__":
    if not os.path.exists(os.path.join(DATA_DIR, "classified_hotzones.geojson")):
        pipeline.run_pipeline(retrain=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
