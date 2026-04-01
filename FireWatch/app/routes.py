from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import DetectionsResponse, HealthResponse, SourceResponse, StatusResponse
from app.state import detector_state


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    snapshot = detector_state.get_snapshot()

    return HealthResponse(
        status=str(snapshot["system_status"]),
        model_loaded=bool(snapshot["model_loaded"]),
        source_connected=bool(snapshot["source_connected"]),
    )


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    snapshot = detector_state.get_snapshot()

    return StatusResponse(
        alert_active=bool(snapshot["alert_active"]),
        consecutive_detections=int(snapshot["consecutive_detections"]),
        missed_frames=int(snapshot["missed_frames"]),
        source_name=str(snapshot["source_name"]),
        last_updated=snapshot["last_updated"],
        system_status=str(snapshot["system_status"]),
        last_source_error=snapshot["last_source_error"],
        last_successful_fetch_at=snapshot["last_successful_fetch_at"],
        last_fetch_http_status=snapshot["last_fetch_http_status"],
    )


@router.get("/detections", response_model=DetectionsResponse)
def get_detections() -> DetectionsResponse:
    snapshot = detector_state.get_snapshot()
    latest_detections = snapshot["latest_detections"]

    return DetectionsResponse(
        detection_count=len(latest_detections),
        latest_detections=latest_detections,
    )


@router.get("/source", response_model=SourceResponse)
def get_source() -> SourceResponse:
    snapshot = detector_state.get_snapshot()

    image_url = None
    if settings.source_type == "arcgis" and settings.get_arcgis_source_url() != "":
        image_url = settings.get_arcgis_source_url()

    auth_mode = "none"
    if settings.source_type == "arcgis":
        auth_mode = settings.arcgis_auth_mode

    return SourceResponse(
        source_type=str(snapshot["source_type"]),
        source_name=str(snapshot["source_name"]),
        source_connected=bool(snapshot["source_connected"]),
        poll_interval_seconds=settings.get_active_poll_interval_seconds(),
        image_url=image_url,
        auth_mode=auth_mode,
        last_source_error=snapshot["last_source_error"],
        last_successful_fetch_at=snapshot["last_successful_fetch_at"],
        last_fetch_http_status=snapshot["last_fetch_http_status"],
    )


@router.get("/snapshot")
def get_snapshot() -> Response:
    frame_bytes = detector_state.get_annotated_frame_bytes()
    if frame_bytes is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "No annotated frame available yet."},
        )

    return Response(content=frame_bytes, media_type="image/jpeg")
