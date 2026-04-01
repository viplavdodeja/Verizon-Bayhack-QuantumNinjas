# FireWatch Backend

This project runs fire and smoke detection in a FastAPI backend using either a webcam or a remote ArcGIS-style image source.

## Project context

FireWatch is the backend portion of a hackathon project for wildfire and smoke monitoring.

Current scope:

- ingest frames from a source
- run YOLO-based fire and smoke detection
- maintain the latest detector state in memory
- expose backend endpoints that a separate frontend can consume

This repository is intentionally backend-only right now.

Related project context:

- the original working prototype logic came from `HackathonProject/fire_test2`
- this `FireWatch` folder is the refactored backend service
- a frontend can later read `/health`, `/source`, `/status`, `/detections`, and `/snapshot`
- additional sources such as ALERTCalifornia, ArcGIS image polling, local folders, and prerecorded video can be added behind the source abstraction

## What it does

- Runs the detector in a background thread.
- Reuses the same YOLO filtering and alert logic from the original webcam prototype.
- Keeps all detector state in memory.
- Supports two source types:
  - `webcam`
  - `arcgis`
- Exposes JSON endpoints for health, source info, status, detections, and the latest annotated snapshot.

## Tech stack

- Python
- FastAPI
- Uvicorn
- OpenCV
- Ultralytics YOLO
- NumPy
- Requests
- Pydantic

## Architecture summary

The backend is organized as a small service with a few clear layers:

- `app/main.py`
  - FastAPI app setup
  - application startup and shutdown
- `app/detector.py`
  - background detector loop
  - model loading
  - frame processing
  - shared state updates
- `app/sources/`
  - frame source implementations
  - webcam source
  - ArcGIS image polling source
  - source factory
- `app/state.py`
  - thread-safe in-memory shared state
- `app/routes.py`
  - API endpoints
- `app/models.py`
  - Pydantic response models
- `app/config.py`
  - environment-based configuration
  - safe `secret.txt` loading helpers

## Current detection flow

At runtime the backend works like this:

1. FastAPI starts.
2. The detector service starts in a background thread.
3. The configured source returns the latest frame.
4. YOLO runs inference on that frame.
5. Detections are filtered using the same rules from the earlier prototype.
6. Alert state is updated using consecutive detections and missed frames.
7. The latest detections and annotated snapshot are kept in memory.
8. API routes expose the current state to clients.

## Source modes

### Webcam mode

Webcam mode uses OpenCV webcam capture and keeps the original local prototype behavior.

### ArcGIS mode

ArcGIS mode polls a remote image URL on an interval, downloads the latest image with `requests`, decodes it into an OpenCV frame, and sends that frame through the same detector pipeline.

ArcGIS auth supports:

- `none`
- `query`
- `header`

The backend reads the API key from `secret.txt` at runtime when ArcGIS auth is enabled.

## Project structure

```text
FireWatch/
  app/
    config.py
    detector.py
    main.py
    models.py
    routes.py
    state.py
    services/
      alert_engine.py
    sources/
      arcgis_source.py
      base_source.py
      source_factory.py
      webcam_source.py
  requirements.txt
  secret.txt
  README.md
```

## API key setup

Place your ArcGIS API key in this file:

```text
FireWatch/secret.txt
```

Rules:

- Put only the API key in the file.
- Extra spaces and newlines are stripped automatically.
- The raw key is never printed in logs.
- Any key-related debug output is masked so only the last 4 characters are shown.
- If the file is missing, webcam mode still works.
- If ArcGIS mode needs auth and the file is missing, the backend fails gracefully into a clear source error state.

## Configuration

You can switch behavior using environment variables.

Main configuration areas:

- model path
- source type
- webcam settings
- ArcGIS polling settings
- ArcGIS auth settings

### Shared config

```powershell
$env:SOURCE_TYPE="webcam"
$env:MODEL_PATH="C:\Users\vipla\Documents\SFBU\BayHack\HackathonProject\fire_test2\firedetect-11s.pt"
```

### Webcam example

```powershell
$env:SOURCE_TYPE="webcam"
$env:CAMERA_INDEX="0"
$env:FRAME_WIDTH="640"
$env:FRAME_HEIGHT="480"
```

### ArcGIS example with no auth

```powershell
$env:SOURCE_TYPE="arcgis"
$env:ARCGIS_IMAGE_URL="https://example.com/latest.jpg"
$env:ARCGIS_AUTH_MODE="none"
$env:ARCGIS_POLL_INTERVAL_SECONDS="5"
$env:ARCGIS_REQUEST_TIMEOUT_SECONDS="10"
```

### ArcGIS example with query auth

```powershell
$env:SOURCE_TYPE="arcgis"
$env:ARCGIS_IMAGE_URL="https://example.com/latest.jpg"
$env:ARCGIS_AUTH_MODE="query"
$env:ARCGIS_API_KEY_FILE="C:\Users\vipla\Documents\SFBU\BayHack\HackathonProject\FireWatch\secret.txt"
$env:ARCGIS_API_KEY_QUERY_PARAM_NAME="token"
```

### ArcGIS example with header auth

```powershell
$env:SOURCE_TYPE="arcgis"
$env:ARCGIS_IMAGE_URL="https://example.com/latest.jpg"
$env:ARCGIS_AUTH_MODE="header"
$env:ARCGIS_API_KEY_FILE="C:\Users\vipla\Documents\SFBU\BayHack\HackathonProject\FireWatch\secret.txt"
$env:ARCGIS_AUTH_HEADER_NAME="Authorization"
$env:ARCGIS_AUTH_HEADER_PREFIX="Bearer "
```

## API endpoints

### `GET /health`

Returns:

- `status`
- `model_loaded`
- `source_connected`

### `GET /source`

Returns:

- `source_type`
- `source_name`
- `source_connected`
- `poll_interval_seconds`
- `image_url`
- `auth_mode`

### `GET /status`

Returns:

- `alert_active`
- `consecutive_detections`
- `missed_frames`
- `source_name`
- `last_updated`
- `system_status`

### `GET /detections`

Returns:

- `detection_count`
- `latest_detections`

### `GET /snapshot`

Returns the latest annotated frame as `image/jpeg`.

## Run locally

```powershell
cd C:\Users\vipla\Documents\SFBU\BayHack\HackathonProject\FireWatch
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Quick test commands

```powershell
Invoke-RestMethod http://127.0.0.1:8000/source
Invoke-RestMethod http://127.0.0.1:8000/status
Invoke-RestMethod http://127.0.0.1:8000/detections
Invoke-WebRequest http://127.0.0.1:8000/snapshot -OutFile latest_snapshot.jpg
```

## Intended frontend usage

The frontend does not need direct access to the model or source logic.

Expected frontend usage pattern:

- call `/health` to see whether the backend is alive
- call `/source` to understand what input source is active
- call `/status` to read alert state and detector counters
- call `/detections` to display the latest detection records
- call `/snapshot` to render the latest annotated image

This keeps the frontend thin and moves the detection logic into one backend service.

## Notes

- Duplicate ArcGIS images are skipped so the backend does not keep reprocessing the exact same remote image.
- The `/source` endpoint never exposes the raw API key.
- Webcam mode remains usable even if the ArcGIS key file is missing.
- On startup, the backend logs a clear ArcGIS configuration status message so you can see whether ArcGIS mode is ready.
