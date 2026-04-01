from typing import Optional

from app.config import settings
from app.sources.arcgis_source import ArcGISImageSource
from app.sources.base_source import BaseFrameSource
from app.sources.webcam_source import WebcamSource


def create_source() -> Optional[BaseFrameSource]:
    if settings.source_type == "arcgis":
        return ArcGISImageSource(
            image_url=settings.get_arcgis_source_url(),
            poll_interval_seconds=settings.arcgis_poll_interval_seconds,
            request_timeout_seconds=settings.arcgis_request_timeout_seconds,
            auth_mode=settings.arcgis_auth_mode,
            api_key_file=settings.arcgis_api_key_file,
            api_key_query_param_name=settings.arcgis_api_key_query_param_name,
            auth_header_name=settings.arcgis_auth_header_name,
            auth_header_prefix=settings.arcgis_auth_header_prefix,
        )

    if settings.source_type == "webcam":
        return WebcamSource(
            camera_index=settings.camera_index,
            frame_width=settings.frame_width,
            frame_height=settings.frame_height,
            poll_interval_seconds=settings.frame_poll_interval_seconds,
        )

    return None
