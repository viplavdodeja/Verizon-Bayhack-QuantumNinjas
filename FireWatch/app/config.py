from pathlib import Path
import os
from threading import Lock
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_PROJECT_DIR = BASE_DIR.parent / "fire_test2"
LOCAL_MODEL_PATH = BASE_DIR / "firedetect-11s.pt"
REFERENCE_MODEL_PATH = REFERENCE_PROJECT_DIR / "firedetect-11s.pt"

if LOCAL_MODEL_PATH.exists():
    DEFAULT_MODEL_PATH = LOCAL_MODEL_PATH
else:
    DEFAULT_MODEL_PATH = REFERENCE_MODEL_PATH


ARCGIS_CAMERA_PRESETS: List[Dict[str, str]] = [
    {
        "camera_id": "axis-antelope-mtn",
        "name": "Axis Antelope Mountain",
        "region": "Owens Valley",
        "image_url": "https://cameras.alertcalifornia.org/public-camera-data/Axis-AntelopeMtn/latest-frame.jpg",
    },
    {
        "camera_id": "axis-alabama-hills-1",
        "name": "Axis Alabama Hills 1",
        "region": "Lone Pine",
        "image_url": "https://cameras.alertcalifornia.org/public-camera-data/Axis-AlabamaHills1/latest-frame.jpg",
    },
    {
        "camera_id": "axis-grapevine-1",
        "name": "Axis Grapevine 1",
        "region": "Tejon Pass",
        "image_url": "https://cameras.alertcalifornia.org/public-camera-data/Axis-Grapevine1/latest-frame.jpg",
    },
]


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
        self._runtime_lock = Lock()
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
                "0.60",
            )
        )
        self.alert_confidence_threshold = float(
            _read_env(
                "ALERT_CONFIDENCE_THRESHOLD",
                "FIREWATCH_ALERT_CONFIDENCE_THRESHOLD",
                "0.85",
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

        self._active_source_type = self.source_type
        self._active_arcgis_image_url = self.arcgis_image_url
        self._selected_arcgis_camera_id = self._resolve_camera_id_from_url(
            self.arcgis_image_url
        )
        self._active_arcgis_source_name = self._resolve_source_name(
            self._selected_arcgis_camera_id,
            self.arcgis_image_url,
        )

    def get_source_type(self) -> str:
        with self._runtime_lock:
            return self._active_source_type

    def get_default_source_name(self) -> str:
        with self._runtime_lock:
            if self._active_source_type == "arcgis":
                return self._active_arcgis_source_name
            return "webcam"

    def get_active_poll_interval_seconds(self) -> float:
        if self.get_source_type() == "arcgis":
            return self.arcgis_poll_interval_seconds
        return self.frame_poll_interval_seconds

    def get_arcgis_source_url(self) -> str:
        with self._runtime_lock:
            return self._active_arcgis_image_url

    def get_selected_arcgis_camera_id(self) -> Optional[str]:
        with self._runtime_lock:
            return self._selected_arcgis_camera_id

    def get_active_arcgis_source_name(self) -> str:
        with self._runtime_lock:
            return self._active_arcgis_source_name

    def list_arcgis_cameras(self) -> List[Dict[str, str]]:
        cameras: List[Dict[str, str]] = []
        for camera in ARCGIS_CAMERA_PRESETS:
            copied_camera: Dict[str, str] = {}
            for key, value in camera.items():
                copied_camera[key] = value
            cameras.append(copied_camera)
        return cameras

    def switch_to_webcam(self) -> str:
        with self._runtime_lock:
            self._active_source_type = "webcam"
            return "webcam"

    def switch_to_arcgis(
        self,
        camera_id: Optional[str],
        image_url: Optional[str],
    ) -> str:
        selected_camera = None
        resolved_image_url = ""

        if camera_id is not None and camera_id != "":
            selected_camera = self._find_camera_by_id(camera_id)
            if selected_camera is None:
                raise ValueError("Unknown ArcGIS camera id.")
            resolved_image_url = selected_camera["image_url"]
        elif image_url is not None and image_url.strip() != "":
            resolved_image_url = image_url.strip()
        else:
            raise ValueError("ArcGIS source requires a camera id or image URL.")

        with self._runtime_lock:
            self._active_source_type = "arcgis"
            self._active_arcgis_image_url = resolved_image_url
            if selected_camera is None:
                self._selected_arcgis_camera_id = self._resolve_camera_id_from_url(
                    resolved_image_url
                )
            else:
                self._selected_arcgis_camera_id = selected_camera["camera_id"]
            self._active_arcgis_source_name = self._resolve_source_name(
                self._selected_arcgis_camera_id,
                resolved_image_url,
            )
            return self._active_arcgis_source_name

    def read_arcgis_api_key(self) -> Optional[str]:
        return read_secret_file(self.arcgis_api_key_file)

    def get_masked_arcgis_api_key(self) -> str:
        return mask_secret(self.read_arcgis_api_key())

    def get_arcgis_startup_status_message(self) -> str:
        if self.get_source_type() != "arcgis":
            return "ArcGIS mode is not active."

        active_image_url = self.get_arcgis_source_url()
        if active_image_url == "":
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

    def _find_camera_by_id(self, camera_id: str) -> Optional[Dict[str, str]]:
        for camera in ARCGIS_CAMERA_PRESETS:
            if camera["camera_id"] == camera_id:
                return camera
        return None

    def _resolve_camera_id_from_url(self, image_url: str) -> Optional[str]:
        if image_url == "":
            return None

        for camera in ARCGIS_CAMERA_PRESETS:
            if camera["image_url"] == image_url:
                return camera["camera_id"]
        return None

    def _resolve_source_name(
        self,
        camera_id: Optional[str],
        image_url: str,
    ) -> str:
        if camera_id is not None:
            camera = self._find_camera_by_id(camera_id)
            if camera is not None:
                return camera["name"]

        if image_url != "":
            return "Custom ArcGIS Camera"

        return "arcgis-image"


settings = Settings()
