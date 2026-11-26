"""Watch every public AlertCalifornia wildfire camera at once.

A background thread sweeps the full camera list in rotation. Frames are
downloaded in parallel, unchanged frames are skipped by hash, and new frames
go through the same YOLO model, box filtering and alert rules as the
single-source detector, with alert state kept per camera.
"""

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import logging
import os
import time
from threading import Event, Lock, Thread
from typing import Dict, Iterator, List, Optional

import cv2
import numpy as np
import requests
from ultralytics import YOLO

from app.config import settings
from app.services.alert_engine import AlertEngine


logger = logging.getLogger(__name__)

CAMERA_INDEX_URL = os.getenv(
    "ALERTCA_CAMERA_INDEX_URL",
    "https://cameras.alertcalifornia.org/public-camera-data/all_cameras-v3.json",
)
FRAME_URL_TEMPLATE = os.getenv(
    "ALERTCA_FRAME_URL_TEMPLATE",
    "https://cameras.alertcalifornia.org/public-camera-data/{camera_id}/latest-frame.jpg",
)
THUMB_URL_TEMPLATE = os.getenv(
    "ALERTCA_THUMB_URL_TEMPLATE",
    "https://cameras.alertcalifornia.org/public-camera-data/{camera_id}/latest-thumb.jpg",
)
MULTI_CAMERA_ENABLED = os.getenv("MULTI_CAMERA_ENABLED", "true").lower() != "false"
INDEX_REFRESH_SECONDS = float(os.getenv("MULTI_CAMERA_INDEX_REFRESH_SECONDS", "3600"))
DOWNLOAD_WORKERS = int(os.getenv("MULTI_CAMERA_DOWNLOAD_WORKERS", "16"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("MULTI_CAMERA_REQUEST_TIMEOUT_SECONDS", "15"))
# Cameras with recent fire/smoke activity are re-checked after this many
# other cameras, so they update far more often than once per full sweep.
HOT_RECHECK_EVERY = int(os.getenv("MULTI_CAMERA_HOT_RECHECK_EVERY", "100"))
HOT_WINDOW_SECONDS = float(os.getenv("MULTI_CAMERA_HOT_WINDOW_SECONDS", "1800"))
FULL_SNAPSHOT_MAX_WIDTH = int(os.getenv("MULTI_CAMERA_SNAPSHOT_MAX_WIDTH", "1280"))
THUMB_WIDTH = int(os.getenv("MULTI_CAMERA_THUMB_WIDTH", "360"))
MIN_SWEEP_SECONDS = float(os.getenv("MULTI_CAMERA_MIN_SWEEP_SECONDS", "20"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CameraState:
    camera_id: str
    name: str
    lat: Optional[float]
    lon: Optional[float]
    county: Optional[str]
    region: Optional[str]
    state: Optional[str]
    sponsor: Optional[str]
    image_url: str
    thumb_url: str
    alert_engine: AlertEngine
    status: str = "pending"  # pending | ok | alert | error
    last_checked_at: Optional[str] = None
    last_checked_ts: float = 0.0
    last_updated_at: Optional[str] = None  # last time a NEW frame was analysed
    last_hash: Optional[str] = None
    last_error: Optional[str] = None
    last_http_status: Optional[int] = None
    detections: List[Dict[str, object]] = field(default_factory=list)
    last_detection_ts: float = 0.0
    alert_started_at: Optional[str] = None
    frames_analysed: int = 0
    full_jpeg: Optional[bytes] = None
    thumb_jpeg: Optional[bytes] = None

    def is_hot(self, now: float) -> bool:
        return (
            self.alert_engine.alert_active
            or self.alert_engine.consecutive_detections > 0
            or (now - self.last_detection_ts) < HOT_WINDOW_SECONDS
        )

    def summary(self) -> Dict[str, object]:
        top = max(self.detections, key=lambda d: float(d["confidence"]), default=None)
        return {
            "camera_id": self.camera_id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "county": self.county,
            "region": self.region,
            "state": self.state,
            "image_url": self.image_url,
            "status": self.status,
            "alert_active": self.alert_engine.alert_active,
            "consecutive_detections": self.alert_engine.consecutive_detections,
            "detection_count": len(self.detections),
            "top_label": top["label"] if top else None,
            "top_confidence": float(top["confidence"]) if top else None,
            "alert_started_at": self.alert_started_at,
            "last_checked_at": self.last_checked_at,
            "last_updated_at": self.last_updated_at,
            "last_error": self.last_error,
            "has_snapshot": self.full_jpeg is not None,
        }

    def detail(self) -> Dict[str, object]:
        data = self.summary()
        data["detections"] = list(self.detections)
        data["missed_frames"] = self.alert_engine.missed_frames
        data["frames_analysed"] = self.frames_analysed
        data["last_http_status"] = self.last_http_status
        return data


class MultiCameraMonitor:
    def __init__(self, detector_service) -> None:
        self.detector_service = detector_service
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        self.lock = Lock()
        self.cameras: Dict[str, CameraState] = {}
        self.model: Optional[YOLO] = None
        self.index_loaded_ts = 0.0
        self.index_error: Optional[str] = None
        self.model_error: Optional[str] = None
        self.sweep_count = 0
        self.current_sweep_started_ts: Optional[float] = None
        self.current_sweep_checked = 0
        self.last_sweep_seconds: Optional[float] = None
        self.last_sweep_finished_at: Optional[str] = None
        self.avg_inference_ms: Optional[float] = None
        self.frames_analysed_total = 0
        self.frames_skipped_unchanged = 0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "FireWatch/1.0"
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=DOWNLOAD_WORKERS, pool_maxsize=DOWNLOAD_WORKERS * 2
        )
        self.session.mount("https://", adapter)

    # ---------- lifecycle ----------

    def start(self) -> None:
        if not MULTI_CAMERA_ENABLED:
            logger.info("Multi-camera monitor disabled (MULTI_CAMERA_ENABLED=false).")
            return
        if self.thread is not None and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = Thread(target=self._run, name="multi-camera", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=10)
            self.thread = None

    # ---------- public read API ----------

    def list_cameras(self) -> List[Dict[str, object]]:
        with self.lock:
            return [camera.summary() for camera in self.cameras.values()]

    def get_camera(self, camera_id: str) -> Optional[Dict[str, object]]:
        with self.lock:
            camera = self.cameras.get(camera_id)
            return camera.detail() if camera else None

    def get_snapshot(self, camera_id: str, size: str) -> Optional[bytes]:
        with self.lock:
            camera = self.cameras.get(camera_id)
            if camera is None:
                return None
            return camera.thumb_jpeg if size == "thumb" else camera.full_jpeg

    def get_thumb_fallback_url(self, camera_id: str) -> Optional[str]:
        with self.lock:
            camera = self.cameras.get(camera_id)
            return camera.thumb_url if camera else None

    def list_alerts(self) -> List[Dict[str, object]]:
        with self.lock:
            alerts = [
                camera.detail()
                for camera in self.cameras.values()
                if camera.alert_engine.alert_active
            ]
        alerts.sort(key=lambda a: a["alert_started_at"] or "", reverse=True)
        return alerts

    def status(self) -> Dict[str, object]:
        with self.lock:
            counts: Dict[str, int] = {}
            for camera in self.cameras.values():
                counts[camera.status] = counts.get(camera.status, 0) + 1
            total = len(self.cameras)
        elapsed = (
            time.time() - self.current_sweep_started_ts
            if self.current_sweep_started_ts
            else None
        )
        return {
            "enabled": MULTI_CAMERA_ENABLED,
            "running": self.thread is not None and self.thread.is_alive(),
            "camera_index_url": CAMERA_INDEX_URL,
            "camera_count": total,
            "status_counts": counts,
            "index_error": self.index_error,
            "model_error": self.model_error,
            "sweep_count": self.sweep_count,
            "current_sweep_checked": self.current_sweep_checked,
            "current_sweep_elapsed_seconds": round(elapsed, 1) if elapsed else None,
            "last_sweep_seconds": self.last_sweep_seconds,
            "last_sweep_finished_at": self.last_sweep_finished_at,
            "avg_inference_ms": self.avg_inference_ms,
            "frames_analysed_total": self.frames_analysed_total,
            "frames_skipped_unchanged": self.frames_skipped_unchanged,
        }

    # ---------- worker ----------

    def _run(self) -> None:
        try:
            self.model = YOLO(str(settings.model_path))
            self.model_error = None
        except Exception as error:  # pragma: no cover - surfaced via /monitor/status
            self.model_error = str(error)
            logger.exception("Multi-camera monitor could not load the model.")
            return

        with ThreadPoolExecutor(
            max_workers=DOWNLOAD_WORKERS, thread_name_prefix="cam-fetch"
        ) as pool:
            while not self.stop_event.is_set():
                if time.time() - self.index_loaded_ts > INDEX_REFRESH_SECONDS:
                    self._refresh_index()
                if not self.cameras:
                    self.stop_event.wait(30)
                    continue

                sweep_start = time.time()
                self._sweep(pool)
                sweep_seconds = time.time() - sweep_start
                if self.stop_event.is_set():
                    break
                self.sweep_count += 1
                self.last_sweep_seconds = round(sweep_seconds, 1)
                self.last_sweep_finished_at = _now_iso()
                logger.info(
                    "Multi-camera sweep %d: %d cameras in %.1fs "
                    "(avg inference %.0f ms, %d analysed, %d unchanged so far).",
                    self.sweep_count,
                    len(self.cameras),
                    sweep_seconds,
                    self.avg_inference_ms or 0.0,
                    self.frames_analysed_total,
                    self.frames_skipped_unchanged,
                )
                # AlertCalifornia frames change about once a minute; do not
                # hammer the CDN if a sweep finished very quickly.
                if sweep_seconds < MIN_SWEEP_SECONDS:
                    self.stop_event.wait(MIN_SWEEP_SECONDS - sweep_seconds)

    def _refresh_index(self) -> None:
        try:
            response = self.session.get(CAMERA_INDEX_URL, timeout=30)
            response.raise_for_status()
            features = response.json().get("features", [])
        except Exception as error:
            self.index_error = f"Camera index fetch failed: {error}"
            logger.warning(self.index_error)
            self.index_loaded_ts = time.time() - INDEX_REFRESH_SECONDS + 300  # retry in 5 min
            return

        seen = set()
        with self.lock:
            for feature in features:
                props = feature.get("properties") or {}
                camera_id = props.get("id")
                if not camera_id:
                    continue
                coords = (feature.get("geometry") or {}).get("coordinates") or [None, None]
                seen.add(camera_id)
                existing = self.cameras.get(camera_id)
                if existing is not None:
                    existing.name = props.get("name") or camera_id
                    existing.lat, existing.lon = coords[1], coords[0]
                    continue
                self.cameras[camera_id] = CameraState(
                    camera_id=camera_id,
                    name=props.get("name") or camera_id,
                    lat=coords[1],
                    lon=coords[0],
                    county=props.get("county"),
                    region=props.get("region"),
                    state=props.get("state"),
                    sponsor=props.get("sponsor"),
                    image_url=FRAME_URL_TEMPLATE.format(camera_id=camera_id),
                    thumb_url=THUMB_URL_TEMPLATE.format(camera_id=camera_id),
                    alert_engine=AlertEngine(
                        min_consecutive_detections=settings.min_consecutive_detections,
                        max_missed_frames=settings.max_missed_frames,
                        alert_confidence_threshold=settings.alert_confidence_threshold,
                    ),
                )
            for camera_id in list(self.cameras):
                if camera_id not in seen:
                    del self.cameras[camera_id]
        self.index_error = None
        self.index_loaded_ts = time.time()
        logger.info("Loaded %d AlertCalifornia cameras from %s.", len(seen), CAMERA_INDEX_URL)

    def _sweep_order(self) -> Iterator[str]:
        """Every camera once, hot cameras first and re-visited during the sweep."""
        now = time.time()
        with self.lock:
            cameras = list(self.cameras.values())
        hot = [c.camera_id for c in cameras if c.is_hot(now)]
        rest = sorted(
            (c for c in cameras if not c.is_hot(now)), key=lambda c: c.last_checked_ts
        )
        yield from hot
        for position, camera in enumerate(rest, start=1):
            yield camera.camera_id
            if hot and position % HOT_RECHECK_EVERY == 0:
                yield from hot

    def _sweep(self, pool: ThreadPoolExecutor) -> None:
        self.current_sweep_started_ts = time.time()
        self.current_sweep_checked = 0
        order = self._sweep_order()
        in_flight: Dict[Future, str] = {}
        max_in_flight = DOWNLOAD_WORKERS * 2
        exhausted = False

        while not self.stop_event.is_set():
            while not exhausted and len(in_flight) < max_in_flight:
                camera_id = next(order, None)
                if camera_id is None:
                    exhausted = True
                    break
                with self.lock:
                    camera = self.cameras.get(camera_id)
                if camera is None:
                    continue
                in_flight[pool.submit(self._download, camera.image_url)] = camera_id
            if not in_flight:
                break
            done, _ = wait(list(in_flight), timeout=1.0, return_when=FIRST_COMPLETED)
            for future in done:
                camera_id = in_flight.pop(future)
                self._process(camera_id, future.result())
                self.current_sweep_checked += 1

        for future in in_flight:
            future.cancel()

    def _download(self, url: str) -> Dict[str, object]:
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as error:
            return {"ok": False, "error": f"Request failed: {error.__class__.__name__}", "status": None}
        if response.status_code != 200:
            return {"ok": False, "error": f"HTTP {response.status_code}", "status": response.status_code}
        if not response.headers.get("Content-Type", "").startswith("image/"):
            return {"ok": False, "error": "Response was not an image", "status": response.status_code}
        return {"ok": True, "content": response.content, "status": response.status_code}

    def _process(self, camera_id: str, result: Dict[str, object]) -> None:
        now = time.time()
        with self.lock:
            camera = self.cameras.get(camera_id)
        if camera is None:
            return

        camera.last_checked_ts = now
        camera.last_checked_at = _now_iso()
        camera.last_http_status = result.get("status")  # type: ignore[assignment]

        if not result["ok"]:
            camera.last_error = str(result["error"])
            if not camera.alert_engine.alert_active:
                camera.status = "error"
            return

        content: bytes = result["content"]  # type: ignore[assignment]
        digest = hashlib.sha1(content).hexdigest()
        if digest == camera.last_hash:
            self.frames_skipped_unchanged += 1
            camera.last_error = None
            if camera.status == "error":
                camera.status = "alert" if camera.alert_engine.alert_active else "ok"
            return

        frame = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            camera.last_error = "Image could not be decoded"
            camera.status = "error"
            return

        started = time.perf_counter()
        try:
            detections = self.detector_service.predict_frame(self.model, frame)
        except Exception as error:
            camera.last_error = f"Prediction failed: {error}"
            camera.status = "error"
            return
        inference_ms = (time.perf_counter() - started) * 1000
        self.avg_inference_ms = round(
            inference_ms
            if self.avg_inference_ms is None
            else self.avg_inference_ms * 0.95 + inference_ms * 0.05,
            1,
        )

        engine = camera.alert_engine
        was_alert = engine.alert_active
        highest = max((float(d["confidence"]) for d in detections), default=0.0)
        engine.update(detection_count=len(detections), highest_confidence=highest)

        annotated = self.detector_service._build_annotated_frame(
            frame=self._shrink(frame, FULL_SNAPSHOT_MAX_WIDTH, detections),
            detections=self._scaled_detections(frame, detections, FULL_SNAPSHOT_MAX_WIDTH),
            alert_active=engine.alert_active,
            consecutive_detections=engine.consecutive_detections,
        )
        thumb = None
        if annotated is not None:
            decoded = cv2.imdecode(np.frombuffer(annotated, np.uint8), cv2.IMREAD_COLOR)
            small = self._shrink(decoded, THUMB_WIDTH, [])
            ok, encoded = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            thumb = encoded.tobytes() if ok else None

        with self.lock:
            camera.last_hash = digest
            camera.last_error = None
            camera.last_updated_at = _now_iso()
            camera.detections = detections
            camera.frames_analysed += 1
            if detections:
                camera.last_detection_ts = now
            if engine.alert_active and not was_alert:
                camera.alert_started_at = _now_iso()
                logger.warning(
                    "ALERT: %s (%s) - %d detection(s), top confidence %.2f.",
                    camera.name, camera.camera_id, len(detections), highest,
                )
            if not engine.alert_active:
                camera.alert_started_at = None
            camera.status = "alert" if engine.alert_active else "ok"
            camera.full_jpeg = annotated
            camera.thumb_jpeg = thumb
        self.frames_analysed_total += 1

    @staticmethod
    def _shrink(frame, max_width: int, _detections):
        height, width = frame.shape[:2]
        if width <= max_width:
            return frame
        scale = max_width / width
        return cv2.resize(frame, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)

    @staticmethod
    def _scaled_detections(frame, detections: List[Dict[str, object]], max_width: int):
        width = frame.shape[1]
        if width <= max_width:
            return detections
        scale = max_width / width
        scaled = []
        for detection in detections:
            copy = dict(detection)
            for key in ("x1", "y1", "x2", "y2"):
                copy[key] = int(int(detection[key]) * scale)
            scaled.append(copy)
        return scaled


from app.detector import detector_service  # noqa: E402  (no circular import)

multi_camera_monitor = MultiCameraMonitor(detector_service)
