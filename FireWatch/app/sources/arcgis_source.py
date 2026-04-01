from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
import time
from typing import Optional

import cv2
import numpy as np
import requests

from app.config import mask_secret
from app.config import read_secret_file
from app.sources.base_source import BaseFrameSource
from app.sources.base_source import FrameReadResult


logger = logging.getLogger(__name__)


class ArcGISImageSource(BaseFrameSource):
    def __init__(
        self,
        source_name: str,
        image_url: str,
        poll_interval_seconds: float,
        request_timeout_seconds: float,
        auth_mode: str,
        api_key_file: Path,
        api_key_query_param_name: str,
        auth_header_name: str,
        auth_header_prefix: str,
    ) -> None:
        super().__init__("arcgis", source_name)
        self.image_url = image_url
        self.poll_interval_seconds = poll_interval_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.auth_mode = auth_mode
        self.api_key_file = api_key_file
        self.api_key_query_param_name = api_key_query_param_name
        self.auth_header_name = auth_header_name
        self.auth_header_prefix = auth_header_prefix
        self.session = requests.Session()
        self.api_key: Optional[str] = None
        self.last_poll_started_at = 0.0
        self.last_image_hash: Optional[str] = None
        self.last_successful_fetch_at: Optional[datetime] = None

    def connect(self) -> bool:
        if self.image_url.strip() == "":
            logger.error("ArcGIS source connection failed because ARCGIS_IMAGE_URL is empty.")
            return False

        self.api_key = self._load_api_key()

        if self.auth_mode != "none" and self.api_key is None:
            logger.error(
                "ArcGIS source connection failed because auth is enabled but the API key could not be loaded."
            )
            return False

        if self.auth_mode == "query" and self.api_key is not None:
            logger.info(
                "ArcGIS source will authenticate with query auth using parameter '%s' and masked key %s.",
                self.api_key_query_param_name,
                mask_secret(self.api_key),
            )

        if self.auth_mode == "header" and self.api_key is not None:
            logger.info(
                "ArcGIS source will authenticate with header auth using header '%s' and masked key %s.",
                self.auth_header_name,
                mask_secret(self.api_key),
            )

        return True

    def read(self) -> FrameReadResult:
        self._wait_for_poll_interval()

        try:
            response = self.session.get(
                self.image_url,
                params=self._build_query_params(),
                headers=self._build_headers(),
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as error:
            logger.warning("ArcGIS image fetch failed: %s", error)
            return self._build_failed_result(
                message="Image request failed.",
                last_fetch_http_status=None,
            )

        if response.status_code != 200:
            logger.warning(
                "ArcGIS image fetch returned HTTP %s.",
                response.status_code,
            )
            return self._build_failed_result(
                message=f"Image request returned HTTP {response.status_code}.",
                last_fetch_http_status=response.status_code,
            )

        image_bytes = response.content
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        if self.last_image_hash == image_hash:
            seconds_since_success = self._get_seconds_since_last_successful_fetch()
            logger.info(
                "ArcGIS image fetch succeeded with HTTP 200, but the image was unchanged. Seconds since last success: %s",
                seconds_since_success,
            )
            return FrameReadResult(
                frame=None,
                is_duplicate=True,
                success=True,
                message="Duplicate image skipped.",
                last_source_error=None,
                last_successful_fetch_at=self._get_last_successful_fetch_at_iso(),
                last_fetch_http_status=200,
            )

        frame = self._decode_image_bytes(image_bytes)
        if frame is None:
            logger.warning("ArcGIS image fetch succeeded, but the bytes could not be decoded.")
            return self._build_failed_result(
                message="Downloaded bytes could not be decoded.",
                last_fetch_http_status=200,
            )

        self.last_image_hash = image_hash
        self.last_successful_fetch_at = datetime.now(timezone.utc)

        logger.info("ArcGIS image fetch succeeded with HTTP 200.")
        return FrameReadResult(
            frame=frame,
            is_duplicate=False,
            success=True,
            message="ArcGIS image fetched successfully.",
            last_source_error=None,
            last_successful_fetch_at=self._get_last_successful_fetch_at_iso(),
            last_fetch_http_status=200,
        )

    def release(self) -> None:
        self.session.close()

    def _load_api_key(self) -> Optional[str]:
        if self.auth_mode == "none":
            return None

        api_key = read_secret_file(self.api_key_file)
        if api_key is None:
            logger.error(
                "ArcGIS API key file is missing, unreadable, or empty: %s",
                self.api_key_file,
            )
            return None

        return api_key

    def _build_query_params(self) -> Optional[dict]:
        if self.auth_mode != "query" or self.api_key is None:
            return None

        params = {}
        params[self.api_key_query_param_name] = self.api_key
        return params

    def _build_headers(self) -> Optional[dict]:
        if self.auth_mode != "header" or self.api_key is None:
            return None

        headers = {}
        headers[self.auth_header_name] = f"{self.auth_header_prefix}{self.api_key}"
        return headers

    def _decode_image_bytes(self, image_bytes: bytes) -> Optional[np.ndarray]:
        numpy_bytes = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(numpy_bytes, cv2.IMREAD_COLOR)
        return frame

    def _wait_for_poll_interval(self) -> None:
        if self.poll_interval_seconds <= 0:
            self.last_poll_started_at = time.time()
            return

        now = time.time()
        elapsed = now - self.last_poll_started_at

        if self.last_poll_started_at > 0 and elapsed < self.poll_interval_seconds:
            time.sleep(self.poll_interval_seconds - elapsed)

        self.last_poll_started_at = time.time()

    def _build_failed_result(
        self,
        message: str,
        last_fetch_http_status: Optional[int],
    ) -> FrameReadResult:
        seconds_since_success = self._get_seconds_since_last_successful_fetch()
        logger.info(
            "ArcGIS source has been without a successful fetch for %s seconds.",
            seconds_since_success,
        )
        return FrameReadResult(
            frame=None,
            is_duplicate=False,
            success=False,
            message=message,
            last_source_error=message,
            last_successful_fetch_at=self._get_last_successful_fetch_at_iso(),
            last_fetch_http_status=last_fetch_http_status,
        )

    def _get_seconds_since_last_successful_fetch(self) -> Optional[float]:
        if self.last_successful_fetch_at is None:
            return None

        now = datetime.now(timezone.utc)
        delta = now - self.last_successful_fetch_at
        return round(delta.total_seconds(), 2)

    def _get_last_successful_fetch_at_iso(self) -> Optional[str]:
        if self.last_successful_fetch_at is None:
            return None
        return self.last_successful_fetch_at.isoformat()
