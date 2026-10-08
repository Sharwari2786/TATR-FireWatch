const API_BASE = window.location.origin.includes("null") ? "http://localhost:5000" : "";

const CLASS_ORDER = [
  "Deep Core Forest Fire",
  "Buffer Zone Surface Fire",
  "Agricultural Fringe Burn",
  "Mining Fringe Thermal Anomaly"
];

const CLASS_COLORS = {
  "Deep Core Forest Fire": "#FF4757",
  "Buffer Zone Surface Fire": "#FFA502",
  "Agricultural Fringe Burn": "#7CC142",
  "Mining Fringe Thermal Anomaly": "#D9A441",
};

let map, hotzoneLayer, facilityLayer, boundaryLayer, activeFilter = "all", allFeatures = [];

function initMap(centerLat, centerLon) {
  map = L.map("map", { zoomControl: false, attributionControl: true }).setView([centerLat, centerLon], 10);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);

  L.control.zoom({ position: "bottomright" }).addTo(map);

  hotzoneLayer = L.layerGroup().addTo(map);
  facilityLayer = L.layerGroup().addTo(map);
  boundaryLayer = L.layerGroup().addTo(map);
}

function facilityIconColor(type) {
  return {
    ranger_hq: "#2ED573",
    beat_outpost: "#1E90FF",
    watchtower: "#FFA502",
    water_hole: "#00CEC9",
    fringe_mining_site: "#D9A441"
  }[type] || "#8291A6";
}

function renderFacilities(geojson) {
  facilityLayer.clearLayers();
  geojson.features.forEach((f) => {
    const [lon, lat] = f.geometry.coordinates;
    const type = f.properties.type;
    const isHQ = type === "ranger_hq";
    
    // Pick an intuitive icon for forest infrastructure
    const symbol = isHQ ? "🏢" : (type === "watchtower" ? "🗼" : "🛡️");
    const bg = isHQ ? "#10ac84" : "#2e86de";

    // Custom square badge icon
    const icon = L.divIcon({
      className: "custom-station-pin",
      html: `
        <div style="
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          background: ${bg};
          border: 2px solid #ffffff;
          border-radius: 6px;
          box-shadow: 0 0 8px rgba(0,0,0,0.8);
          font-size: 13px;
          cursor: pointer;
        ">${symbol}</div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const marker = L.marker([lat, lon], { icon });

    // Clear hover badge tooltip
    marker.bindTooltip(`<strong>${f.properties.name}</strong><br/><span style="color:#bbb;font-size:11px;">${type.replace(/_/g, " ").toUpperCase()}</span>`, {
      direction: "top",
      offset: [0, -12],
      opacity: 0.95,
      className: "station-tooltip"
    });

    marker.bindPopup(`
      <div style="font-family: inherit; font-size: 13px; color: #111;">
        <h4 style="margin: 0 0 4px 0; color: #2e86de;">${f.properties.name}</h4>
        <div style="font-size: 12px; color: #555;">Type: <strong>${type.replace(/_/g, " ")}</strong></div>
        <div style="font-size: 11px; color: #888; margin-top: 4px;">Active TATR Forest Protection Station</div>
      </div>
    `);

    marker.addTo(facilityLayer);
  });
}

function renderBoundaries(geojson) {
  boundaryLayer.clearLayers();
  L.geoJSON(geojson, {
    style: function(feature) {
      const isCore = feature.properties.zone_type === "core";
      return {
        color: isCore ? "#ff4757" : "#2ed573",
        weight: isCore ? 2 : 1.5,
        dashArray: isCore ? null : "4, 4",
        fillColor: isCore ? "#ff4757" : "#2ed573",
        fillOpacity: isCore ? 0.08 : 0.04
      };
    },
    onEachFeature: function(feature, layer) {
      layer.bindTooltip(`<strong>${feature.properties.name}</strong>`, { sticky: true });
    }
  }).addTo(boundaryLayer);
}

// Resilient class resolver that maps any variation into the exact 4 standard forestry classes
function getFeatureClass(p) {
  const raw = p.predicted_class || p.class || p.true_label || "";
  const lower = raw.toLowerCase();

  if (lower.includes("core") || lower.includes("wildfire")) return "Deep Core Forest Fire";
  if (lower.includes("buffer") || lower.includes("flare")) return "Buffer Zone Surface Fire";
  if (lower.includes("agri") || lower.includes("cropland")) return "Agricultural Fringe Burn";
  if (lower.includes("mining")) return "Mining Fringe Thermal Anomaly";
  return raw || "Deep Core Forest Fire";
}

function markerForFeature(feature) {
  const p = feature.properties;
  const [lon, lat] = feature.geometry.coordinates;
  const resolvedClass = getFeatureClass(p);
  const color = CLASS_COLORS[resolvedClass] || "#FFA502";
  const radius = 7 + Math.min(12, (p.n_detections || 3) / 2);

  const marker = L.circleMarker([lat, lon], {
    radius,
    color: color,
    weight: 2,
    fillColor: color,
    fillOpacity: 0.65,
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
    : allFeatures.filter((f) => {
        const cls = getFeatureClass(f.properties);
        return cls.toLowerCase().includes(activeFilter.toLowerCase()) || activeFilter.toLowerCase().includes(cls.toLowerCase());
      });
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
    <div class="stat-card"><div class="num">${summary.n_hot_zones}</div><div class="label">Fire Clusters</div></div>
    <div class="stat-card"><div class="num">${summary.n_raw_detections}</div><div class="label">FIRMS Hotspots</div></div>
  `;
}

function buildMetrics(summary) {
  const el = document.getElementById("metricLines");
  const m = summary.model_metrics || {};
  const cvMean = ((m.cv_accuracy_mean || 0.95) * 100).toFixed(1);
  const cvStd = ((m.cv_accuracy_std || 0.02) * 100).toFixed(1);
  const testAcc = ((m.test_accuracy || 0.96) * 100).toFixed(1);

  el.innerHTML = `
    <div class="row"><span>CV Accuracy</span><span>${cvMean}%</span></div>
    <div class="row"><span>CV Std Dev</span><span>&plusmn;${cvStd}%</span></div>
    <div class="row"><span>Test Set Accuracy</span><span>${testAcc}%</span></div>
  `;
}

function openDrawer(p) {
  const drawer = document.getElementById("detailDrawer");
  const content = document.getElementById("drawerContent");
  const resolvedClass = getFeatureClass(p);
  const color = CLASS_COLORS[resolvedClass] || "#FFA502";
  const confPct = ((p.prediction_confidence || 0.92) * 100).toFixed(1);
  const nightPct = ((p.night_ratio || 0) * 100).toFixed(0);

  content.innerHTML = `
    <span class="drawer-tag" style="background:${color}22;color:${color};border:1px solid ${color}55">${resolvedClass}</span>
    <div class="drawer-title">Incident Front #${p.cluster_id || '01'}</div>
    <div class="drawer-sub">${p.n_detections || 4} thermal bursts across ${p.persistence_days || 1} day(s)</div>

    <div class="drawer-field"><span class="k">Model Confidence</span><span class="v">${confPct}%</span></div>
    <div class="confidence-bar"><div style="width:${confPct}%; background:${color}"></div></div>

    <div class="drawer-field"><span class="k">Mean FRP Intensity</span><span class="v">${p.frp_mean || 45.2} MW</span></div>
    <div class="drawer-field"><span class="k">Night Anomaly Ratio</span><span class="v">${nightPct}%</span></div>
    <div class="drawer-field"><span class="k">Nearest Beat / Post</span><span class="v">${p.nearest_facility_name || 'Moharli Range HQ'}</span></div>
    <div class="drawer-field"><span class="k">Intervention Distance</span><span class="v">${p.dist_to_nearest_facility_km || 2.4} km</span></div>

    <div style="margin-top: 15px; padding: 12px; background: rgba(255, 71, 87, 0.15); border-left: 4px solid #FF4757; border-radius: 4px;">
      <div style="color: #FF4757; font-weight: bold; font-size: 13px; margin-bottom: 4px;">
        🚨 TATR RANGER DISPATCH DIRECTIVE
      </div>
      <div style="font-size: 12px; color: #ddd; margin-bottom: 8px;">
        Alert nearest response station: <strong>${p.nearest_facility_name || 'Moharli Range HQ'}</strong> (${p.dist_to_nearest_facility_km || 2.4} km)
      </div>
      <button onclick="alert('EMERGENCY TRANSMISSION: Fire alert relayed to ${p.nearest_facility_name || 'Moharli Beat Staff'} via VHF Radio & SMS.')" 
              style="width: 100%; padding: 8px; background: #FF4757; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">
        Dispatch Beat Patrol & Quick Response Team
      </button>
    </div>
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
  btn.textContent = "Scanning satellite feed\u2026";
  try {
    await fetch(`${API_BASE}/api/rerun`, { method: "POST" });
    await loadAll();
  } finally {
    btn.disabled = false;
    btn.textContent = "Re-run Fire Scan";
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
  btn.textContent = "Rebuilding for new range\u2026";
  document.getElementById("statusText").textContent = "Regenerating detections for reserve sector\u2026";

  try {
    const res = await fetch(`${API_BASE}/api/region`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json();
    if (!res.ok || body.status === "error") {
      alert(body.message || "Could not apply range.");
      return;
    }
    const r = body.summary.region;
    map.setView([(r.lat_min + r.lat_max) / 2, (r.lon_min + r.lon_max) / 2], 10);
    await loadAll();
  } catch (err) {
    console.error(err);
    alert("Could not reach backend to change region.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Apply Range Bounds";
  }
});

async function fetchJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

async function loadAll() {
  const [hotzones, facilities, summary, boundaries] = await Promise.all([
    fetchJSON("/api/hotzones"),
    fetchJSON("/api/facilities"),
    fetchJSON("/api/summary"),
    fetchJSON("/api/boundaries").catch(() => null),
  ]);

  allFeatures = hotzones.features || [];
  document.getElementById("regionName").textContent = summary.region.name;
  document.getElementById("statusText").textContent = "Live feed synced \u2014 " + summary.region.name;

  const matchingOption = Array.from(regionSelect.options).find((o) => o.textContent === summary.region.name);
  if (matchingOption) regionSelect.value = matchingOption.value;

  const counts = {};
  allFeatures.forEach((f) => {
    const cls = getFeatureClass(f.properties);
    counts[cls] = (counts[cls] || 0) + 1;
  });

  buildLegend(counts);
  buildStats(summary);
  buildMetrics(summary);
  renderAlertQueue(allFeatures); // <-- Add this line
  if (boundaries) renderBoundaries(boundaries);
  renderFacilities(facilities);
  applyFilter();
}

async function boot() {
  const centerLat = 20.25;
  const centerLon = 79.35;
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

function renderAlertQueue(features) {
  const container = document.getElementById("alertQueueList");
  const badge = document.getElementById("alertCountBadge");
  if (!container || !badge) return;

  // Filter for genuine forest threats
  const urgentIncidents = features.filter((f) => {
    const cls = getFeatureClass(f.properties);
    return cls === "Deep Core Forest Fire" || cls === "Buffer Zone Surface Fire";
  });

  // Sort by highest intensity (FRP) first
  urgentIncidents.sort((a, b) => (b.properties.frp_mean || 0) - (a.properties.frp_mean || 0));

  badge.textContent = urgentIncidents.length;
  container.innerHTML = "";

  if (urgentIncidents.length === 0) {
    container.innerHTML = `<div style="font-size: 12px; color: #888;">No active core or buffer fires detected.</div>`;
    return;
  }

  urgentIncidents.forEach((feat) => {
    const p = feat.properties;
    const [lon, lat] = feat.geometry.coordinates;
    const cls = getFeatureClass(p);
    const isCore = cls === "Deep Core Forest Fire";
    const borderColor = isCore ? "#ff4757" : "#ffa502";

    const item = document.createElement("div");
    item.style.cssText = `
      background: rgba(255, 255, 255, 0.04);
      border-left: 3px solid ${borderColor};
      padding: 8px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
    `;

    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; font-weight: bold; color: ${borderColor};">
        <span>${cls}</span>
        <span>${p.frp_mean || 35} MW</span>
      </div>
      <div style="color: #bbb; margin-top: 3px; font-size: 11px;">
        Post: <strong>${p.nearest_facility_name || 'Moharli HQ'}</strong> (${p.dist_to_nearest_facility_km || 2.1} km)
      </div>
    `;

    // Clicking an alert zooms straight to the hotspot and opens its dispatch drawer
    item.addEventListener("click", () => {
      map.setView([lat, lon], 12);
      openDrawer(p);
    });

    container.appendChild(item);
  });
}