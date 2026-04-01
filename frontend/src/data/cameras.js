// ─── Terrain clusters ─────────────────────────────────────────────────────
// Each cluster anchors generated cameras to real wildfire-prone terrain.
// risk: 0.4–0.95 — drives weighted random selection for fire events.

const CAMERA_CLUSTERS = [
  { name: "Sierra Nevada",      lat: 37.5,  lng: -119.5, risk: 0.75 },
  { name: "East Bay Hills",     lat: 37.8,  lng: -121.9, risk: 0.70 },
  { name: "Central Valley",     lat: 36.5,  lng: -119.5, risk: 0.52 },
  { name: "SoCal Inland",       lat: 34.0,  lng: -117.0, risk: 0.90 },
  { name: "San Diego Hills",    lat: 33.3,  lng: -116.8, risk: 0.85 },
  { name: "Northern California",lat: 40.5,  lng: -122.5, risk: 0.65 },
];

// Weighted cluster picker — high-risk clusters selected more often
function pickWeightedCluster() {
  const total = CAMERA_CLUSTERS.reduce((sum, c) => sum + c.risk, 0);
  let rand = Math.random() * total;
  for (const cluster of CAMERA_CLUSTERS) {
    rand -= cluster.risk;
    if (rand <= 0) return cluster;
  }
  return CAMERA_CLUSTERS[CAMERA_CLUSTERS.length - 1];
}

// ─── Named anchor cameras ─────────────────────────────────────────────────
// These are the 5 hand-placed real-world reference cameras shown in the UI.

const BASE_CAMERAS = [
  { id: 1, name: "Bear Mountain",    lat: 37.2382, lng: -119.0000, sector: "Sierra NE-4",   region: "Sierra Nevada",       risk: 0.72 },
  { id: 2, name: "Mount Diablo",     lat: 37.8816, lng: -121.9142, sector: "Bay Area NW-1", region: "East Bay Hills",      risk: 0.68 },
  { id: 3, name: "Santa Ana Ridge",  lat: 33.7395, lng: -117.6284, sector: "SoCal SE-2",    region: "SoCal Inland",        risk: 0.88 },
  { id: 4, name: "Point Reyes",      lat: 38.0705, lng: -122.8996, sector: "Coastal NW-7",  region: "Northern California", risk: 0.44 },
  { id: 5, name: "Palomar Mountain", lat: 33.3628, lng: -116.8636, sector: "SoCal SE-9",    region: "San Diego Hills",     risk: 0.83 },
];

// ─── Generated network cameras ────────────────────────────────────────────
// 35 cameras distributed using weighted cluster selection so that high-risk
// terrain receives proportionally more coverage.

const GENERATED_CAMERAS = Array.from({ length: 35 }, (_, i) => {
  const cluster = pickWeightedCluster();
  const zoneIndex = Math.floor(Math.random() * 12);
  return {
    id: i + 100,
    name: `ALERT-${cluster.name.split(" ")[0]}-${String(i + 1).padStart(2, "0")}`,
    lat: cluster.lat + (Math.random() - 0.5) * 0.5,
    lng: cluster.lng + (Math.random() - 0.5) * 0.5,
    sector: `Zone-${zoneIndex}`,
    region: cluster.name,
    risk: parseFloat((cluster.risk * (0.85 + Math.random() * 0.3)).toFixed(2)),
  };
});

// ─── Full camera network ──────────────────────────────────────────────────
export const ALERT_CAMERAS = [...BASE_CAMERAS, ...GENERATED_CAMERAS];

// ─── Weighted camera picker ───────────────────────────────────────────────
// Used by dashboard detection loop to pick fire location by terrain risk.
// cameras: Camera[] — pass ALERT_CAMERAS or any subset

export function pickHighRiskCamera(cameras) {
  const total = cameras.reduce((sum, c) => sum + (c.risk ?? 0.5), 0);
  let rand = Math.random() * total;
  for (const cam of cameras) {
    rand -= (cam.risk ?? 0.5);
    if (rand <= 0) return cam;
  }
  return cameras[cameras.length - 1];
}

// ─── Event metadata generator ─────────────────────────────────────────────

const SPREAD_DIRS = [
  "Moving NE", "Moving NW", "Moving SE", "Moving SW",
  "Spreading N", "Spreading S", "Drifting NE", "Drifting NW",
];

export function genEventMeta(type) {
  const dir = SPREAD_DIRS[Math.floor(Math.random() * SPREAD_DIRS.length)];

  const speed = type === "Fire"
    ? Math.floor(12 + Math.random() * 20)   // 12–32 mph
    : Math.floor(3  + Math.random() * 7);   // 3–10 mph

  // spread distance: fire travels further
  const distMi = type === "Fire"
    ? (0.5 + Math.random() * 2.5).toFixed(1)  // 0.5–3.0 mi
    : (0.1 + Math.random() * 0.8).toFixed(1); // 0.1–0.9 mi

  // spread radius in meters — consumed by MapView Circle
  const spreadRadiusM = type === "Fire"
    ? Math.floor(800  + Math.random() * 2200)  // 800–3000 m
    : Math.floor(200  + Math.random() * 600);  // 200–800  m

  return {
    spreadDir:      `${dir} at ~${speed} mph`,
    distance:       `${distMi} mi from residential zone`,
    spreadRadiusM,
    actions: type === "Fire"
      ? ["Dispatch nearest unit", "Evacuate nearby structures", "Block access roads"]
      : ["Monitor progression",  "Stage units at perimeter",  "Issue smoke advisory"],
  };
}
