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
    model_path: Optional[str]
    model_error: Optional[str]


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
    model_path: Optional[str]
    model_error: Optional[str]


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
    selected_camera_id: Optional[str]
    last_source_error: Optional[str]
    last_successful_fetch_at: Optional[str]
    last_fetch_http_status: Optional[int]


class CameraOption(BaseModel):
    camera_id: str
    name: str
    region: str
    image_url: str


class CameraListResponse(BaseModel):
    cameras: List[CameraOption]


class SourceSelectRequest(BaseModel):
    source_type: str
    camera_id: Optional[str] = None
    image_url: Optional[str] = None


class SourceSelectResponse(BaseModel):
    status: str
    message: str
    source: SourceResponse
