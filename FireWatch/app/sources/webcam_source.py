from typing import Optional
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

    def connect(self) -> bool:
        self.capture = cv2.VideoCapture(self.camera_index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        return bool(self.capture.isOpened())

    def read(self) -> FrameReadResult:
        self._wait_for_poll_interval()

        if self.capture is None:
            return FrameReadResult(
                frame=None,
                is_duplicate=False,
                success=False,
                message="Webcam is not initialized.",
            )

        was_read, frame = self.capture.read()
        if not was_read:
            return FrameReadResult(
                frame=None,
                is_duplicate=False,
                success=False,
                message="Failed to read frame from webcam.",
            )

        return FrameReadResult(
            frame=frame,
            is_duplicate=False,
            success=True,
            message="Webcam frame captured.",
        )

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def _wait_for_poll_interval(self) -> None:
        if self.poll_interval_seconds <= 0:
            self.last_read_started_at = time.time()
            return

        now = time.time()
        elapsed = now - self.last_read_started_at

        if self.last_read_started_at > 0 and elapsed < self.poll_interval_seconds:
            time.sleep(self.poll_interval_seconds - elapsed)

        self.last_read_started_at = time.time()
