import { useEffect, useMemo, useRef, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";

import {
  buildCameraSnapshotUrl,
  fetchAlerts,
  fetchAllCameras,
  fetchCameraDetail,
} from "../lib/api";

const PAGE_SIZE = 24;
const CAMERA_POLL_MS = 10000;
const ALERT_POLL_MS = 5000;

const STATUS_COLORS = {
  alert: "#ef4444",
  ok: "#22c55e",
  error: "#6b7280",
  pending: "#94a3b8",
};

const STATUS_LABELS = {
  alert: "Fire / smoke alert",
  ok: "Clear",
  error: "Unavailable",
  pending: "Not checked yet",
};

function formatTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString();
}

function prettyCounty(county) {
  if (!county) return "";
  return county.charAt(0).toUpperCase() + county.slice(1);
}

function AlertBanner({ alerts, onOpen }) {
  if (alerts.length === 0) return null;

  return (
    <div
      className="sticky top-0 z-[1100] rounded-xl p-4 shadow-lg"
      style={{ background: "#7f1d1d", border: "1px solid #ef4444" }}
      role="alert"
    >
      <p className="text-sm font-black uppercase tracking-widest text-red-100">
        {alerts.length} active fire / smoke alert{alerts.length === 1 ? "" : "s"}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {alerts.map((alert) => (
          <button
            key={alert.camera_id}
            type="button"
            onClick={() => onOpen(alert.camera_id)}
            className="rounded-full px-3 py-1 text-xs font-semibold text-white transition hover:brightness-125"
            style={{ background: "rgba(239,68,68,0.35)", border: "1px solid rgba(254,202,202,0.4)" }}
          >
            {alert.name}
            {alert.county ? ` · ${prettyCounty(alert.county)}` : ""}
            {alert.top_label
              ? ` · ${alert.top_label} ${Math.round(alert.top_confidence * 100)}%`
              : ""}
            {alert.alert_started_at ? ` · since ${formatTime(alert.alert_started_at)}` : ""}
          </button>
        ))}
      </div>
    </div>
  );
}

function MonitorStats({ monitor, cameras }) {
  const counts = monitor?.status_counts ?? {};
  const total = monitor?.camera_count ?? cameras.length;
  const items = [
    ["Cameras", total],
    ["Alerts", counts.alert ?? 0],
    ["Clear", counts.ok ?? 0],
    ["Unavailable", counts.error ?? 0],
    ["Not checked yet", counts.pending ?? 0],
    [
      "Full sweep",
      monitor?.last_sweep_seconds
        ? `${Math.round(monitor.last_sweep_seconds)} s`
        : monitor?.current_sweep_checked
          ? `in progress ${monitor.current_sweep_checked}/${total}`
          : "starting",
    ],
    ["Inference", monitor?.avg_inference_ms ? `${Math.round(monitor.avg_inference_ms)} ms` : "—"],
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
      {items.map(([label, value]) => (
        <div
          key={label}
          className="rounded-xl p-3"
          style={{ background: "rgba(17,17,17,0.86)", border: "1px solid rgba(251,146,60,0.12)" }}
        >
          <p className="text-[10px] uppercase tracking-widest text-gray-500">{label}</p>
          <p className="mt-1 text-lg font-bold text-gray-100">{value}</p>
        </div>
      ))}
    </div>
  );
}

function CameraMap({ cameras, onOpen }) {
  // Draw alerts last so they sit on top of the green dots.
  const ordered = useMemo(
    () =>
      [...cameras]
        .filter((camera) => camera.lat != null && camera.lon != null)
        .sort((a, b) => (a.status === "alert") - (b.status === "alert")),
    [cameras],
  );

  return (
    <div className="overflow-hidden rounded-2xl" style={{ height: 460, border: "1px solid rgba(251,146,60,0.15)" }}>
      <MapContainer
        center={[37.2, -119.5]}
        zoom={6}
        preferCanvas
        style={{ height: "100%", width: "100%", background: "#0b0b0b" }}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {ordered.map((camera) => (
          <CircleMarker
            key={camera.camera_id}
            center={[camera.lat, camera.lon]}
            radius={camera.status === "alert" ? 9 : 4}
            pathOptions={{
              color: STATUS_COLORS[camera.status] ?? STATUS_COLORS.pending,
              fillColor: STATUS_COLORS[camera.status] ?? STATUS_COLORS.pending,
              fillOpacity: camera.status === "alert" ? 0.9 : 0.7,
              weight: camera.status === "alert" ? 2 : 1,
            }}
            eventHandlers={{ click: () => onOpen(camera.camera_id) }}
          >
            <Tooltip>
              {camera.name} — {STATUS_LABELS[camera.status] ?? camera.status}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}

function CameraTile({ camera, onOpen }) {
  const color = STATUS_COLORS[camera.status] ?? STATUS_COLORS.pending;
  const version = camera.last_updated_at ?? camera.last_checked_at ?? "0";

  return (
    <button
      type="button"
      onClick={() => onOpen(camera.camera_id)}
      className="group overflow-hidden rounded-xl text-left transition hover:-translate-y-0.5"
      style={{
        background: "rgba(17,17,17,0.9)",
        border: `1px solid ${camera.status === "alert" ? color : "rgba(255,255,255,0.08)"}`,
        boxShadow: camera.status === "alert" ? `0 0 18px ${color}66` : "none",
      }}
    >
      <div className="relative aspect-video bg-black">
        <img
          src={buildCameraSnapshotUrl(camera.camera_id, "thumb", version)}
          alt={`Latest frame from ${camera.name}`}
          loading="lazy"
          className="h-full w-full object-cover"
        />
        <span
          className="absolute left-2 top-2 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white"
          style={{ background: `${color}cc` }}
        >
          {camera.status === "alert" && camera.top_label
            ? `${camera.top_label} ${Math.round(camera.top_confidence * 100)}%`
            : STATUS_LABELS[camera.status] ?? camera.status}
        </span>
      </div>
      <div className="p-2">
        <p className="truncate text-sm font-semibold text-gray-100">{camera.name}</p>
        <p className="truncate text-xs text-gray-500">
          {prettyCounty(camera.county)} · updated {formatTime(camera.last_updated_at)}
        </p>
      </div>
    </button>
  );
}

function CameraModal({ cameraId, onClose }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchCameraDetail(cameraId);
        if (!cancelled) {
          setDetail(data);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      }
    }
    load();
    const timer = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [cameraId]);

  useEffect(() => {
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const version = detail?.last_updated_at ?? detail?.last_checked_at ?? "0";

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.78)" }}
      onClick={onClose}
    >
      <div
        className="max-h-full w-full max-w-5xl overflow-auto rounded-2xl p-5"
        style={{ background: "#111", border: "1px solid rgba(251,146,60,0.2)" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-orange-400">
              {STATUS_LABELS[detail?.status] ?? "Loading"}
            </p>
            <h2 className="text-2xl font-black text-gray-100">{detail?.name ?? cameraId}</h2>
            <p className="text-sm text-gray-400">
              {prettyCounty(detail?.county)} {detail?.lat ? `· ${detail.lat.toFixed(3)}, ${detail.lon.toFixed(3)}` : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-3 py-1 text-sm text-gray-300"
            style={{ border: "1px solid rgba(255,255,255,0.15)" }}
          >
            Close
          </button>
        </div>

        {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}

        <img
          src={buildCameraSnapshotUrl(cameraId, "full", version)}
          alt={`Latest annotated frame from ${detail?.name ?? cameraId}`}
          className="mt-4 w-full rounded-xl bg-black"
        />

        <div className="mt-4 grid gap-3 text-sm text-gray-300 md:grid-cols-4">
          <p>Last checked: {formatTime(detail?.last_checked_at)}</p>
          <p>New frame analysed: {formatTime(detail?.last_updated_at)}</p>
          <p>Consecutive detections: {detail?.consecutive_detections ?? 0}</p>
          <p>Frames analysed: {detail?.frames_analysed ?? 0}</p>
        </div>
        {detail?.last_error ? (
          <p className="mt-2 text-sm text-gray-400">Source error: {detail.last_error}</p>
        ) : null}

        <h3 className="mt-5 text-xs uppercase tracking-widest text-gray-500">Detections in latest frame</h3>
        {detail?.detections?.length ? (
          <ul className="mt-2 space-y-1 text-sm text-gray-200">
            {detail.detections.map((detection, index) => (
              <li key={index}>
                {detection.label} — {Math.round(detection.confidence * 100)}% confidence, box (
                {detection.x1}, {detection.y1}) → ({detection.x2}, {detection.y2})
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-gray-400">No fire or smoke detected in the latest frame.</p>
        )}

        <a
          href={detail?.image_url}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-block text-xs text-orange-300 underline"
        >
          Open the original AlertCalifornia frame
        </a>
      </div>
    </div>
  );
}

function useNotifications(alerts) {
  const supported = typeof window !== "undefined" && "Notification" in window;
  const [permission, setPermission] = useState(supported ? Notification.permission : "unsupported");
  const seen = useRef(null);

  useEffect(() => {
    const currentKeys = new Set(alerts.map((a) => `${a.camera_id}|${a.alert_started_at}`));
    // First load: remember existing alerts without notifying about all of them.
    if (seen.current === null) {
      seen.current = currentKeys;
      return;
    }
    if (supported && permission === "granted") {
      for (const alert of alerts) {
        const key = `${alert.camera_id}|${alert.alert_started_at}`;
        if (!seen.current.has(key)) {
          new Notification(`FireWatch alert: ${alert.name}`, {
            body: `${alert.top_label ?? "Fire/smoke"} detected (${Math.round((alert.top_confidence ?? 0) * 100)}%)${
              alert.county ? ` in ${prettyCounty(alert.county)} County` : ""
            }.`,
            tag: key,
          });
        }
      }
    }
    seen.current = currentKeys;
  }, [alerts, permission, supported]);

  async function request() {
    if (!supported) return;
    setPermission(await Notification.requestPermission());
  }

  return { permission, request };
}

export default function AllCameras() {
  const [cameras, setCameras] = useState([]);
  const [monitor, setMonitor] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [openCamera, setOpenCamera] = useState(null);
  const { permission, request } = useNotifications(alerts);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchAllCameras();
        if (cancelled) return;
        setCameras(data.cameras);
        setMonitor(data.monitor);
        setError(null);
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      }
    }
    load();
    const timer = setInterval(load, CAMERA_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchAlerts();
        if (!cancelled) setAlerts(data.alerts);
      } catch {
        // Camera polling already surfaces backend errors.
      }
    }
    load();
    const timer = setInterval(load, ALERT_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const statusRank = { alert: 0, ok: 1, pending: 2, error: 3 };
    return cameras
      .filter((camera) => filter === "all" || camera.status === filter)
      .filter(
        (camera) =>
          !needle ||
          camera.name.toLowerCase().includes(needle) ||
          (camera.county ?? "").toLowerCase().includes(needle) ||
          camera.camera_id.includes(needle),
      )
      .sort(
        (a, b) =>
          (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9) || a.name.localeCompare(b.name),
      );
  }, [cameras, filter, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageItems = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  return (
    <div className="space-y-5">
      <AlertBanner alerts={alerts} onOpen={setOpenCamera} />

      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-orange-400">All California cameras</p>
          <h2 className="text-2xl font-black text-gray-100">
            Watching {monitor?.camera_count ?? cameras.length} AlertCalifornia wildfire cameras
          </h2>
          <p className="text-sm text-gray-400">
            Each camera publishes a new still about once a minute. FireWatch checks every camera in rotation and
            runs fire/smoke detection on each new frame.
          </p>
        </div>
        <button
          type="button"
          onClick={request}
          disabled={permission === "granted" || permission === "unsupported"}
          className="rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest text-white disabled:opacity-60"
          style={{ background: permission === "granted" ? "#166534" : "#c2410c" }}
        >
          {permission === "granted"
            ? "Alert notifications on"
            : permission === "denied"
              ? "Notifications blocked in browser settings"
              : permission === "unsupported"
                ? "Notifications not supported"
                : "Turn on alert notifications"}
        </button>
      </div>

      {error ? (
        <p className="rounded-xl p-3 text-sm text-red-200" style={{ background: "rgba(127,29,29,0.5)" }}>
          Could not reach the FireWatch backend: {error}
        </p>
      ) : null}
      {monitor?.index_error ? <p className="text-sm text-red-300">{monitor.index_error}</p> : null}

      <MonitorStats monitor={monitor} cameras={cameras} />
      <CameraMap cameras={cameras} onOpen={setOpenCamera} />

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap gap-2">
          {["all", "alert", "ok", "pending", "error"].map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => {
                setFilter(value);
                setPage(0);
              }}
              className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-widest"
              style={{
                background: filter === value ? "#ea580c" : "rgba(255,255,255,0.06)",
                color: filter === value ? "#fff" : "#d1d5db",
              }}
            >
              {value === "all" ? "All" : STATUS_LABELS[value]}
            </button>
          ))}
        </div>
        <input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(0);
          }}
          placeholder="Search camera or county"
          className="rounded-full px-4 py-2 text-sm text-gray-100 outline-none"
          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
        {pageItems.map((camera) => (
          <CameraTile key={camera.camera_id} camera={camera} onOpen={setOpenCamera} />
        ))}
      </div>
      {filtered.length === 0 ? <p className="text-sm text-gray-400">No cameras match.</p> : null}

      <div className="flex items-center justify-center gap-3 text-sm text-gray-300">
        <button
          type="button"
          disabled={safePage === 0}
          onClick={() => setPage(safePage - 1)}
          className="rounded-full px-3 py-1 disabled:opacity-40"
          style={{ border: "1px solid rgba(255,255,255,0.15)" }}
        >
          Previous
        </button>
        <span>
          Page {safePage + 1} of {pageCount} · {filtered.length} cameras
        </span>
        <button
          type="button"
          disabled={safePage >= pageCount - 1}
          onClick={() => setPage(safePage + 1)}
          className="rounded-full px-3 py-1 disabled:opacity-40"
          style={{ border: "1px solid rgba(255,255,255,0.15)" }}
        >
          Next
        </button>
      </div>

      {openCamera ? <CameraModal cameraId={openCamera} onClose={() => setOpenCamera(null)} /> : null}
    </div>
  );
}
