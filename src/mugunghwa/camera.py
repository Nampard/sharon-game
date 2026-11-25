"""카메라 캡처 스레드. 최신 프레임 하나만 슬롯에 둔다.

macOS는 카메라 권한 요청을 메인 스레드에서만 띄울 수 있으므로, 카메라 열기(`try_open`)는
메인 루프에서 호출하고 열린 장치만 캡처 스레드로 넘긴다.
"""
from __future__ import annotations

import sys
import threading
import time

import cv2
import numpy as np

from .model import LatestSlot


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    if sys.platform == "win32":
        backend = cv2.CAP_DSHOW       # MSMF는 일부 웹캠에서 여는 데 수 초 걸림 (ADR-0006)
    elif sys.platform == "darwin":
        backend = cv2.CAP_AVFOUNDATION
    else:
        backend = cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap


class Camera:
    RETRY_S = 1.5

    def __init__(self, index: int, width: int, height: int, mirror: bool = True):
        self.index, self.width, self.height, self.mirror = index, width, height, mirror
        self.frames: LatestSlot[np.ndarray] = LatestSlot()
        self.error: str | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_try = -1e9

    @property
    def running(self) -> bool:
        return self._thread is not None

    def try_open(self, now: float) -> None:
        """메인 스레드에서 매 프레임 호출. 아직 안 열렸으면 주기적으로 다시 시도한다."""
        if self.running or now - self._last_try < self.RETRY_S:
            return
        self._last_try = now
        cap = open_camera(self.index, self.width, self.height)
        if not cap.isOpened():
            cap.release()
            self.error = f"카메라 {self.index}번을 열 수 없습니다. 연결과 권한을 확인해 주세요."
            return
        self.error = None
        self._thread = threading.Thread(target=self._run, args=(cap,), daemon=True, name="camera")
        self._thread.start()

    def _run(self, cap: cv2.VideoCapture) -> None:
        stop = self._stop  # switch()가 새 Event로 바꿔도 이 스레드는 자기 Event를 본다
        try:
            while not stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue
                if self.mirror:
                    frame = cv2.flip(frame, 1)
                self.frames.put(frame)
        finally:
            cap.release()

    def switch(self, index: int, now: float) -> None:
        """다른 카메라로 바꾼다 (메인 스레드에서 호출). 실패하면 error에 안내가 남고 계속 재시도한다."""
        self.stop()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None
        self._stop = threading.Event()
        self.index = index
        self.frames.put(None)  # 이전 카메라의 마지막 화면을 지운다
        self._last_try = -1e9
        self.try_open(now)

    def stop(self) -> None:
        self._stop.set()
