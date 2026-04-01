class AlertEngine:
    def __init__(
        self,
        min_consecutive_detections: int,
        max_missed_frames: int,
        alert_confidence_threshold: float,
    ) -> None:
        self.min_consecutive_detections = min_consecutive_detections
        self.max_missed_frames = max_missed_frames
        self.alert_confidence_threshold = alert_confidence_threshold
        self.consecutive_detections = 0
        self.missed_frames = 0
        self.alert_active = False

    def reset(self) -> None:
        self.consecutive_detections = 0
        self.missed_frames = 0
        self.alert_active = False

    def update(
        self,
        detection_count: int,
        highest_confidence: float,
    ) -> None:
        if detection_count > 0:
            self.consecutive_detections += 1
            self.missed_frames = 0
        else:
            self.missed_frames += 1
            self.consecutive_detections = 0

        if highest_confidence >= self.alert_confidence_threshold:
            self.alert_active = True
            return

        if self.consecutive_detections >= self.min_consecutive_detections:
            self.alert_active = True

        if self.missed_frames >= self.max_missed_frames:
            self.alert_active = False
