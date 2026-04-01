# QuantumNinjas FireWatch

A real-time wildfire detection and emergency response dashboard built for the Verizon BayHack hackathon. The system simulates monitoring the ALERTCalifornia camera network using AI-powered detection, interactive mapping, and command-center-style tooling designed for use by actual emergency responders.

---

## Overview

FireWatch monitors a simulated network of 1,200+ cameras across high-risk wildfire terrain in California. It surfaces the most critical feeds automatically, shows detected fire and smoke events on an interactive map with spread-radius visualization, and provides coordinators with real-time location data, recommended actions, and a full activity timeline.

The system uses a **hybrid approach**: real ALERTCalifornia infrastructure context (live iframe embeds in Manual mode) combined with a simulated AI detection engine (Auto mode) that picks fire events using terrain-weighted probability rather than random chance.

---

## Features

### Camera Network
- 40 cameras distributed across 6 real wildfire-prone California regions
- Named anchor cameras at known high-risk locations (Bear Mountain, Mount Diablo, Santa Ana Ridge, Point Reyes, Palomar Mountain)
- Weighted camera generation: high-risk terrain (SoCal Inland, San Diego Hills) receives proportionally more coverage
- Searchable, region-grouped camera selector with priority surfacing of cameras with active incidents

### Detection Engine
- **Manual Mode** — embeds a live ALERTCalifornia public camera view via iframe, centered on the active camera's coordinates
- **Auto Mode** — AI simulation engine scans the active feed every 3 seconds; smoke and fire events are triggered probabilistically, with fire events routed to the highest terrain-risk camera in the network rather than the currently viewed one
- Detection state tracks type (None / Smoke / Fire), confidence %, AI reasoning text, and a confidence trend indicator (↑ / ↓ / —)

### Map
- Interactive React-Leaflet map centered on the active camera
- Smooth `flyTo` animation when detection location changes
- **Spread-radius circles** rendered around each alert using `spreadRadiusM` from event metadata (800–3000m for fire, 200–800m for smoke)
- All historical alerts rendered as secondary dot markers with their own spread circles
- Active detection marker rendered on top with full popup detail (camera name, sector, confidence, estimated spread radius, AI reasoning)

### Coordination Panel
- Per-event location data: lat/lng, sector/zone, region, camera name
- Simulated spread direction and speed (fire: 12–32 mph, smoke: 3–10 mph)
- Distance to nearest residential zone
- Recommended actions list (auto-generated per detection type)

### Alert System
- Auto-switch: when a new alert fires on a different camera, the active feed switches to it automatically
- Priority camera list: cameras with active alerts float to the top of the selector under "🔥 Active Incidents"
- Alert history table: timestamp, camera name, sector, confidence
- System Activity timeline: full chronological log of every state change, detection, and camera switch

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 19 + Vite |
| Styling | Tailwind CSS v3 |
| Map | React-Leaflet v5 + Leaflet 1.9 |
| Language | JavaScript (ESM) |
| Build | Vite 8 |
| Linting | ESLint 9 |

---

## Project Structure

```
frontend/
├── src/
│   ├── pages/
│   │   └── dashboard.jsx       # Main command center UI + all state logic
│   ├── components/
│   │   └── MapView.jsx         # Leaflet map with multi-marker + Circle spread rings
│   ├── data/
│   │   └── cameras.js          # Camera network, terrain clusters, weighted picker, event metadata
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css               # Tailwind + Leaflet CSS imports
├── public/
├── index.html
├── tailwind.config.js
├── vite.config.js
└── package.json
```

---

## Getting Started

### Prerequisites

- Node.js 18+
- npm

### Install

```bash
cd frontend
npm install
```

### Run

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Build

```bash
npm run build
```

---

## Usage

1. **Start Monitoring** — activates the detection loop on the active camera
2. **Switch to Auto Mode** — enables AI-triggered fire alerts routed by terrain risk weighting
3. **Switch to Manual Mode** — loads the live ALERTCalifornia public camera viewer for the selected camera; alert dispatch is manual only
4. **Send Alert** — manually triggers a fire alert on the current camera
5. **Search cameras** — filter the camera list by name, sector, or region; active incidents always appear first
6. **Map** — shows all alert markers and spread circles; click any marker for details

---

## Camera Regions & Risk Weights

| Region | Risk Weight | Notes |
|---|---|---|
| SoCal Inland | 0.90 | Highest fire risk; Santa Ana winds |
| San Diego Hills | 0.85 | Chaparral terrain, high ignition rate |
| Sierra Nevada | 0.75 | Dense forest, lightning risk |
| East Bay Hills | 0.70 | Urban-wildland interface |
| Northern California | 0.65 | Remote terrain, late-season risk |
| Central Valley | 0.52 | Agriculture buffer, moderate risk |

Risk weights drive both camera placement density and the probability of Auto-mode fire events occurring in each region.

---

## Team

**QuantumNinjas** — Verizon BayHack
