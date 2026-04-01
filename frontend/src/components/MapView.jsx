import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from "react-leaflet";
import L from "leaflet";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const fireIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  iconRetinaUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

const smokeIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png",
  iconRetinaUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-orange.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

function makeHistoryIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${color};border:2px solid rgba(255,255,255,0.5);box-shadow:0 0 8px ${color};opacity:0.75"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
    popupAnchor: [0, -8],
  });
}

const alertHistoryFireIcon = makeHistoryIcon("#ef4444");
const alertHistorySmokeIcon = makeHistoryIcon("#f59e0b");

const DEFAULT_CENTER = [37.7749, -122.4194];

function FlyToMarker({ position }) {
  const map = useMap();
  const prevPos = useRef(null);

  useEffect(() => {
    if (!position) return;
    const isSame =
      prevPos.current &&
      prevPos.current[0] === position[0] &&
      prevPos.current[1] === position[1];
    if (!isSame) {
      map.flyTo(position, 13, { duration: 1.4 });
      prevPos.current = position;
    }
  }, [map, position]);

  return null;
}

export default function MapView({ detection, center, alerts = [] }) {
  const hasDetection = detection.type !== "None";
  const markerPos = center ?? null;
  const icon = detection.type === "Fire" ? fireIcon : smokeIcon;

  // Deduplicate historical alert markers by camera location
  const historyMarkers = alerts.filter(
    (a, i, arr) =>
      a.lat &&
      a.lng &&
      arr.findIndex(x => x.lat === a.lat && x.lng === a.lng) === i
  );

  return (
    <div style={{ height: "288px" }} className="w-full rounded-lg overflow-hidden">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={11}
        scrollWheelZoom={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FlyToMarker position={hasDetection ? markerPos : null} />

        {/* Historical alert markers + spread circles (background layer) */}
        {historyMarkers.map(a => {
          const isActive = hasDetection && markerPos && markerPos[0] === a.lat && markerPos[1] === a.lng;
          if (isActive) return null;
          const isFire = a.type === "Fire";
          const radius = a.spreadRadiusM ?? (a.confidence * 25);
          return (
            <Marker
              key={`hist-${a.id}`}
              position={[a.lat, a.lng]}
              icon={isFire ? alertHistoryFireIcon : alertHistorySmokeIcon}
            >
              <Circle
                center={[a.lat, a.lng]}
                radius={radius}
                pathOptions={{
                  color:       isFire ? "#ef4444" : "#f59e0b",
                  fillColor:   isFire ? "#ef4444" : "#f59e0b",
                  fillOpacity: 0.08,
                  weight:      1,
                  opacity:     0.35,
                  dashArray:   "4 4",
                }}
              />
              <Popup>
                <div style={{ minWidth: "140px" }}>
                  <p style={{ fontWeight: "700", fontSize: "0.85rem", marginBottom: "3px" }}>
                    {isFire ? "🔥" : "🌫"} {a.type} — {a.camera}
                  </p>
                  <p style={{ color: "#6b7280", fontSize: "0.75rem" }}>{a.sector}</p>
                  <p style={{ color: "#9ca3af", fontSize: "0.75rem" }}>
                    {a.time} · {a.confidence}% conf. · ~{Math.round(radius / 1000 * 10) / 10} km radius
                  </p>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Active detection spread circle (renders under marker) */}
        {hasDetection && markerPos && (
          <Circle
            center={markerPos}
            radius={detection.location?.spreadRadiusM ?? (detection.confidence * 30)}
            pathOptions={{
              color:       detection.type === "Fire" ? "#dc2626" : "#f59e0b",
              fillColor:   detection.type === "Fire" ? "#dc2626" : "#f59e0b",
              fillOpacity: 0.12,
              weight:      2,
              opacity:     0.6,
              dashArray:   detection.type === "Fire" ? undefined : "6 4",
            }}
          />
        )}

        {/* Active detection marker (foreground) */}
        {hasDetection && markerPos && (
          <Marker position={markerPos} icon={icon}>
            <Popup>
              <div style={{ minWidth: "160px" }}>
                <p style={{ fontWeight: "700", fontSize: "0.95rem", marginBottom: "4px" }}>
                  {detection.type === "Fire" ? "🔥" : "🌫"} {detection.type} Detected
                </p>
                <p style={{ color: "#4b5563", fontSize: "0.8rem", marginBottom: "4px" }}>
                  Confidence:{" "}
                  <span style={{ fontWeight: "600", color: "#111827" }}>
                    {detection.confidence}%
                  </span>
                </p>
                {detection.location?.cameraName && (
                  <p style={{ color: "#6b7280", fontSize: "0.75rem", marginBottom: "3px" }}>
                    {detection.location.cameraName} · {detection.location.sector}
                  </p>
                )}
                {detection.location?.spreadRadiusM && (
                  <p style={{ color: "#9ca3af", fontSize: "0.75rem", marginBottom: "3px" }}>
                    Est. spread radius: ~{Math.round(detection.location.spreadRadiusM / 100) / 10} km
                  </p>
                )}
                <p style={{ color: "#6b7280", fontSize: "0.75rem", lineHeight: "1.4" }}>
                  {detection.reasoning}
                </p>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
