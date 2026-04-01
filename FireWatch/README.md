# FireWatch Backend

This project refactors the working `fire_test2` webcam prototype into a FastAPI backend.

## What it does

- Runs fire and smoke detection in a background thread.
- Uses the same webcam + Ultralytics YOLO pipeline from `fire_test2/live_test3.py`.
- Keeps the latest detector state in memory.
- Exposes JSON endpoints for health, status, detections, and the latest annotated frame.
- Uses a source abstraction so webcam is only the first source implementation.

## Project structure

```text
FireWatch/
  app/
    main.py
    config.py
    state.py
    models.py
    detector.py
    routes.py
    sources/
      base_source.py
      webcam_source.py
    services/
      alert_engine.py
  requirements.txt
  README.md
```

## Notes about the model file

By default, this backend looks for the YOLO model at:

```text
../fire_test2/firedetect-11s.pt
```

That means it reuses the existing working model from the old prototype without modifying the old folder.

If you want to point to a different model file later, set:

```powershell
$env:FIREWATCH_MODEL_PATH="C:\path\to\your\model.pt"
```

## API endpoints

### `GET /health`

Returns:

- `status`
- `model_loaded`
- `source_connected`

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

Each detection includes:

- `label`
- `confidence`
- `area_ratio`
- `x1`
- `y1`
- `x2`
- `y2`
- `timestamp`

### `GET /snapshot`

Returns the latest annotated frame as `image/jpeg`.

## Run locally

### 1. Create the project directory

```powershell
New-Item -ItemType Directory -Force C:\Users\vipla\Documents\SFBU\BayHack\HackathonProject\FireWatch
```

### 2. Create and activate a virtual environment

```powershell
cd C:\Users\vipla\Documents\SFBU\BayHack\HackathonProject\FireWatch
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install requirements

```powershell
pip install -r requirements.txt
```

### 4. Run the backend

```powershell
uvicorn app.main:app --reload
```

### 5. Open the API

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- Status: `http://127.0.0.1:8000/status`
- Detections: `http://127.0.0.1:8000/detections`
- Snapshot: `http://127.0.0.1:8000/snapshot`

## Future extension points

To add ALERTCalifornia / ArcGIS camera polling later, add another source class that follows the `BaseFrameSource` interface and update the source factory in `app/detector.py`.
