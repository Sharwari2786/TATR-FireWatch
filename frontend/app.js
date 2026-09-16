const API_BASE = window.location.origin.includes("null") ? "http://localhost:5000" : "";

const CLASS_ORDER = ["Industrial Fire", "Flare", "Mining Activity", "Agricultural Burn", "Wildfire"];
const CLASS_COLORS = {
  "Industrial Fire": "#FF6B35",
  "Flare": "#45D9C0",
  "Mining Activity": "#D9A441",
  "Agricultural Burn": "#7CC142",
  "Wildfire": "#FF4757",
};

let map, hotzoneLayer, facilityLayer, activeFilter = "all", allFeatures = [];

function initMap(centerLat, centerLon) {
  map = L.map("map", { zoomControl: false, attributionControl: true }).setView([centerLat, centerLon], 7);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);

  L.control.zoom({ position: "bottomright" }).addTo(map);

  hotzoneLayer = L.layerGroup().addTo(map);
  facilityLayer = L.layerGroup().addTo(map);
}

function facilityIconColor(type) {
  return { refinery: "#FF6B35", power_plant: "#4FA0FF", steel_plant: "#B58CFF",
           gas_flare: "#45D9C0", mining_site: "#D9A441" }[type] || "#8291A6";
}

function renderFacilities(geojson) {
  facilityLayer.clearLayers();
  geojson.features.forEach((f) => {
    const [lon, lat] = f.geometry.coordinates;
    const marker = L.circleMarker([lat, lon], {
      radius: 4,
      color: facilityIconColor(f.properties.type),
      weight: 1.5,
      fillOpacity: 0.15,
      opacity: 0.7,
    });
    marker.bindPopup(`<strong>${f.properties.name}</strong><br/>${f.properties.type.replace("_", " ")}`);
    marker.addTo(facilityLayer);
  });
}

function markerForFeature(feature) {
  const p = feature.properties;
  const [lon, lat] = feature.geometry.coordinates;
  const color = CLASS_COLORS[p.predicted_class] || "#8291A6";
  const radius = 6 + Math.min(10, p.n_detections / 3);

  const marker = L.circleMarker([lat, lon], {
    radius,
    color,
    weight: 2,
    fillColor: color,
    fillOpacity: 0.35,
  });

  marker.on("click", () => openDrawer(p));
  return marker;
}

function renderHotzones(features) {
  hotzoneLayer.clearLayers();
  features.forEach((f) => markerForFeature(f).addTo(hotzoneLayer));
}

function applyFilter() {
  const filtered = activeFilter === "all"
    ? allFeatures
    : allFeatures.filter((f) => f.properties.predicted_class === activeFilter);
  renderHotzones(filtered);
}

function buildLegend(classCounts) {
  const ul = document.getElementById("legendList");
  ul.innerHTML = "";
  CLASS_ORDER.forEach((cls) => {
    const li = document.createElement("li");
    const count = classCounts[cls] || 0;
    li.innerHTML = `<span class="swatch" style="background:${CLASS_COLORS[cls]}"></span>${cls}<span class="count">${count}</span>`;
    ul.appendChild(li);
  });
}

function buildStats(summary) {
  const grid = document.getElementById("statGrid");
  grid.innerHTML = `
    <div class="stat-card"><div class="num">${summary.n_hot_zones}</div><div class="label">Hot zones</div></div>
    <div class="stat-card"><div class="num">${summary.n_raw_detections}</div><div class="label">Raw detections</div></div>
  `;
}

function buildMetrics(summary) {
  const el = document.getElementById("metricLines");
  const m = summary.model_metrics;
  el.innerHTML = `
    <div class="row"><span>CV accuracy</span><span>${(m.cv_accuracy_mean * 100).toFixed(1)}%</span></div>
    <div class="row"><span>CV std dev</span><span>&plusmn;${(m.cv_accuracy_std * 100).toFixed(1)}%</span></div>
    <div class="row"><span>Held-out accuracy</span><span>${(m.test_accuracy * 100).toFixed(1)}%</span></div>
  `;
}

function openDrawer(p) {
  const drawer = document.getElementById("detailDrawer");
  const content = document.getElementById("drawerContent");
  const color = CLASS_COLORS[p.predicted_class] || "#8291A6";

  content.innerHTML = `
    <span class="drawer-tag" style="background:${color}22;color:${color};border:1px solid ${color}55">${p.predicted_class}</span>
    <div class="drawer-title">Hot zone #${p.cluster_id}</div>
    <div class="drawer-sub">${p.n_detections} detections over ${p.persistence_days} day(s)</div>

    <div class="drawer-field"><span class="k">Prediction confidence</span><span class="v">${(p.confidence * 100).toFixed(1)}%</span></div>
    <div class="confidence-bar"><div style="width:${p.confidence * 100}%; background:${color}"></div></div>

    <div class="drawer-field"><span class="k">Mean FRP</span><span class="v">${p.frp_mean} MW</span></div>
    <div class="drawer-field"><span class="k">Night-detection ratio</span><span class="v">${(p.night_ratio * 100).toFixed(0)}%</span></div>
    <div class="drawer-field"><span class="k">Nearest facility</span><span class="v">${p.nearest_facility_name}</span></div>
    <div class="drawer-field"><span class="k">Facility type</span><span class="v">${p.nearest_facility_type.replace("_", " ")}</span></div>
    <div class="drawer-field"><span class="k">Distance to facility</span><span class="v">${p.dist_to_nearest_facility_km} km</span></div>
  `;
  drawer.classList.add("open");
}

document.getElementById("drawerClose").addEventListener("click", () => {
  document.getElementById("detailDrawer").classList.remove("open");
});

document.querySelectorAll(".filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    activeFilter = chip.dataset.filter;
    applyFilter();
  });
});

document.getElementById("facilityToggle").addEventListener("change", (e) => {
  if (e.target.checked) facilityLayer.addTo(map);
  else map.removeLayer(facilityLayer);
});

document.getElementById("sidebarToggle").addEventListener("click", () => {
  document.getElementById("sidebar").classList.add("open");
});
document.getElementById("sidebarClose").addEventListener("click", () => {
  document.getElementById("sidebar").classList.remove("open");
});

document.getElementById("rerunBtn").addEventListener("click", async () => {
  const btn = document.getElementById("rerunBtn");
  btn.disabled = true;
  btn.textContent = "Re-running pipeline\u2026";
  try {
    await fetch(`${API_BASE}/api/rerun`, { method: "POST" });
    await loadAll();
  } finally {
    btn.disabled = false;
    btn.textContent = "Re-run classification";
  }
});

const regionSelect = document.getElementById("regionSelect");
const customBounds = document.getElementById("customBounds");

regionSelect.addEventListener("change", () => {
  customBounds.classList.toggle("open", regionSelect.value === "__custom__");
});

async function loadRegionPresets() {
  const data = await fetchJSON("/api/regions");
  regionSelect.innerHTML = "";
  data.presets.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.key;
    opt.textContent = p.name;
    regionSelect.appendChild(opt);
  });
  const customOpt = document.createElement("option");
  customOpt.value = "__custom__";
  customOpt.textContent = "Custom bounds\u2026";
  regionSelect.appendChild(customOpt);
}

document.getElementById("applyRegionBtn").addEventListener("click", async () => {
  const btn = document.getElementById("applyRegionBtn");
  const choice = regionSelect.value;
  let payload;

  if (choice === "__custom__") {
    const latMin = parseFloat(document.getElementById("latMin").value);
    const latMax = parseFloat(document.getElementById("latMax").value);
    const lonMin = parseFloat(document.getElementById("lonMin").value);
    const lonMax = parseFloat(document.getElementById("lonMax").value);
    const name = document.getElementById("customName").value;

    if ([latMin, latMax, lonMin, lonMax].some((v) => Number.isNaN(v)) || latMin >= latMax || lonMin >= lonMax) {
      alert("Enter valid bounds: lat min < lat max, lon min < lon max.");
      return;
    }
    payload = { lat_min: latMin, lat_max: latMax, lon_min: lonMin, lon_max: lonMax, name };
  } else {
    payload = { preset: choice };
  }

  btn.disabled = true;
  btn.textContent = "Rebuilding for new region\u2026";
  document.getElementById("statusText").textContent = "Regenerating detections for new region\u2026";

  try {
    const res = await fetch(`${API_BASE}/api/region`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json();
    if (!res.ok || body.status === "error") {
      alert(body.message || "Could not apply that region.");
      return;
    }
    const r = body.summary.region;
    map.setView([(r.lat_min + r.lat_max) / 2, (r.lon_min + r.lon_max) / 2], regionZoom(r));
    await loadAll();
  } catch (err) {
    console.error(err);
    alert("Could not reach the backend to change region.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Apply region";
  }
});

function regionZoom(r) {
  const span = Math.max(r.lat_max - r.lat_min, r.lon_max - r.lon_min);
  if (span > 4) return 6;
  if (span > 1.5) return 8;
  return 10;
}

async function fetchJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

async function loadAll() {
  const [hotzones, facilities, summary] = await Promise.all([
    fetchJSON("/api/hotzones"),
    fetchJSON("/api/facilities"),
    fetchJSON("/api/summary"),
  ]);

  allFeatures = hotzones.features;
  document.getElementById("regionName").textContent = summary.region.name;
  document.getElementById("statusText").textContent = "Live feed synced \u2014 " + summary.region.name;

  const matchingOption = Array.from(regionSelect.options).find((o) => o.textContent === summary.region.name);
  if (matchingOption) regionSelect.value = matchingOption.value;

  buildLegend(summary.class_counts);
  buildStats(summary);
  buildMetrics(summary);
  renderFacilities(facilities);
  applyFilter();
}

async function boot() {
  const centerLat = (18.5 + 24.5) / 2;
  const centerLon = (72.5 + 80.5) / 2;
  initMap(centerLat, centerLon);

  try {
    await loadRegionPresets();
    await loadAll();
  } catch (err) {
    document.getElementById("statusText").textContent = "Connection error \u2014 is the backend running?";
    console.error(err);
  }

  document.getElementById("loadingVeil").classList.add("hidden");
}

boot();
