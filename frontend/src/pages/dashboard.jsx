import { useState, useEffect, useMemo, useCallback } from "react";
import MapView from "../components/MapView";
import { ALERT_CAMERAS, genEventMeta, pickHighRiskCamera } from "../data/cameras";

// Pure helper — lives outside component to avoid stale closures in intervals
function buildLocation(camera, type) {
  return {
    lat: camera.lat,
    lng: camera.lng,
    sector: camera.sector,
    region: camera.region,
    cameraName: camera.name,
    ...genEventMeta(type),
  };
}

function makeAlert(camera, type, confidence) {
  return {
    id: Date.now(),
    time: new Date().toLocaleTimeString(),
    type,
    confidence,
    cameraId: camera.id,
    camera: camera.name,
    sector: camera.sector,
    lat: camera.lat,
    lng: camera.lng,
  };
}

function CameraButton({ cam, isActive, isHot, onClick }) {
  return (
    <button
      className="cam-btn"
      onClick={onClick}
      style={{
        background: isActive
          ? "rgba(251,146,60,0.18)"
          : isHot
          ? "rgba(239,68,68,0.08)"
          : "rgba(255,255,255,0.04)",
        color: isActive ? "#fb923c" : isHot ? "#fca5a5" : "#9ca3af",
        borderColor: isActive
          ? "rgba(251,146,60,0.4)"
          : isHot
          ? "rgba(239,68,68,0.25)"
          : "rgba(255,255,255,0.06)",
      }}
    >
      {isHot && <span className="mr-1">🔥</span>}
      <span className="font-bold">{cam.name}</span>
      <span className="ml-2 font-normal opacity-60">{cam.sector}</span>
    </button>
  );
}

export default function Dashboard() {
  const [status, setStatus] = useState("Idle");
  const [mode, setMode] = useState("Manual");
  const [alerts, setAlerts] = useState([]);
  const [activeCamera, setActiveCamera] = useState(ALERT_CAMERAS[0]);
  const [cameraSearch, setCameraSearch] = useState("");
  const [activityLog, setActivityLog] = useState([{
    id: Date.now(),
    time: new Date().toLocaleTimeString(),
    message: "System initialized",
    type: "system",
  }]);

  const [detection, setDetection] = useState({
    type: "None",
    confidence: 0,
    prevConfidence: 0,
    reasoning: "System idle. No active detection.",
    location: null,
  });

  // ─── Derived ──────────────────────────────────────────────────────────────
  const isAlert = status === "Alert";
  const isFire = detection.type === "Fire";
  const isSmoke = detection.type === "Smoke";
  const confidenceTrend =
    detection.confidence > detection.prevConfidence ? "up" :
    detection.confidence < detection.prevConfidence ? "down" : "stable";

  // Set of camera IDs that currently have active alerts
  const alertCameraIds = useMemo(
    () => new Set(alerts.map(a => a.cameraId)),
    [alerts]
  );

  // Filtered + grouped camera list
  // Returns: { incidents: Camera[], grouped: Record<string, Camera[]> }
  const cameraGroups = useMemo(() => {
    const q = cameraSearch.trim().toLowerCase();
    const pool = q
      ? ALERT_CAMERAS.filter(cam =>
          cam.name.toLowerCase().includes(q) ||
          cam.sector.toLowerCase().includes(q) ||
          cam.region.toLowerCase().includes(q)
        )
      : ALERT_CAMERAS;

    const incidents = pool.filter(cam => alertCameraIds.has(cam.id));
    const rest = pool.filter(cam => !alertCameraIds.has(cam.id));

    const grouped = rest.reduce((acc, cam) => {
      if (!acc[cam.region]) acc[cam.region] = [];
      acc[cam.region].push(cam);
      return acc;
    }, {});

    return { incidents, grouped };
  }, [cameraSearch, alertCameraIds]);

  // ─── Activity Log ─────────────────────────────────────────────────────────
  const logActivity = useCallback((message, type = "info") => {
    setActivityLog(prev => [{
      id: Date.now() + Math.random(),
      time: new Date().toLocaleTimeString(),
      message,
      type,
    }, ...prev].slice(0, 40));
  }, []);

  // ─── Handlers ─────────────────────────────────────────────────────────────
  const handleStartMonitoring = useCallback(() => {
    setStatus("Monitoring");
    logActivity(`Monitoring started — ${activeCamera.name}`, "system");
  }, [activeCamera, logActivity]);

  const handleStopMonitoring = useCallback(() => {
    setStatus("Idle");
    setDetection({ type: "None", confidence: 0, prevConfidence: 0, reasoning: "System idle. No active detection.", location: null });
    logActivity("Monitoring stopped", "system");
  }, [logActivity]);

  const handleSetMode = useCallback((newMode) => {
    setMode(newMode);
    logActivity(`Mode changed to ${newMode}`, "system");
  }, [logActivity]);

  const handleSetCamera = useCallback((cam) => {
    setActiveCamera(cam);
    setCameraSearch("");
    logActivity(`Camera switched to ${cam.name} (${cam.sector})`, "system");
  }, [logActivity]);

  const handleAlert = useCallback(() => {
    const conf = 92;
    setStatus("Alert");
    setAlerts(prev => [makeAlert(activeCamera, "Fire", conf), ...prev]);
    setDetection(prev => ({
      type: "Fire",
      confidence: conf,
      prevConfidence: prev.confidence,
      reasoning: "Active fire detected near power lines. Rapid spread observed. Immediate response required.",
      location: buildLocation(activeCamera, "Fire"),
    }));
    logActivity(`🔥 Manual alert triggered — ${activeCamera.name} · ${conf}% conf.`, "fire");
  }, [activeCamera, logActivity]);

  // ─── Auto-switch to camera with latest alert ─────────────────────────────
  useEffect(() => {
    if (alerts.length === 0) return;
    const latest = alerts[0];
    const cam = ALERT_CAMERAS.find(c => c.id === latest.cameraId);
    if (cam && cam.id !== activeCamera.id) {
      setActiveCamera(cam);
      logActivity(`Auto-switched to ${cam.name} — active incident`, "system");
    }
  }, [alerts]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Reset on camera switch ───────────────────────────────────────────────
  useEffect(() => {
    if (status !== "Alert") {
      setDetection(prev => ({
        type: "None",
        confidence: 0,
        prevConfidence: prev.confidence,
        reasoning: "System idle. No active detection.",
        location: null,
      }));
    }
  }, [activeCamera]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Auto detection loop ──────────────────────────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      if (status !== "Monitoring") return;
      const rand = Math.random();

      if (rand > 0.7) {
        const conf = Math.floor(60 + Math.random() * 20);
        setDetection(prev => ({
          type: "Smoke",
          confidence: conf,
          prevConfidence: prev.confidence,
          reasoning: "Smoke plume detected moving northeast. Potential wildfire ignition zone.",
          location: buildLocation(activeCamera, "Smoke"),
        }));
        logActivity(`Smoke detected — ${activeCamera.name} · ${conf}% conf.`, "smoke");
      }

      // Auto alerts only fire in Auto mode — pick by terrain risk, not activeCamera
      if (rand > 0.9 && mode === "Auto") {
        const fireCam = pickHighRiskCamera(ALERT_CAMERAS);
        const conf = 90;
        setStatus("Alert");
        setAlerts(prev => [makeAlert(fireCam, "Fire", conf), ...prev]);
        setDetection(prev => ({
          type: "Fire",
          confidence: conf,
          prevConfidence: prev.confidence,
          reasoning: "Confirmed fire ignition detected near vegetation. Rapid spread likely.",
          location: buildLocation(fireCam, "Fire"),
        }));
        logActivity(`🔥 Fire confirmed — ${fireCam.name} · ${conf}% conf.`, "fire");
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [status, activeCamera, mode, logActivity]);

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div className={`min-h-screen p-6 space-y-6 font-mono ${
      isAlert
        ? "bg-gradient-to-br from-gray-950 via-red-950 to-gray-950"
        : "bg-gradient-to-br from-gray-950 via-gray-900 to-zinc-900"
    }`}>
      <style>{`
        .flame-text {
          background: linear-gradient(to top, #f97316, #fbbf24, #fef08a);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .card {
          background: rgba(17,17,17,0.85);
          border: 1px solid rgba(251,146,60,0.15);
          backdrop-filter: blur(6px);
          transition: box-shadow 0.25s ease, border-color 0.25s ease;
        }
        .card:hover {
          box-shadow: 0 0 24px rgba(251,146,60,0.22);
          border-color: rgba(251,146,60,0.25);
        }
        .card-alert {
          background: rgba(30,0,0,0.9);
          border: 1px solid rgba(239,68,68,0.4);
        }
        .card-alert:hover {
          box-shadow: 0 0 24px rgba(239,68,68,0.35);
          border-color: rgba(239,68,68,0.55);
        }
        .glow-red { box-shadow: 0 0 20px rgba(239,68,68,0.3); }
        .glow-orange { box-shadow: 0 0 16px rgba(251,146,60,0.2); }
        .btn {
          width: 100%;
          padding: 8px 12px;
          border-radius: 8px;
          font-weight: 600;
          font-size: 0.85rem;
          letter-spacing: 0.05em;
          transition: all 0.2s;
          border: 1px solid transparent;
        }
        .btn:hover { filter: brightness(1.2); transform: translateY(-1px); }
        .btn:active { transform: translateY(0); filter: brightness(0.95); }
        .cam-btn {
          width: 100%;
          padding: 5px 10px;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 600;
          text-align: left;
          transition: all 0.15s;
          border: 1px solid transparent;
          cursor: pointer;
        }
        .cam-btn:hover { filter: brightness(1.2); }
        .search-input {
          width: 100%;
          padding: 5px 10px;
          border-radius: 6px;
          font-size: 0.75rem;
          font-family: monospace;
          background: rgba(255,255,255,0.05);
          border: 1px solid rgba(251,146,60,0.15);
          color: #d1d5db;
          outline: none;
          transition: border-color 0.15s;
        }
        .search-input:focus { border-color: rgba(251,146,60,0.45); }
        .search-input::placeholder { color: #374151; }
        .fire-bar { background: linear-gradient(to right, #f97316, #ef4444, #dc2626); }
        .smoke-bar { background: linear-gradient(to right, #fbbf24, #f59e0b); }
        .safe-bar { background: linear-gradient(to right, #22c55e, #16a34a); }
        .log-row { transition: background 0.1s; border-bottom: 1px solid rgba(255,255,255,0.04); }
        .log-row:hover { background: rgba(255,255,255,0.025); }
      `}</style>

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className={`card rounded-xl p-5 flex justify-between items-center ${isAlert ? "card-alert glow-red" : "glow-orange"}`}>
        <div>
          <h1 className="text-2xl font-bold flame-text tracking-wide">QuantumNinjas FireWatch</h1>
          <p className="text-xs text-orange-300 mt-0.5">
            {status === "Idle" && "System idle — awaiting activation"}
            {status === "Monitoring" && `Monitoring ALERTCalifornia Network • Active Camera: ${activeCamera.name}`}
            {status === "Alert" && `⚠ Critical alert — ${activeCamera.name} · ${activeCamera.sector}`}
          </p>
        </div>

        <div className="flex flex-col items-end gap-2">
          {/* Scale indicators */}
          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-500">
              Monitoring{" "}
              <span className="text-gray-200 font-semibold tabular-nums">1,204</span>{" "}
              cameras
            </span>
            <span className="w-px h-3 bg-gray-700 inline-block" />
            <span className="text-xs text-gray-500">
              Active Alerts:{" "}
              <span className={`font-bold tabular-nums ${alerts.length > 0 ? "text-red-400" : "text-gray-300"}`}>
                {alerts.length}
              </span>
            </span>
          </div>
          <div className="flex gap-3 items-center">
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest ${
              isAlert
                ? "bg-red-600/90 text-white animate-pulse"
                : status === "Monitoring"
                ? "bg-amber-500/90 text-black"
                : "bg-green-700/80 text-green-100"
            }`}>
              {status}
            </span>
            <span className="px-3 py-1 rounded-full bg-orange-900/60 border border-orange-500/30 text-orange-300 text-xs font-bold uppercase tracking-widest">
              {mode}
            </span>
          </div>
        </div>
      </div>

      {/* ── Alert Banner ────────────────────────────────────────────────────── */}
      {isAlert && (
        <div className="rounded-xl text-center font-bold shadow-lg animate-pulse p-4 text-sm tracking-widest uppercase"
          style={{ background: "linear-gradient(to right, #7f1d1d, #991b1b, #7f1d1d)", color: "#fca5a5", border: "1px solid #ef4444" }}>
          🔥 PRIORITY ALERT: Active Fire Detected — {activeCamera.name} ({activeCamera.sector}) — Immediate Response Required 🔥
        </div>
      )}

      {/* ── Feed + Controls ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-6">

        {/* Live Feed */}
        <div className={`col-span-2 card rounded-xl p-5 ${isAlert ? "glow-red" : "glow-orange"}`}>
          <div className="flex items-start justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-orange-400 uppercase tracking-widest">Live Camera Feed</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {mode === "Manual" ? "ALERTCalifornia · Public Infrastructure View" : "AI Monitoring System · Autonomous Scan Mode"}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs px-2 py-0.5 rounded font-bold uppercase tracking-widest"
                style={{
                  background: mode === "Manual" ? "rgba(59,130,246,0.15)" : "rgba(168,85,247,0.15)",
                  color: mode === "Manual" ? "#93c5fd" : "#c4b5fd",
                  border: mode === "Manual" ? "1px solid rgba(59,130,246,0.3)" : "1px solid rgba(168,85,247,0.3)",
                }}>
                {mode === "Manual" ? "⊙ Manual" : "⚡ Auto"}
              </span>
              <div className="flex items-center gap-1.5">
                <span className={`inline-block w-2 h-2 rounded-full ${
                  isAlert ? "bg-red-500 animate-pulse" : status === "Monitoring" ? "bg-green-500 animate-pulse" : "bg-gray-600"
                }`} />
                <span className="text-xs text-gray-300">
                  {isAlert ? "Alert Active" : status === "Monitoring" ? "Live" : "Standby"}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mb-3 px-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 uppercase tracking-widest">Network</span>
              <span className="text-xs font-semibold text-gray-200">ALERTCalifornia</span>
            </div>
            <div className="w-px h-3 bg-gray-600" />
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 uppercase tracking-widest">Cameras Online</span>
              <span className="text-xs font-semibold text-gray-200 tabular-nums">1,200+</span>
            </div>
            <div className="w-px h-3 bg-gray-600" />
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 uppercase tracking-widest">Active Feed</span>
              <span className="text-xs font-semibold text-orange-300 font-mono">{activeCamera.name}</span>
              <span className="text-xs text-gray-500">·</span>
              <span className="text-xs text-gray-300">{activeCamera.sector}</span>
              <span className="text-xs text-gray-500">·</span>
              <span className="text-xs text-gray-400">{activeCamera.region}</span>
            </div>
            <div className="w-px h-3 bg-gray-600" />
            <span className="text-xs text-gray-500 font-mono tabular-nums">
              {activeCamera.lat.toFixed(4)}°, {activeCamera.lng.toFixed(4)}°
            </span>
          </div>

          <div className="relative rounded-lg overflow-hidden" style={{ height: "320px" }}>
            {mode === "Manual" && (
              <iframe
                key={activeCamera.id}
                src={`https://cameras.alertcalifornia.org/?pos=${activeCamera.lat}_${activeCamera.lng}_6`}
                title={`ALERTCalifornia — ${activeCamera.name}`}
                className="w-full h-full"
                style={{ border: "none", background: "#000" }}
                allow="fullscreen"
              />
            )}

            {mode === "Auto" && (
              <div className="w-full h-full bg-black flex items-center justify-center relative"
                style={{ border: "1px solid rgba(251,146,60,0.2)" }}>
                {isAlert && (
                  <div className="absolute inset-0 pointer-events-none"
                    style={{ background: "radial-gradient(ellipse at bottom, rgba(220,38,38,0.3) 0%, transparent 65%)" }} />
                )}
                {status === "Monitoring" && (
                  <div className="absolute inset-0 pointer-events-none overflow-hidden">
                    <div className="absolute left-0 right-0 h-px opacity-20 animate-bounce"
                      style={{ top: "40%", background: "linear-gradient(to right, transparent, #f97316, transparent)" }} />
                  </div>
                )}
                <div className="flex flex-col items-center gap-2 z-10">
                  <span className={`text-sm tracking-widest uppercase font-bold ${
                    isFire ? "text-red-400" : isSmoke ? "text-amber-400" : "text-gray-500"
                  }`}>
                    {status === "Idle" ? "No Signal" : isFire ? "Fire Detected" : isSmoke ? "Smoke Detected" : "Scanning..."}
                  </span>
                  {status !== "Idle" && (
                    <span className="text-xs text-gray-600 font-mono tabular-nums">
                      {activeCamera.lat.toFixed(4)}°N · {activeCamera.lng.toFixed(4)}°W
                    </span>
                  )}
                  {status === "Monitoring" && !isFire && !isSmoke && (
                    <span className="text-xs text-orange-500/50 italic animate-pulse mt-1">
                      ◉ AI model analyzing feed
                    </span>
                  )}
                </div>
                {status !== "Idle" && (
                  <span className="absolute top-3 left-3 text-xs px-2 py-1 rounded font-bold animate-pulse z-10"
                    style={{ background: "#dc2626", color: "white" }}>
                    ● REC
                  </span>
                )}
                {status !== "Idle" && (
                  <span className="absolute top-3 right-3 text-xs px-2 py-1 rounded font-mono z-10"
                    style={{ background: "rgba(0,0,0,0.75)", color: "#6b7280", border: "1px solid rgba(255,255,255,0.07)" }}>
                    {activeCamera.name}
                  </span>
                )}
                {(isFire || isSmoke) && (
                  <div className="absolute bottom-0 left-0 right-0 px-4 py-3 z-10"
                    style={{ background: "linear-gradient(to top, rgba(0,0,0,0.85), transparent)" }}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-widest"
                        style={{ color: isFire ? "#f87171" : "#fbbf24" }}>
                        {detection.type} · {detection.confidence}% confidence
                      </span>
                      <span className="text-xs text-gray-500 font-mono">{activeCamera.sector}</span>
                    </div>
                  </div>
                )}
                {isFire && (
                  <div className="absolute bottom-0 left-0 right-0 h-20 pointer-events-none"
                    style={{ background: "linear-gradient(to top, rgba(251,146,60,0.2), transparent)" }} />
                )}
              </div>
            )}

            {isAlert && (
              <div className="absolute inset-0 pointer-events-none rounded-lg animate-pulse"
                style={{ border: "2px solid rgba(239,68,68,0.5)", zIndex: 20 }} />
            )}
          </div>
        </div>

        {/* Controls + Camera Selector */}
        <div className="card rounded-xl p-5 glow-orange flex flex-col gap-3">
          <h2 className="text-sm font-bold text-orange-400 uppercase tracking-widest">Control Panel</h2>

          <button className="btn" onClick={handleStartMonitoring}
            style={{ background: "rgba(21,128,61,0.8)", color: "#bbf7d0", borderColor: "rgba(34,197,94,0.3)" }}>
            ▶ Start Monitoring
          </button>
          <button className="btn" onClick={handleStopMonitoring}
            style={{ background: "rgba(127,29,29,0.8)", color: "#fca5a5", borderColor: "rgba(239,68,68,0.3)" }}>
            ■ Stop Monitoring
          </button>
          <button className="btn" onClick={() => handleSetMode("Manual")}
            style={{ background: "rgba(30,58,138,0.8)", color: "#bfdbfe", borderColor: "rgba(59,130,246,0.3)" }}>
            ⊙ Manual Mode
          </button>
          <button className="btn" onClick={() => handleSetMode("Auto")}
            style={{ background: "rgba(88,28,135,0.8)", color: "#e9d5ff", borderColor: "rgba(168,85,247,0.3)" }}>
            ⚡ Auto Mode
          </button>
          <button className="btn" onClick={handleAlert}
            style={{ background: "linear-gradient(135deg, #c2410c, #dc2626)", color: "white", borderColor: "rgba(251,146,60,0.4)" }}>
            🔥 Send Alert
          </button>

          {/* Camera Selector */}
          <div className="flex flex-col gap-2" style={{ borderTop: "1px solid rgba(251,146,60,0.12)", paddingTop: "8px" }}>
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-500 uppercase tracking-widest">Camera Network</p>
              <span className="text-xs text-gray-600 tabular-nums">{ALERT_CAMERAS.length} online</span>
            </div>

            <input
              type="text"
              className="search-input"
              placeholder="Search name, sector, region..."
              value={cameraSearch}
              onChange={e => setCameraSearch(e.target.value)}
            />

            <div className="flex flex-col overflow-y-auto" style={{ maxHeight: "172px", gap: "1px" }}>
              {cameraGroups.incidents.length === 0 && Object.keys(cameraGroups.grouped).length === 0 && (
                <p className="text-xs text-gray-600 italic px-2 py-1">No cameras match</p>
              )}

              {/* Priority: Active Incidents */}
              {cameraGroups.incidents.length > 0 && (
                <>
                  <p className="text-xs font-bold px-1 pt-1 pb-0.5 uppercase tracking-widest"
                    style={{ color: "#ef4444" }}>
                    🔥 Active Incidents
                  </p>
                  {cameraGroups.incidents.map(cam => (
                    <CameraButton
                      key={cam.id}
                      cam={cam}
                      isActive={activeCamera.id === cam.id}
                      isHot
                      onClick={() => handleSetCamera(cam)}
                    />
                  ))}
                  {Object.keys(cameraGroups.grouped).length > 0 && (
                    <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", margin: "4px 0" }} />
                  )}
                </>
              )}

              {/* Grouped by region */}
              {Object.entries(cameraGroups.grouped).map(([region, cameras]) => (
                <div key={region}>
                  <p className="text-xs px-1 pt-1 pb-0.5 uppercase tracking-widest"
                    style={{ color: "#4b5563", letterSpacing: "0.08em" }}>
                    {region}
                  </p>
                  {cameras.map(cam => (
                    <CameraButton
                      key={cam.id}
                      cam={cam}
                      isActive={activeCamera.id === cam.id}
                      isHot={false}
                      onClick={() => handleSetCamera(cam)}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Detection + Coordination + Map ──────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-6">
        <div className="flex flex-col gap-6">

          {/* Detection Analysis */}
          <div className={`card rounded-xl p-5 space-y-4 ${isFire ? "card-alert glow-red" : "glow-orange"}`}>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-orange-400 uppercase tracking-widest">Detection Analysis</h2>
              <span className="text-xs text-gray-500 font-mono">{activeCamera.name}</span>
            </div>

            <p className={`text-2xl font-bold tracking-wide ${
              isFire ? "text-red-400" : isSmoke ? "text-amber-400" : "text-green-400"
            }`}>
              {isFire ? "🔥 " : isSmoke ? "🌫 " : "✓ "}{detection.type}
            </p>

            <div>
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-gray-400 uppercase tracking-widest">Confidence</p>
                {detection.type !== "None" && (
                  <span className="text-xs font-bold"
                    style={{ color: confidenceTrend === "up" ? "#4ade80" : confidenceTrend === "down" ? "#f87171" : "#4b5563" }}>
                    {confidenceTrend === "up" ? "↑ Increasing" : confidenceTrend === "down" ? "↓ Decreasing" : "— Stable"}
                  </span>
                )}
              </div>
              <div className="w-full rounded-full h-2" style={{ background: "rgba(255,255,255,0.08)" }}>
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    detection.confidence > 80 ? "fire-bar" : detection.confidence > 50 ? "smoke-bar" : "safe-bar"
                  }`}
                  style={{ width: `${detection.confidence}%` }}
                />
              </div>
              <p className="text-sm font-bold mt-1" style={{
                color: detection.confidence > 80 ? "#f87171" : detection.confidence > 50 ? "#fbbf24" : "#4ade80"
              }}>
                {detection.confidence}%
              </p>
            </div>

            <p className="text-sm text-gray-300 leading-relaxed">{detection.reasoning}</p>

            {status === "Monitoring" && (
              <p className="text-xs text-orange-400 italic animate-pulse">
                ◉ Scanning {activeCamera.name} — {activeCamera.region}
              </p>
            )}
          </div>

          {/* Location & Coordination */}
          <div className={`card rounded-xl p-5 space-y-4 ${isFire ? "card-alert glow-red" : "glow-orange"}`}>
            <h2 className="text-sm font-bold text-orange-400 uppercase tracking-widest">
              Location &amp; Coordination
            </h2>

            {!detection.location ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-500 italic">No active event</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Camera</p>
                    <p className="text-sm font-bold text-gray-200">{activeCamera.name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Sector</p>
                    <p className="text-sm font-bold text-orange-300">{activeCamera.sector}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Latitude</p>
                    <p className="text-sm font-bold text-gray-400 font-mono tabular-nums">{activeCamera.lat.toFixed(4)}°</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Longitude</p>
                    <p className="text-sm font-bold text-gray-400 font-mono tabular-nums">{activeCamera.lng.toFixed(4)}°</p>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Camera</p>
                    <p className="text-sm font-bold text-gray-100">{detection.location.cameraName}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Region</p>
                    <p className="text-sm font-bold text-gray-300">{detection.location.region}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Latitude</p>
                    <p className="text-sm font-bold text-gray-100 font-mono tabular-nums">{detection.location.lat.toFixed(4)}°</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Longitude</p>
                    <p className="text-sm font-bold text-gray-100 font-mono tabular-nums">{detection.location.lng.toFixed(4)}°</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Sector / Zone</p>
                    <p className="text-sm font-bold text-orange-300">{detection.location.sector}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-0.5">Spread Direction</p>
                    <p className="text-sm font-bold text-amber-300">{detection.location.spreadDir}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 rounded-lg px-3 py-2"
                  style={{ background: "rgba(251,146,60,0.08)", border: "1px solid rgba(251,146,60,0.2)" }}>
                  <span className="text-base">📍</span>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-widest">Distance to Critical Area</p>
                    <p className="text-sm font-bold text-orange-200">{detection.location.distance}</p>
                  </div>
                </div>
                <div className="rounded-lg px-3 py-3 space-y-2"
                  style={{
                    background: isFire ? "rgba(127,29,29,0.45)" : "rgba(120,80,0,0.3)",
                    border: isFire ? "1px solid rgba(239,68,68,0.35)" : "1px solid rgba(251,191,36,0.25)",
                  }}>
                  <p className="text-xs font-bold uppercase tracking-widest"
                    style={{ color: isFire ? "#fca5a5" : "#fde68a" }}>
                    ⚡ Recommended Actions
                  </p>
                  <ul className="space-y-1">
                    {detection.location.actions.map((action, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm font-semibold text-gray-100">
                        <span className="text-xs" style={{ color: isFire ? "#f87171" : "#fbbf24" }}>▸</span>
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Map */}
        <div className="card rounded-xl p-5 flex flex-col gap-3 glow-orange">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-orange-400 uppercase tracking-widest">Live Map Overview</h2>
            <span className="text-xs text-gray-500 font-mono">
              {activeCamera.lat.toFixed(4)}°, {activeCamera.lng.toFixed(4)}°
            </span>
          </div>

          <MapView
            detection={detection}
            center={[activeCamera.lat, activeCamera.lng]}
            alerts={alerts}
          />

          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-300">
              {isFire ? "🔥 Fire detected — dispatch required"
                : isSmoke ? "🌫 Smoke detected — monitoring"
                : "✓ No active threats"}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-600 tabular-nums">{alerts.length} marker{alerts.length !== 1 ? "s" : ""}</span>
              <span className="text-xs text-gray-500 font-mono">{activeCamera.sector}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Alert History + Activity Timeline ────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-6">

        {/* Alert History */}
        <div className="card rounded-xl p-5 glow-orange">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-orange-400 uppercase tracking-widest">Alert History</h2>
            <span className="text-xs text-gray-600 tabular-nums">{alerts.length} total</span>
          </div>

          {alerts.length === 0 ? (
            <p className="text-gray-400 text-sm italic">No alerts logged</p>
          ) : (
            <div className="overflow-y-auto space-y-0" style={{ maxHeight: "200px" }}>
              {alerts.map(a => (
                <div key={a.id} className="log-row grid py-2 text-xs"
                  style={{ gridTemplateColumns: "1fr 1fr 1fr 72px" }}>
                  <span className="text-gray-300 font-mono">{a.time}</span>
                  <span className="text-orange-300 font-semibold">{a.camera}</span>
                  <span className="text-gray-400">{a.sector}</span>
                  <span className="font-bold text-red-400 text-right">🔥 {a.confidence}%</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* System Activity Timeline */}
        <div className="card rounded-xl p-5 glow-orange">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-orange-400 uppercase tracking-widest">System Activity</h2>
            <span className="text-xs text-gray-600 tabular-nums">{activityLog.length} events</span>
          </div>

          <div className="overflow-y-auto space-y-0" style={{ maxHeight: "200px" }}>
            {activityLog.map(entry => (
              <div key={entry.id} className="log-row flex items-start gap-3 py-1.5 rounded">
                <span className="text-gray-600 font-mono tabular-nums shrink-0 text-xs pt-px">
                  {entry.time}
                </span>
                <span className="text-xs font-mono leading-snug" style={{
                  color: entry.type === "fire"   ? "#f87171"
                       : entry.type === "smoke"  ? "#fbbf24"
                       : entry.type === "alert"  ? "#fca5a5"
                       : entry.type === "system" ? "#6b7280"
                       : "#9ca3af",
                }}>
                  {entry.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
