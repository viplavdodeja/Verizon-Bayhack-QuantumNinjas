from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional


class DetectorState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._state: Dict[str, object] = {
            "alert_active": False,
            "consecutive_detections": 0,
            "missed_frames": 0,
            "latest_detections": [],
            "last_updated": None,
            "source_name": "webcam",
            "system_status": "starting",
            "model_loaded": False,
            "source_connected": False,
            "latest_annotated_frame_bytes": None,
        }

    def set_source_name(self, source_name: str) -> None:
        with self._lock:
            self._state["source_name"] = source_name

    def set_system_status(self, system_status: str) -> None:
        with self._lock:
            self._state["system_status"] = system_status
            self._state["last_updated"] = self._iso_timestamp()

    def set_model_loaded(self, model_loaded: bool) -> None:
        with self._lock:
            self._state["model_loaded"] = model_loaded
            self._state["last_updated"] = self._iso_timestamp()

    def set_source_connected(self, source_connected: bool) -> None:
        with self._lock:
            self._state["source_connected"] = source_connected
            self._state["last_updated"] = self._iso_timestamp()

    def update_detection_state(
        self,
        alert_active: bool,
        consecutive_detections: int,
        missed_frames: int,
        latest_detections: List[Dict[str, object]],
        annotated_frame_bytes: Optional[bytes],
    ) -> None:
        with self._lock:
            self._state["alert_active"] = alert_active
            self._state["consecutive_detections"] = consecutive_detections
            self._state["missed_frames"] = missed_frames
            self._state["latest_detections"] = latest_detections
            self._state["latest_annotated_frame_bytes"] = annotated_frame_bytes
            self._state["last_updated"] = self._iso_timestamp()

    def get_snapshot(self) -> Dict[str, object]:
        with self._lock:
            copied_state: Dict[str, object] = {}
            for key, value in self._state.items():
                if key == "latest_detections":
                    copied_detections: List[Dict[str, object]] = []
                    for detection in value:
                        copied_detection: Dict[str, object] = {}
                        for detection_key, detection_value in detection.items():
                            copied_detection[detection_key] = detection_value
                        copied_detections.append(copied_detection)
                    copied_state[key] = copied_detections
                elif key == "latest_annotated_frame_bytes" and value is not None:
                    copied_state[key] = bytes(value)
                else:
                    copied_state[key] = value
            return copied_state

    def get_annotated_frame_bytes(self) -> Optional[bytes]:
        with self._lock:
            frame_bytes = self._state["latest_annotated_frame_bytes"]
            if frame_bytes is None:
                return None
            return bytes(frame_bytes)

    def _iso_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()


detector_state = DetectorState()
