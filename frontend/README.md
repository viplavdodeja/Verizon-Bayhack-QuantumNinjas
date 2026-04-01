# QuantumNinjas FireWatch Frontend

This frontend now connects to the live FireWatch FastAPI backend instead of using the old simulated dashboard loop.

## What it does

- polls the backend for `/health`
- polls the backend for `/source`
- polls the backend for `/status`
- polls the backend for `/detections`
- displays the latest backend `/snapshot`
- shows backend diagnostics such as source connection, fetch status, and last source error

## Tech stack

| Layer | Technology |
|---|---|
| Framework | React 19 + Vite |
| Styling | Tailwind CSS v3 |
| Language | JavaScript (ESM) |
| Build | Vite 8 |
| Dev proxy | Vite proxy to `http://127.0.0.1:8000` |

## Project structure

```text
frontend/
  src/
    lib/
      api.js
    pages/
      dashboard.jsx
    App.jsx
    main.jsx
    index.css
  vite.config.js
  package.json
```

## Backend dependency

The frontend expects the FireWatch backend to be running locally at:

```text
http://127.0.0.1:8000
```

Vite proxies frontend requests from `/api/*` to the backend during local development.

## Run locally

### 1. Start the backend

```powershell
cd C:\Users\vipla\Documents\SFBU\BayHack\HackathonProject\FireWatch
uvicorn app.main:app --reload
```

### 2. Start the frontend

```powershell
cd C:\Users\vipla\Documents\SFBU\BayHack\HackathonProject\frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Connected endpoints

The frontend uses these backend routes:

- `GET /health`
- `GET /source`
- `GET /status`
- `GET /detections`
- `GET /snapshot`

## Notes

- The frontend is now read-only with respect to the backend.
- It reflects backend detector state instead of generating simulated alerts in the browser.
- If `/snapshot` is not available yet, the UI shows a placeholder message until the backend produces an annotated frame.
