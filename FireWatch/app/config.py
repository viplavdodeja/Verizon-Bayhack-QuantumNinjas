from pathlib import Path
import os
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_PROJECT_DIR = BASE_DIR.parent / "fire_test2"
DEFAULT_MODEL_PATH = REFERENCE_PROJECT_DIR / "firedetect-11s.pt"


def _read_env(primary_name: str, legacy_name: str, default_value: str) -> str:
    primary_value = os.getenv(primary_name)
    if primary_value is not None:
        return primary_value

    legacy_value = os.getenv(legacy_name)
    if legacy_value is not None:
        return legacy_value

    return default_value


def read_secret_file(secret_file_path: Path) -> Optional[str]:
    if not secret_file_path.exists():
        return None

    try:
        secret_value = secret_file_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None

    if secret_value == "":
        return None

    return secret_value


def mask_secret(secret_value: Optional[str]) -> str:
    if secret_value is None or secret_value == "":
        return "(missing)"

    if len(secret_value) <= 4:
        return "*" * len(secret_value)

    masked_prefix = "*" * (len(secret_value) - 4)
    visible_suffix = secret_value[-4:]
    return f"{masked_prefix}{visible_suffix}"


class Settings:
    def __init__(self) -> None:
        self.app_name = "FireWatch Backend"
        self.model_path = Path(
            _read_env("MODEL_PATH", "FIREWATCH_MODEL_PATH", str(DEFAULT_MODEL_PATH))
        )
        self.source_type = _read_env("SOURCE_TYPE", "FIREWATCH_SOURCE_TYPE", "webcam")
        self.camera_index = int(
            _read_env("CAMERA_INDEX", "FIREWATCH_CAMERA_INDEX", "0")
        )
        self.frame_width = int(
            _read_env("FRAME_WIDTH", "FIREWATCH_FRAME_WIDTH", "640")
        )
        self.frame_height = int(
            _read_env("FRAME_HEIGHT", "FIREWATCH_FRAME_HEIGHT", "480")
        )
        self.img_size = int(_read_env("IMG_SIZE", "FIREWATCH_IMG_SIZE", "640"))
        self.confidence_threshold = float(
            _read_env(
                "CONFIDENCE_THRESHOLD",
                "FIREWATCH_CONFIDENCE_THRESHOLD",
                "0.40",
            )
        )
        self.iou_threshold = float(
            _read_env("IOU_THRESHOLD", "FIREWATCH_IOU_THRESHOLD", "0.45")
        )
        self.min_consecutive_detections = int(
            _read_env(
                "MIN_CONSECUTIVE_DETECTIONS",
                "FIREWATCH_MIN_CONSECUTIVE_DETECTIONS",
                "3",
            )
        )
        self.max_missed_frames = int(
            _read_env("MAX_MISSED_FRAMES", "FIREWATCH_MAX_MISSED_FRAMES", "5")
        )
        self.max_box_area_ratio = float(
            _read_env("MAX_BOX_AREA_RATIO", "FIREWATCH_MAX_BOX_AREA_RATIO", "0.70")
        )
        self.frame_poll_interval_seconds = float(
            _read_env(
                "FRAME_POLL_INTERVAL_SECONDS",
                "FIREWATCH_FRAME_POLL_INTERVAL_SECONDS",
                "0.05",
            )
        )
        self.snapshot_jpeg_quality = int(
            _read_env(
                "SNAPSHOT_JPEG_QUALITY",
                "FIREWATCH_SNAPSHOT_JPEG_QUALITY",
                "85",
            )
        )
        self.arcgis_image_url = os.getenv("ARCGIS_IMAGE_URL", "").strip()
        self.arcgis_poll_interval_seconds = float(
            os.getenv("ARCGIS_POLL_INTERVAL_SECONDS", "5.0")
        )
        self.arcgis_request_timeout_seconds = float(
            os.getenv("ARCGIS_REQUEST_TIMEOUT_SECONDS", "10.0")
        )
        self.arcgis_auth_mode = os.getenv("ARCGIS_AUTH_MODE", "none").strip().lower()
        self.arcgis_api_key_file = Path(
            os.getenv("ARCGIS_API_KEY_FILE", str(BASE_DIR / "secret.txt"))
        )
        self.arcgis_api_key_query_param_name = os.getenv(
            "ARCGIS_API_KEY_QUERY_PARAM_NAME",
            "token",
        ).strip()
        self.arcgis_auth_header_name = os.getenv(
            "ARCGIS_AUTH_HEADER_NAME",
            "Authorization",
        ).strip()
        self.arcgis_auth_header_prefix = os.getenv(
            "ARCGIS_AUTH_HEADER_PREFIX",
            "Bearer ",
        )

    def get_default_source_name(self) -> str:
        if self.source_type == "arcgis":
            return "arcgis-image"
        return "webcam"

    def get_active_poll_interval_seconds(self) -> float:
        if self.source_type == "arcgis":
            return self.arcgis_poll_interval_seconds
        return self.frame_poll_interval_seconds

    def get_arcgis_source_url(self) -> str:
        if self.arcgis_image_url == "":
            return ""
        return self.arcgis_image_url

    def read_arcgis_api_key(self) -> Optional[str]:
        return read_secret_file(self.arcgis_api_key_file)

    def get_masked_arcgis_api_key(self) -> str:
        return mask_secret(self.read_arcgis_api_key())

    def get_arcgis_startup_status_message(self) -> str:
        if self.source_type != "arcgis":
            return "ArcGIS mode is not active."

        if self.arcgis_image_url == "":
            return "ArcGIS mode is not configured correctly: ARCGIS_IMAGE_URL is empty."

        if self.arcgis_auth_mode not in ["none", "query", "header"]:
            return (
                "ArcGIS mode is not configured correctly: "
                "ARCGIS_AUTH_MODE must be none, query, or header."
            )

        if self.arcgis_auth_mode == "none":
            return "ArcGIS mode is configured correctly with public image access."

        api_key = self.read_arcgis_api_key()
        if api_key is None:
            return (
                "ArcGIS mode is not configured correctly: API key file is missing, unreadable, or empty."
            )

        masked_key = mask_secret(api_key)

        if self.arcgis_auth_mode == "query":
            return (
                "ArcGIS mode is configured correctly with query auth. "
                f"Masked key: {masked_key}"
            )

        return (
            "ArcGIS mode is configured correctly with header auth. "
            f"Masked key: {masked_key}"
        )


settings = Settings()
