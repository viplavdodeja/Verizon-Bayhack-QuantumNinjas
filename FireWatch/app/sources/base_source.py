from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class BaseFrameSource(ABC):
    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read_frame(self) -> Optional[np.ndarray]:
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        raise NotImplementedError
