import { useEffect, useState } from "react";

import AllCameras from "./pages/AllCameras";
import Dashboard from "./pages/dashboard";

const VIEWS = [
  { id: "all", label: "All cameras" },
  { id: "single", label: "Single camera dashboard" },
];

function readView() {
  return window.location.hash === "#single" ? "single" : "all";
}

function App() {
  const [view, setView] = useState(readView);

  useEffect(() => {
    const onHash = () => setView(readView());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div style={{ background: "#020617", minHeight: "100vh", color: "#e5e7eb" }}>
      <nav
        className="flex items-center gap-2 px-6 py-3"
        style={{ background: "#0b0b0b", borderBottom: "1px solid rgba(251,146,60,0.15)" }}
      >
        <span className="mr-4 text-sm font-black tracking-widest text-orange-400">FIREWATCH</span>
        {VIEWS.map((item) => (
          <a
            key={item.id}
            href={`#${item.id}`}
            className="rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest"
            style={{
              background: view === item.id ? "#ea580c" : "rgba(255,255,255,0.06)",
              color: view === item.id ? "#fff" : "#d1d5db",
            }}
          >
            {item.label}
          </a>
        ))}
      </nav>

      {view === "single" ? (
        <Dashboard />
      ) : (
        <div
          className="min-h-screen p-6 md:p-8"
          style={{
            background:
              "radial-gradient(circle at top, rgba(251,146,60,0.10), transparent 32%), linear-gradient(135deg, #020617, #111827 50%, #1f2937)",
          }}
        >
          <div className="mx-auto max-w-7xl">
            <AllCameras />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
