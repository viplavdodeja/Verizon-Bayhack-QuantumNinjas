from datetime import datetime, timezone
from threading import Event, Thread
import time
from typing import Dict, List, Optional

import cv2
from ultralytics import YOLO

from app.config import settings
from app.services.alert_engine import AlertEngine
from app.sources.base_source import BaseFrameSource
from app.sources.webcam_source import WebcamSource
from app.state import detector_state


class FireDetectorService:
    def __init__(self) -> None:
        self.stop_event = Event()
        self.worker_thread: Optional[Thread] = None
        self.model: Optional[YOLO] = None
        self.source: Optional[BaseFrameSource] = None
        self.alert_engine = AlertEngine(
            min_consecutive_detections=settings.min_consecutive_detections,
            max_missed_frames=settings.max_missed_frames,
        )

    def start(self) -> None:
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return

        self.stop_event.clear()
        self.worker_thread = Thread(target=self._run_loop, daemon=True)
        self.worker_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.worker_thread is not None:
            self.worker_thread.join(timeout=5)
        if self.source is not None:
            self.source.release()
            self.source = None

    def _run_loop(self) -> None:
        try:
            detector_state.set_system_status("starting")
            detector_state.set_source_name(settings.source_name)

            self._load_model()
            if self.model is None:
                detector_state.set_system_status("model_error")
                return

            self.source = self._build_source()
            if self.source is None:
                detector_state.set_system_status("source_error")
                return

            detector_state.set_source_name(self.source.source_name)

            source_connected = self.source.connect()
            detector_state.set_source_connected(source_connected)

            if not source_connected:
                detector_state.set_system_status("source_error")
                return

            detector_state.set_system_status("running")

            while not self.stop_event.is_set():
                frame = self.source.read_frame()
                if frame is None:
                    detector_state.set_source_connected(False)
                    detector_state.set_system_status("source_read_error")
                    time.sleep(settings.frame_poll_interval_seconds)
                    continue

                detector_state.set_source_connected(True)
                detector_state.set_system_status("running")

                valid_detections = self._predict(frame)
                self.alert_engine.update(len(valid_detections))

                annotated_frame_bytes = self._build_annotated_frame(
                    frame=frame,
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

                time.sleep(settings.frame_poll_interval_seconds)
        finally:
            if self.source is not None:
                self.source.release()
                self.source = None
            detector_state.set_system_status("stopped")
            detector_state.set_source_connected(False)

    def _load_model(self) -> None:
        try:
            self.model = YOLO(str(settings.model_path))
            detector_state.set_model_loaded(True)
        except Exception:
            self.model = None
            detector_state.set_model_loaded(False)

    def _build_source(self) -> Optional[BaseFrameSource]:
        if settings.source_name == "webcam":
            return WebcamSource(
                camera_index=settings.camera_index,
                frame_width=settings.frame_width,
                frame_height=settings.frame_height,
            )
        return None

    def _predict(self, frame) -> List[Dict[str, object]]:
        if self.model is None:
            return []

        try:
            results = self.model.predict(
                source=frame,
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
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
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
