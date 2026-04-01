from typing import Optional

import cv2
import numpy as np

from app.sources.base_source import BaseFrameSource


class WebcamSource(BaseFrameSource):
    def __init__(self, camera_index: int, frame_width: int, frame_height: int) -> None:
        super().__init__("webcam")
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.capture: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        self.capture = cv2.VideoCapture(self.camera_index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        return bool(self.capture.isOpened())

    def read_frame(self) -> Optional[np.ndarray]:
        if self.capture is None:
            return None

        was_read, frame = self.capture.read()
        if not was_read:
            return None
        return frame

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
