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
    last_source_error: Optional[str]
    last_successful_fetch_at: Optional[str]
    last_fetch_http_status: Optional[int]


class DetectionsResponse(BaseModel):
    detection_count: int
    latest_detections: List[DetectionRecord]


class SourceResponse(BaseModel):
    source_type: str
    source_name: str
    source_connected: bool
    poll_interval_seconds: float
    image_url: Optional[str]
    auth_mode: str
    last_source_error: Optional[str]
    last_successful_fetch_at: Optional[str]
    last_fetch_http_status: Optional[int]
