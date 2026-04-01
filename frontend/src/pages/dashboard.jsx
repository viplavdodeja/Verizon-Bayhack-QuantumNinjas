import { useCallback, useEffect, useMemo, useState } from "react";

import {
  buildSnapshotImageUrl,
  fetchBackendSnapshot,
  switchBackendSource,
} from "../lib/api";


function StatusBadge({ label, tone }) {
  const colors = {
    neutral: {
      background: "rgba(255,255,255,0.06)",
      color: "#d1d5db",
      border: "1px solid rgba(255,255,255,0.08)",
    },
    success: {
      background: "rgba(34,197,94,0.12)",
      color: "#86efac",
      border: "1px solid rgba(34,197,94,0.28)",
    },
    warning: {
      background: "rgba(245,158,11,0.12)",
      color: "#fcd34d",
      border: "1px solid rgba(245,158,11,0.28)",
    },
    danger: {
      background: "rgba(239,68,68,0.14)",
      color: "#fca5a5",
      border: "1px solid rgba(239,68,68,0.28)",
    },
  };

  const style = colors[tone] ?? colors.neutral;

  return (
    <span
      className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest"
      style={style}
    >
      {label}
    </span>
  );
}


function MetricCard({ title, value, subtext, tone = "neutral" }) {
  const borderColor = {
    neutral: "rgba(251,146,60,0.12)",
    success: "rgba(34,197,94,0.25)",
    warning: "rgba(245,158,11,0.24)",
    danger: "rgba(239,68,68,0.24)",
  };

  return (
    <div
      className="rounded-xl p-4"
      style={{
        background: "rgba(17,17,17,0.86)",
        border: `1px solid ${borderColor[tone] ?? borderColor.neutral}`,
      }}
    >
      <p className="text-xs uppercase tracking-widest text-gray-500">{title}</p>
      <p className="mt-2 text-2xl font-bold text-gray-100">{value}</p>
      <p className="mt-1 text-sm text-gray-400">{subtext}</p>
    </div>
  );
}


function ControlTabButton({ label, isActive, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="px-4 py-2 rounded-full text-xs font-bold uppercase tracking-[0.25em] transition"
      style={{
        background: isActive ? "rgba(251,146,60,0.18)" : "rgba(255,255,255,0.04)",
        color: isActive ? "#fdba74" : "#d1d5db",
        border: isActive
          ? "1px solid rgba(251,146,60,0.45)"
          : "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {label}
    </button>
  );
}


function formatTime(value) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}


function formatDetectionLabel(detection) {
  const label = detection.label ?? "unknown";
  const confidence = detection.confidence ?? 0;
  return `${label} - ${(confidence * 100).toFixed(1)}%`;
}


export default function Dashboard() {
  const [backendData, setBackendData] = useState({
    health: null,
    source: null,
    status: null,
    detections: null,
    cameras: null,
    errors: [],
  });
  const [snapshotUrl, setSnapshotUrl] = useState(buildSnapshotImageUrl());
  const [snapshotAvailable, setSnapshotAvailable] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSwitchingSource, setIsSwitchingSource] = useState(false);
  const [sourceMessage, setSourceMessage] = useState("");
  const [customArcgisUrl, setCustomArcgisUrl] = useState("");
  const [activeSourceTab, setActiveSourceTab] = useState("webcam");

  const loadData = useCallback(async () => {
    const snapshot = await fetchBackendSnapshot();
    setBackendData(snapshot);
    setSnapshotUrl(buildSnapshotImageUrl());
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      try {
        const snapshot = await fetchBackendSnapshot();
        if (!isMounted) {
          return;
        }

        setBackendData(snapshot);
        setSnapshotUrl(buildSnapshotImageUrl());
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadInitialData();
    const intervalId = window.setInterval(() => {
      loadData();
    }, 5000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [loadData]);

  useEffect(() => {
    if (backendData.source?.source_type === "arcgis") {
      setActiveSourceTab("arcgis");
      return;
    }

    if (backendData.source?.source_type === "webcam") {
      setActiveSourceTab("webcam");
    }
  }, [backendData.source]);

  useEffect(() => {
    setSnapshotAvailable(false);
  }, [snapshotUrl]);

  const health = backendData.health;
  const source = backendData.source;
  const status = backendData.status;
  const detections = backendData.detections;
  const cameraOptions = backendData.cameras?.cameras ?? [];

  const alertActive = Boolean(status?.alert_active);
  const detectionItems = detections?.latest_detections ?? [];

  const topBannerTone = useMemo(() => {
    if (alertActive) {
      return "danger";
    }

    if (health?.source_connected && health?.model_loaded) {
      return "success";
    }

    if (backendData.errors.length > 0) {
      return "warning";
    }

    return "neutral";
  }, [alertActive, health, backendData.errors]);

  async function handleSwitchToWebcam() {
    setIsSwitchingSource(true);
    setSourceMessage("");

    try {
      const response = await switchBackendSource({
        source_type: "webcam",
      });
      setSourceMessage(response.message);
      await loadData();
    } catch (error) {
      setSourceMessage(error.message);
    } finally {
      setIsSwitchingSource(false);
    }
  }

  async function handleSwitchToArcgisCamera(cameraId) {
    setIsSwitchingSource(true);
    setSourceMessage("");

    try {
      const response = await switchBackendSource({
        source_type: "arcgis",
        camera_id: cameraId,
      });
      setSourceMessage(response.message);
      await loadData();
    } catch (error) {
      setSourceMessage(error.message);
    } finally {
      setIsSwitchingSource(false);
    }
  }

  async function handleCustomArcgisSubmit(event) {
    event.preventDefault();

    if (!customArcgisUrl.trim()) {
      setSourceMessage("Enter a direct ArcGIS image URL before switching.");
      return;
    }

    setIsSwitchingSource(true);
    setSourceMessage("");

    try {
      const response = await switchBackendSource({
        source_type: "arcgis",
        image_url: customArcgisUrl.trim(),
      });
      setSourceMessage(response.message);
      await loadData();
    } catch (error) {
      setSourceMessage(error.message);
    } finally {
      setIsSwitchingSource(false);
    }
  }

  return (
    <div
      className="min-h-screen p-6 md:p-8"
      style={{
        background:
          "radial-gradient(circle at top, rgba(251,146,60,0.10), transparent 32%), linear-gradient(135deg, #020617, #111827 50%, #1f2937)",
        color: "#e5e7eb",
      }}
    >
      <div className="max-w-7xl mx-auto space-y-6">
        <header
          className="rounded-2xl p-6 md:p-8"
          style={{
            background: "rgba(3,7,18,0.78)",
            border: "1px solid rgba(251,146,60,0.18)",
            boxShadow: "0 16px 48px rgba(0,0,0,0.28)",
          }}
        >
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.35em] text-orange-400">
                QuantumNinjas FireWatch
              </p>
              <h1 className="text-3xl md:text-5xl font-black text-gray-100">
                Backend-connected wildfire monitoring console
              </h1>
              <p className="max-w-3xl text-sm md:text-base text-gray-400 leading-7">
                This dashboard reads live state from the FireWatch backend and now
                lets you switch between the local webcam pipeline and AlertCalifornia
                ArcGIS image feeds without restarting the server.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <StatusBadge
                label={alertActive ? "Alert Active" : "Monitoring"}
                tone={topBannerTone}
              />
              <StatusBadge
                label={source?.source_type ?? "Unknown Source"}
                tone="neutral"
              />
              <StatusBadge
                label={health?.source_connected ? "Source Online" : "Source Offline"}
                tone={health?.source_connected ? "success" : "warning"}
              />
            </div>
          </div>
        </header>

        <section
          className="rounded-2xl p-5"
          style={{
            background: "rgba(3,7,18,0.82)",
            border: "1px solid rgba(251,146,60,0.14)",
          }}
        >
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-orange-400">
                Source Control
              </p>
              <h2 className="mt-2 text-xl font-bold text-gray-100">
                Switch the backend between webcam and ArcGIS cameras
              </h2>
            </div>
            <div className="flex gap-3">
              <ControlTabButton
                label="Webcam"
                isActive={activeSourceTab === "webcam"}
                onClick={() => setActiveSourceTab("webcam")}
              />
              <ControlTabButton
                label="ArcGIS Cameras"
                isActive={activeSourceTab === "arcgis"}
                onClick={() => setActiveSourceTab("arcgis")}
              />
            </div>
          </div>

          {activeSourceTab === "webcam" && (
            <div className="mt-5 rounded-xl p-5 bg-white/5 border border-white/10">
              <p className="text-sm text-gray-300">
                Use the local OpenCV webcam source. The backend now prefers the
                Windows DirectShow path first and falls back when MSMF gets stuck.
              </p>
              <button
                type="button"
                onClick={handleSwitchToWebcam}
                disabled={isSwitchingSource}
                className="mt-4 px-5 py-3 rounded-xl text-sm font-semibold"
                style={{
                  background: "rgba(34,197,94,0.16)",
                  border: "1px solid rgba(34,197,94,0.35)",
                  color: "#d1fae5",
                  opacity: isSwitchingSource ? 0.65 : 1,
                }}
              >
                {isSwitchingSource ? "Switching source..." : "Switch to Webcam"}
              </button>
            </div>
          )}

          {activeSourceTab === "arcgis" && (
            <div className="mt-5 space-y-5">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {cameraOptions.map((camera) => {
                  const isSelected = source?.selected_camera_id === camera.camera_id;

                  return (
                    <button
                      key={camera.camera_id}
                      type="button"
                      onClick={() => handleSwitchToArcgisCamera(camera.camera_id)}
                      disabled={isSwitchingSource}
                      className="text-left rounded-xl p-4 transition"
                      style={{
                        background: isSelected
                          ? "rgba(251,146,60,0.16)"
                          : "rgba(255,255,255,0.03)",
                        border: isSelected
                          ? "1px solid rgba(251,146,60,0.45)"
                          : "1px solid rgba(255,255,255,0.08)",
                        opacity: isSwitchingSource ? 0.7 : 1,
                      }}
                    >
                      <p className="text-sm font-semibold text-gray-100">{camera.name}</p>
                      <p className="mt-1 text-xs uppercase tracking-widest text-orange-300">
                        {camera.region}
                      </p>
                      <p className="mt-3 text-xs text-gray-400 break-all">
                        {camera.image_url}
                      </p>
                    </button>
                  );
                })}
              </div>

              <form
                onSubmit={handleCustomArcgisSubmit}
                className="rounded-xl p-4 bg-white/5 border border-white/10"
              >
                <label className="block text-sm font-semibold text-gray-100">
                  Custom direct image URL
                </label>
                <p className="mt-1 text-sm text-gray-400">
                  Paste a direct `latest-frame.jpg` style endpoint if the preset list
                  is not enough.
                </p>
                <input
                  type="text"
                  value={customArcgisUrl}
                  onChange={(event) => setCustomArcgisUrl(event.target.value)}
                  placeholder="https://cameras.alertcalifornia.org/public-camera-data/..."
                  className="mt-3 w-full rounded-xl px-4 py-3 bg-slate-950/70 text-sm text-gray-100 border border-white/10"
                />
                <button
                  type="submit"
                  disabled={isSwitchingSource}
                  className="mt-3 px-5 py-3 rounded-xl text-sm font-semibold"
                  style={{
                    background: "rgba(251,146,60,0.18)",
                    border: "1px solid rgba(251,146,60,0.35)",
                    color: "#fed7aa",
                    opacity: isSwitchingSource ? 0.65 : 1,
                  }}
                >
                  {isSwitchingSource ? "Switching source..." : "Use Custom ArcGIS URL"}
                </button>
              </form>
            </div>
          )}

          {sourceMessage && (
            <p className="mt-4 text-sm text-orange-300">{sourceMessage}</p>
          )}
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            title="System Status"
            value={status?.system_status ?? "Loading"}
            subtext={
              health?.model_loaded
                ? "YOLO model loaded"
                : health?.model_error ?? "Model state unavailable"
            }
            tone={alertActive ? "danger" : "neutral"}
          />
          <MetricCard
            title="Alert State"
            value={alertActive ? "Active" : "Clear"}
            subtext={`Consecutive detections: ${status?.consecutive_detections ?? 0}`}
            tone={alertActive ? "danger" : "success"}
          />
          <MetricCard
            title="Missed Frames"
            value={String(status?.missed_frames ?? 0)}
            subtext="Frames with no valid fire/smoke hit"
            tone={status?.missed_frames > 0 ? "warning" : "neutral"}
          />
          <MetricCard
            title="Latest Detections"
            value={String(detections?.detection_count ?? 0)}
            subtext={source?.source_name ?? "Source name unavailable"}
            tone={detectionItems.length > 0 ? "warning" : "neutral"}
          />
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.45fr_0.95fr]">
          <div
            className="rounded-2xl p-5"
            style={{
              background: "rgba(3,7,18,0.82)",
              border: "1px solid rgba(251,146,60,0.14)",
            }}
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-orange-400">
                  Live Snapshot
                </p>
                <h2 className="mt-2 text-xl font-bold text-gray-100">
                  Latest annotated detector frame
                </h2>
              </div>
              <div className="text-right text-xs text-gray-500">
                <p>Last updated</p>
                <p className="mt-1 text-gray-300">{formatTime(status?.last_updated)}</p>
              </div>
            </div>

            <div
              className="rounded-2xl overflow-hidden flex items-center justify-center"
              style={{
                minHeight: "420px",
                background:
                  "linear-gradient(135deg, rgba(17,24,39,0.96), rgba(31,41,55,0.92))",
                border: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              {isLoading && (
                <p className="text-sm uppercase tracking-[0.24em] text-gray-500">
                  Loading backend data
                </p>
              )}

              {!isLoading && !snapshotAvailable && (
                <div className="text-center px-6">
                  <p className="text-lg font-semibold text-gray-200">
                    Snapshot not available yet
                  </p>
                  <p className="mt-2 text-sm text-gray-500">
                    The backend returns `/snapshot` only after a frame has been fetched,
                    processed, and annotated.
                  </p>
                </div>
              )}

              <img
                src={snapshotUrl}
                alt="Latest FireWatch snapshot"
                className={snapshotAvailable ? "w-full h-full object-cover" : "hidden"}
                onLoad={() => setSnapshotAvailable(true)}
                onError={() => setSnapshotAvailable(false)}
              />
            </div>
          </div>

          <div className="space-y-6">
            <div
              className="rounded-2xl p-5"
              style={{
                background: "rgba(3,7,18,0.82)",
                border: "1px solid rgba(251,146,60,0.14)",
              }}
            >
              <p className="text-xs uppercase tracking-[0.28em] text-orange-400">
                Source Diagnostics
              </p>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Source type</span>
                  <span className="text-gray-100 font-semibold">
                    {source?.source_type ?? "Unknown"}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Source name</span>
                  <span className="text-gray-100 font-semibold">
                    {source?.source_name ?? "Unknown"}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Connected</span>
                  <span
                    className={`font-semibold ${
                      source?.source_connected ? "text-emerald-300" : "text-amber-300"
                    }`}
                  >
                    {source?.source_connected ? "True" : "False"}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Selected camera</span>
                  <span className="text-gray-100 font-semibold">
                    {source?.selected_camera_id ?? "N/A"}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Poll interval</span>
                  <span className="text-gray-100 font-semibold">
                    {source?.poll_interval_seconds ?? "Unknown"}s
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">HTTP status</span>
                  <span className="text-gray-100 font-semibold">
                    {source?.last_fetch_http_status ?? "N/A"}
                  </span>
                </div>
                <div className="pt-2">
                  <p className="text-gray-500 mb-1">Image URL</p>
                  <p className="text-xs text-gray-300 break-all">
                    {source?.image_url ?? "No image URL exposed"}
                  </p>
                </div>
                <div className="pt-2">
                  <p className="text-gray-500 mb-1">Last successful fetch</p>
                  <p className="text-sm text-gray-200">
                    {formatTime(source?.last_successful_fetch_at)}
                  </p>
                </div>
                <div className="pt-2">
                  <p className="text-gray-500 mb-1">Last source error</p>
                  <p className="text-sm text-amber-300">
                    {source?.last_source_error ?? "No active source error"}
                  </p>
                </div>
              </div>
            </div>

            <div
              className="rounded-2xl p-5"
              style={{
                background: "rgba(3,7,18,0.82)",
                border: "1px solid rgba(251,146,60,0.14)",
              }}
            >
              <p className="text-xs uppercase tracking-[0.28em] text-orange-400">
                Backend Requests
              </p>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Health endpoint</span>
                  <span className="text-gray-100 font-semibold">/health</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Camera list endpoint</span>
                  <span className="text-gray-100 font-semibold">/cameras</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Source endpoint</span>
                  <span className="text-gray-100 font-semibold">/source</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Switch endpoint</span>
                  <span className="text-gray-100 font-semibold">/source/select</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Status endpoint</span>
                  <span className="text-gray-100 font-semibold">/status</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Detections endpoint</span>
                  <span className="text-gray-100 font-semibold">/detections</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-500">Snapshot endpoint</span>
                  <span className="text-gray-100 font-semibold">/snapshot</span>
                </div>
                <div className="pt-3 border-t border-white/5">
                  <p className="text-gray-500 mb-1">Frontend polling errors</p>
                  {backendData.errors.length === 0 ? (
                    <p className="text-sm text-emerald-300">No frontend polling errors</p>
                  ) : (
                    <ul className="space-y-2">
                      {backendData.errors.map((errorMessage) => (
                        <li key={errorMessage} className="text-sm text-amber-300">
                          {errorMessage}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <div
            className="rounded-2xl p-5"
            style={{
              background: "rgba(3,7,18,0.82)",
              border: "1px solid rgba(251,146,60,0.14)",
            }}
          >
            <p className="text-xs uppercase tracking-[0.28em] text-orange-400">
              Detection Records
            </p>
            <div className="mt-4 space-y-3">
              {detectionItems.length === 0 && (
                <p className="text-sm text-gray-500">
                  No fire or smoke detections are currently stored in backend memory.
                </p>
              )}

              {detectionItems.map((detection) => (
                <div
                  key={`${detection.timestamp}-${detection.label}-${detection.x1}`}
                  className="rounded-xl p-4"
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)",
                  }}
                >
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-semibold text-gray-100">
                      {formatDetectionLabel(detection)}
                    </p>
                    <StatusBadge
                      label={detection.label}
                      tone={
                        detection.label.toLowerCase().includes("fire")
                          ? "danger"
                          : "warning"
                      }
                    />
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-gray-400">
                    <p>Area ratio: {Number(detection.area_ratio).toFixed(4)}</p>
                    <p>Timestamp: {formatTime(detection.timestamp)}</p>
                    <p>Top-left: ({detection.x1}, {detection.y1})</p>
                    <p>Bottom-right: ({detection.x2}, {detection.y2})</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            className="rounded-2xl p-5"
            style={{
              background: "rgba(3,7,18,0.82)",
              border: "1px solid rgba(251,146,60,0.14)",
            }}
          >
            <p className="text-xs uppercase tracking-[0.28em] text-orange-400">
              Backend State Summary
            </p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div
                className="rounded-xl p-4"
                style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <p className="text-xs uppercase tracking-widest text-gray-500">
                  Health
                </p>
                <p className="mt-2 text-sm text-gray-200">
                  Status: {health?.status ?? "Unknown"}
                </p>
                <p className="mt-1 text-sm text-gray-400">
                  Model loaded: {health?.model_loaded ? "True" : "False"}
                </p>
                <p className="mt-1 text-sm text-gray-400 break-all">
                  Model path: {health?.model_path ?? "Unknown"}
                </p>
                <p className="mt-1 text-sm text-amber-300">
                  Model error: {health?.model_error ?? "No active model error"}
                </p>
                <p className="mt-1 text-sm text-gray-400">
                  Source connected: {health?.source_connected ? "True" : "False"}
                </p>
              </div>
              <div
                className="rounded-xl p-4"
                style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <p className="text-xs uppercase tracking-widest text-gray-500">
                  Status
                </p>
                <p className="mt-2 text-sm text-gray-200">
                  Alert active: {status?.alert_active ? "True" : "False"}
                </p>
                <p className="mt-1 text-sm text-gray-400">
                  Consecutive detections: {status?.consecutive_detections ?? 0}
                </p>
                <p className="mt-1 text-sm text-gray-400">
                  Missed frames: {status?.missed_frames ?? 0}
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
