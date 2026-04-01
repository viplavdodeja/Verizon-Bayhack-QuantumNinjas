from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class FrameReadResult:
    frame: Optional[np.ndarray]
    is_duplicate: bool
    success: bool
    message: str
    last_source_error: Optional[str] = None
    last_successful_fetch_at: Optional[str] = None
    last_fetch_http_status: Optional[int] = None


class BaseFrameSource(ABC):
    def __init__(self, source_type: str, source_name: str) -> None:
        self.source_type = source_type
        self.source_name = source_name

    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read(self) -> FrameReadResult:
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        raise NotImplementedError

    def get_source_name(self) -> str:
        return self.source_name

    def get_source_type(self) -> str:
        return self.source_type
