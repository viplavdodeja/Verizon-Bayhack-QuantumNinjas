from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_PROJECT_DIR = BASE_DIR.parent / "fire_test2"
DEFAULT_MODEL_PATH = REFERENCE_PROJECT_DIR / "firedetect-11s.pt"


class Settings:
    def __init__(self) -> None:
        self.app_name = "FireWatch Backend"
        self.model_path = Path(
            os.getenv("FIREWATCH_MODEL_PATH", str(DEFAULT_MODEL_PATH))
        )
        self.camera_index = int(os.getenv("FIREWATCH_CAMERA_INDEX", "0"))
        self.frame_width = int(os.getenv("FIREWATCH_FRAME_WIDTH", "640"))
        self.frame_height = int(os.getenv("FIREWATCH_FRAME_HEIGHT", "480"))
        self.img_size = int(os.getenv("FIREWATCH_IMG_SIZE", "640"))
        self.confidence_threshold = float(
            os.getenv("FIREWATCH_CONFIDENCE_THRESHOLD", "0.40")
        )
        self.iou_threshold = float(os.getenv("FIREWATCH_IOU_THRESHOLD", "0.45"))
        self.min_consecutive_detections = int(
            os.getenv("FIREWATCH_MIN_CONSECUTIVE_DETECTIONS", "3")
        )
        self.max_missed_frames = int(
            os.getenv("FIREWATCH_MAX_MISSED_FRAMES", "5")
        )
        self.max_box_area_ratio = float(
            os.getenv("FIREWATCH_MAX_BOX_AREA_RATIO", "0.70")
        )
        self.frame_poll_interval_seconds = float(
            os.getenv("FIREWATCH_FRAME_POLL_INTERVAL_SECONDS", "0.05")
        )
        self.snapshot_jpeg_quality = int(
            os.getenv("FIREWATCH_SNAPSHOT_JPEG_QUALITY", "85")
        )
        self.source_name = os.getenv("FIREWATCH_SOURCE_NAME", "webcam")


settings = Settings()
