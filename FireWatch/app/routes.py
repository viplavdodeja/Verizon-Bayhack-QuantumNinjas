from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse

from app.config import settings
from app.detector import detector_service
from app.models import CameraListResponse
from app.models import DetectionsResponse
from app.models import HealthResponse
from app.models import SourceResponse
from app.models import SourceSelectRequest
from app.models import SourceSelectResponse
from app.models import StatusResponse
from app.state import detector_state


router = APIRouter()


def _build_source_response() -> SourceResponse:
    snapshot = detector_state.get_snapshot()
    active_source_type = settings.get_source_type()

    image_url = None
    selected_camera_id = None
    auth_mode = "none"

    if active_source_type == "arcgis":
        image_url = settings.get_arcgis_source_url()
        selected_camera_id = settings.get_selected_arcgis_camera_id()
        auth_mode = settings.arcgis_auth_mode

    return SourceResponse(
        source_type=str(snapshot["source_type"]),
        source_name=str(snapshot["source_name"]),
        source_connected=bool(snapshot["source_connected"]),
        poll_interval_seconds=settings.get_active_poll_interval_seconds(),
        image_url=image_url,
        auth_mode=auth_mode,
        selected_camera_id=selected_camera_id,
        last_source_error=snapshot["last_source_error"],
        last_successful_fetch_at=snapshot["last_successful_fetch_at"],
        last_fetch_http_status=snapshot["last_fetch_http_status"],
    )


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    snapshot = detector_state.get_snapshot()

    return HealthResponse(
        status=str(snapshot["system_status"]),
        model_loaded=bool(snapshot["model_loaded"]),
        source_connected=bool(snapshot["source_connected"]),
        model_path=snapshot["model_path"],
        model_error=snapshot["model_error"],
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
        model_path=snapshot["model_path"],
        model_error=snapshot["model_error"],
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
    return _build_source_response()


@router.get("/cameras", response_model=CameraListResponse)
def get_arcgis_cameras() -> CameraListResponse:
    return CameraListResponse(cameras=settings.list_arcgis_cameras())


@router.post("/source/select", response_model=SourceSelectResponse)
def select_source(payload: SourceSelectRequest) -> SourceSelectResponse:
    try:
        source_name = detector_service.reconfigure_source(
            source_type=payload.source_type,
            camera_id=payload.camera_id,
            image_url=payload.image_url,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return SourceSelectResponse(
        status="ok",
        message=f"Switched active source to {source_name}.",
        source=_build_source_response(),
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
