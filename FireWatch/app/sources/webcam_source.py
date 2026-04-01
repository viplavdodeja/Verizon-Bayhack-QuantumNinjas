from datetime import datetime, timezone
import os
from typing import List, Optional, Tuple
import time

import cv2

from app.sources.base_source import BaseFrameSource
from app.sources.base_source import FrameReadResult


class WebcamSource(BaseFrameSource):
    def __init__(
        self,
        camera_index: int,
        frame_width: int,
        frame_height: int,
        poll_interval_seconds: float,
    ) -> None:
        super().__init__("webcam", "webcam")
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.poll_interval_seconds = poll_interval_seconds
        self.capture: Optional[cv2.VideoCapture] = None
        self.last_read_started_at = 0.0
        self.last_successful_read_at: Optional[str] = None
        self.backend_attempts = self._build_backend_attempts()
        self.current_backend_index = 0
        self.current_backend_name = "default"
        self.read_attempts_per_backend = 4
        self.reconnect_delay_seconds = 0.2

    def connect(self) -> bool:
        return self._connect_to_available_backend(0)

    def read(self) -> FrameReadResult:
        self._wait_for_poll_interval()

        if self.capture is None:
            return FrameReadResult(
                frame=None,
                is_duplicate=False,
                success=False,
                message="Webcam is not initialized.",
                last_source_error="Webcam is not initialized.",
                last_successful_fetch_at=self.last_successful_read_at,
                last_fetch_http_status=None,
            )

        frame = self._read_frame_with_retries(self.capture)
        if frame is not None:
            self.last_successful_read_at = self._now_iso()
            return FrameReadResult(
                frame=frame,
                is_duplicate=False,
                success=True,
                message=f"Webcam frame captured with {self.current_backend_name}.",
                last_source_error=None,
                last_successful_fetch_at=self.last_successful_read_at,
                last_fetch_http_status=None,
            )

        read_error_message = (
            f"Failed to read frame from webcam using {self.current_backend_name}."
        )

        recovered = self._recover_capture()
        if recovered and self.capture is not None:
            recovered_frame = self._read_frame_with_retries(self.capture)
            if recovered_frame is not None:
                self.last_successful_read_at = self._now_iso()
                return FrameReadResult(
                    frame=recovered_frame,
                    is_duplicate=False,
                    success=True,
                    message=f"Recovered webcam capture using {self.current_backend_name}.",
                    last_source_error=None,
                    last_successful_fetch_at=self.last_successful_read_at,
                    last_fetch_http_status=None,
                )

        return FrameReadResult(
            frame=None,
            is_duplicate=False,
            success=False,
            message=read_error_message,
            last_source_error=read_error_message,
            last_successful_fetch_at=self.last_successful_read_at,
            last_fetch_http_status=None,
        )

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def _build_backend_attempts(self) -> List[Tuple[str, Optional[int]]]:
        backend_attempts: List[Tuple[str, Optional[int]]] = []

        if os.name == "nt":
            backend_attempts.append(("dshow", cv2.CAP_DSHOW))
            backend_attempts.append(("msmf", cv2.CAP_MSMF))

        backend_attempts.append(("default", None))
        return backend_attempts

    def _connect_to_available_backend(self, start_index: int) -> bool:
        self.release()

        for backend_index in range(start_index, len(self.backend_attempts)):
            backend_name, backend_code = self.backend_attempts[backend_index]
            capture = self._open_capture(backend_code)
            if capture is None:
                continue

            first_frame = self._read_frame_with_retries(capture)
            if first_frame is None:
                capture.release()
                continue

            self.capture = capture
            self.current_backend_index = backend_index
            self.current_backend_name = backend_name
            self.source_name = f"webcam-{backend_name}"
            self.last_successful_read_at = self._now_iso()
            return True

        return False

    def _open_capture(self, backend_code: Optional[int]) -> Optional[cv2.VideoCapture]:
        if backend_code is None:
            capture = cv2.VideoCapture(self.camera_index)
        else:
            capture = cv2.VideoCapture(self.camera_index, backend_code)

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

        if not capture.isOpened():
            capture.release()
            return None

        return capture

    def _recover_capture(self) -> bool:
        time.sleep(self.reconnect_delay_seconds)
        next_backend_index = self.current_backend_index + 1
        if self._connect_to_available_backend(next_backend_index):
            return True

        return self._connect_to_available_backend(0)

    def _read_frame_with_retries(self, capture: cv2.VideoCapture):
        for attempt_index in range(self.read_attempts_per_backend):
            was_read, frame = capture.read()
            if was_read and frame is not None:
                return frame

            if attempt_index < self.read_attempts_per_backend - 1:
                time.sleep(self.reconnect_delay_seconds)

        return None

    def _wait_for_poll_interval(self) -> None:
        if self.poll_interval_seconds <= 0:
            self.last_read_started_at = time.time()
            return

        now = time.time()
        elapsed = now - self.last_read_started_at

        if self.last_read_started_at > 0 and elapsed < self.poll_interval_seconds:
            time.sleep(self.poll_interval_seconds - elapsed)

        self.last_read_started_at = time.time()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
