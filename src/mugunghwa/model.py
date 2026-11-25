"""스레드·모듈 사이에서 주고받는 데이터 타입."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Generic, TypeVar

import numpy as np


@dataclass
class Person:
    track_id: int
    bbox: np.ndarray       # [x1, y1, x2, y2]
    keypoints: np.ndarray  # (17, 3) [x, y, conf]

    @property
    def height(self) -> float:
        return float(self.bbox[3] - self.bbox[1])


@dataclass
class Detection:
    frame: np.ndarray            # 인식에 사용한 BGR 프레임 (박스와 정확히 맞음)
    persons: list[Person] = field(default_factory=list)
    timestamp: float = 0.0
    fps: float = 0.0


T = TypeVar("T")


class LatestSlot(Generic[T]):
    """최신 값 하나만 보관하는 스레드 간 슬롯 (큐가 아니라 덮어쓰기, ADR-0005)."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._value: T | None = None
        self._seq = 0

    def put(self, value: T) -> None:
        with self._cond:
            self._value = value
            self._seq += 1
            self._cond.notify_all()

    def get(self) -> tuple[int, T | None]:
        with self._cond:
            return self._seq, self._value

    def wait_newer(self, seq: int, timeout: float = 0.5) -> tuple[int, T | None]:
        with self._cond:
            self._cond.wait_for(lambda: self._seq > seq, timeout=timeout)
            return self._seq, self._value
