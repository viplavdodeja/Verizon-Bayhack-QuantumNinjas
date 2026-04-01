from datetime import datetime, timezone
import logging
from threading import Event, RLock, Thread
from typing import Dict, List, Optional

import cv2
from ultralytics import YOLO

from app.config import settings
from app.services.alert_engine import AlertEngine
from app.sources.base_source import BaseFrameSource
from app.sources.base_source import FrameReadResult
from app.sources.source_factory import create_source
from app.state import detector_state


logger = logging.getLogger(__name__)


class FireDetectorService:
    def __init__(self) -> None:
        self.stop_event = Event()
        self.worker_thread: Optional[Thread] = None
        self.model: Optional[YOLO] = None
        self.source: Optional[BaseFrameSource] = None
        self.control_lock = RLock()
        self.alert_engine = AlertEngine(
            min_consecutive_detections=settings.min_consecutive_detections,
            max_missed_frames=settings.max_missed_frames,
            alert_confidence_threshold=settings.alert_confidence_threshold,
        )

    def start(self) -> None:
        with self.control_lock:
            if self.worker_thread is not None and self.worker_thread.is_alive():
                return

            self.stop_event.clear()
            self.worker_thread = Thread(target=self._run_loop, daemon=True)
            self.worker_thread.start()

    def stop(self) -> None:
        with self.control_lock:
            self._stop_locked()

    def reconfigure_source(
        self,
        source_type: str,
        camera_id: Optional[str],
        image_url: Optional[str],
    ) -> str:
        with self.control_lock:
            if source_type == "webcam":
                source_name = settings.switch_to_webcam()
            elif source_type == "arcgis":
                source_name = settings.switch_to_arcgis(
                    camera_id=camera_id,
                    image_url=image_url,
                )
            else:
                raise ValueError("Unsupported source type.")

            self._stop_locked()
            detector_state.reset_runtime_state(
                source_type=settings.get_source_type(),
                source_name=source_name,
            )
            self.alert_engine.reset()
            self.start()
            return source_name

    def _stop_locked(self) -> None:
        self.stop_event.set()
        if self.worker_thread is not None:
            self.worker_thread.join(timeout=5)
            self.worker_thread = None
        if self.source is not None:
            self.source.release()
            self.source = None

    def _run_loop(self) -> None:
        try:
            active_source_type = settings.get_source_type()
            detector_state.set_system_status("starting")
            detector_state.set_source_details(
                active_source_type,
                settings.get_default_source_name(),
            )

            if active_source_type == "arcgis":
                logger.info(settings.get_arcgis_startup_status_message())
            else:
                logger.info("Webcam mode is configured correctly.")

            self._load_model()
            if self.model is None:
                detector_state.set_system_status("model_error")
                return

            self.source = create_source()
            if self.source is None:
                detector_state.set_system_status("source_error")
                return

            detector_state.set_source_details(
                self.source.get_source_type(),
                self.source.get_source_name(),
            )

            source_connected = self.source.connect()
            detector_state.set_source_connected(source_connected)

            if not source_connected:
                detector_state.set_system_status("source_error")
                return

            detector_state.set_system_status("running")

            while not self.stop_event.is_set():
                read_result = self.source.read()
                detector_state.update_source_diagnostics(
                    last_source_error=read_result.last_source_error,
                    last_successful_fetch_at=read_result.last_successful_fetch_at,
                    last_fetch_http_status=read_result.last_fetch_http_status,
                )

                if read_result.is_duplicate:
                    logger.info(read_result.message)
                    detector_state.set_source_connected(True)
                    detector_state.set_system_status("running")
                    continue

                if not read_result.success or read_result.frame is None:
                    logger.warning(read_result.message)
                    detector_state.set_source_connected(False)
                    detector_state.set_system_status("source_read_error")
                    continue

                detector_state.set_source_connected(True)
                detector_state.set_source_details(
                    self.source.get_source_type(),
                    self.source.get_source_name(),
                )
                detector_state.set_system_status("running")

                valid_detections = self._predict(read_result)
                highest_confidence = self._get_highest_confidence(valid_detections)
                self.alert_engine.update(
                    detection_count=len(valid_detections),
                    highest_confidence=highest_confidence,
                )

                annotated_frame_bytes = self._build_annotated_frame(
                    frame=read_result.frame,
                    detections=valid_detections,
                    alert_active=self.alert_engine.alert_active,
                    consecutive_detections=self.alert_engine.consecutive_detections,
                )

                detector_state.update_detection_state(
                    alert_active=self.alert_engine.alert_active,
                    consecutive_detections=self.alert_engine.consecutive_detections,
                    missed_frames=self.alert_engine.missed_frames,
                    latest_detections=valid_detections,
                    annotated_frame_bytes=annotated_frame_bytes,
                )
        finally:
            if self.source is not None:
                self.source.release()
                self.source = None
            detector_state.set_source_connected(False)
            if self.stop_event.is_set():
                detector_state.set_system_status("stopped")

    def _load_model(self) -> None:
        if self.model is not None:
            detector_state.set_model_loaded(True)
            detector_state.set_model_diagnostics(
                model_path=str(settings.model_path),
                model_error=None,
            )
            return

        try:
            self.model = YOLO(str(settings.model_path))
            detector_state.set_model_loaded(True)
            detector_state.set_model_diagnostics(
                model_path=str(settings.model_path),
                model_error=None,
            )
        except Exception as error:
            self.model = None
            detector_state.set_model_loaded(False)
            detector_state.set_model_diagnostics(
                model_path=str(settings.model_path),
                model_error=str(error),
            )
            logger.exception("Failed to load YOLO model from %s", settings.model_path)

    def _predict(self, read_result: FrameReadResult) -> List[Dict[str, object]]:
        if self.model is None or read_result.frame is None:
            return []

        try:
            results = self.model.predict(
                source=read_result.frame,
                conf=settings.confidence_threshold,
                iou=settings.iou_threshold,
                imgsz=settings.img_size,
                verbose=False,
            )
        except Exception:
            detector_state.set_system_status("prediction_error")
            return []

        result = results[0]
        boxes = result.boxes

        valid_detections: List[Dict[str, object]] = []
        frame_height = read_result.frame.shape[0]
        frame_width = read_result.frame.shape[1]
        frame_area = frame_width * frame_height

        if boxes is None or len(boxes) == 0:
            return valid_detections

        for box in boxes:
            class_index = int(box.cls[0])
            label = self.model.names[class_index]
            confidence = float(box.conf[0])

            coordinates = box.xyxy[0].tolist()
            x1 = int(coordinates[0])
            y1 = int(coordinates[1])
            x2 = int(coordinates[2])
            y2 = int(coordinates[3])

            box_width = max(0, x2 - x1)
            box_height = max(0, y2 - y1)
            box_area = box_width * box_height
            area_ratio = box_area / frame_area

            if area_ratio > settings.max_box_area_ratio:
                continue

            detection_record: Dict[str, object] = {
                "label": label,
                "confidence": confidence,
                "area_ratio": area_ratio,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            valid_detections.append(detection_record)

        return valid_detections

    def _get_highest_confidence(
        self,
        detections: List[Dict[str, object]],
    ) -> float:
        highest_confidence = 0.0

        for detection in detections:
            confidence = float(detection["confidence"])
            if confidence > highest_confidence:
                highest_confidence = confidence

        return highest_confidence

    def _build_annotated_frame(
        self,
        frame,
        detections: List[Dict[str, object]],
        alert_active: bool,
        consecutive_detections: int,
    ) -> Optional[bytes]:
        annotated_frame = frame.copy()

        for detection in detections:
            label_text = (
                f"{detection['label']} {float(detection['confidence']):.2f}"
            )

            cv2.rectangle(
                annotated_frame,
                (int(detection["x1"]), int(detection["y1"])),
                (int(detection["x2"]), int(detection["y2"])),
                (0, 0, 255),
                2,
            )

            cv2.putText(
                annotated_frame,
                label_text,
                (int(detection["x1"]), max(20, int(detection["y1"]) - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        if alert_active:
            status_text = "ALERT ACTIVE"
            status_color = (0, 0, 255)
        else:
            status_text = "Monitoring"
            status_color = (0, 255, 0)

        cv2.putText(
            annotated_frame,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            status_color,
            2,
        )

        cv2.putText(
            annotated_frame,
            f"Consecutive detections: {consecutive_detections}",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        encode_parameters = [
            int(cv2.IMWRITE_JPEG_QUALITY),
            settings.snapshot_jpeg_quality,
        ]
        was_encoded, encoded_image = cv2.imencode(
            ".jpg",
            annotated_frame,
            encode_parameters,
        )

        if not was_encoded:
            return None
        return encoded_image.tobytes()


detector_service = FireDetectorService()
