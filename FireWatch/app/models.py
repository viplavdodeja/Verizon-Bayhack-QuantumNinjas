from typing import List, Optional

from pydantic import BaseModel


class DetectionRecord(BaseModel):
    label: str
    confidence: float
    area_ratio: float
    x1: int
    y1: int
    x2: int
    y2: int
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    source_connected: bool


class StatusResponse(BaseModel):
    alert_active: bool
    consecutive_detections: int
    missed_frames: int
    source_name: str
    last_updated: Optional[str]
    system_status: str


class DetectionsResponse(BaseModel):
    detection_count: int
    latest_detections: List[DetectionRecord]
