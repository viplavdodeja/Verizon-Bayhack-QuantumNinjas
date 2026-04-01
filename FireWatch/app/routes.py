from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.models import DetectionsResponse, HealthResponse, StatusResponse
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
    )


@router.get("/detections", response_model=DetectionsResponse)
def get_detections() -> DetectionsResponse:
    snapshot = detector_state.get_snapshot()
    latest_detections = snapshot["latest_detections"]

    return DetectionsResponse(
        detection_count=len(latest_detections),
        latest_detections=latest_detections,
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
