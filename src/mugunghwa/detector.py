"""사람 인식·추적 (ADR-0003). YOLO pose + ByteTrack, 별도 스레드에서 실행."""
from __future__ import annotations

import threading
import time
from typing import Protocol

import numpy as np

from .model import Detection, LatestSlot, Person
from .paths import asset


class Detector(Protocol):
    def detect(self, frame: np.ndarray) -> list[Person]: ...


class YoloPoseDetector:
    def __init__(self, model: str, imgsz: int = 640, conf: float = 0.4, device: str | None = None):
        from ultralytics import YOLO  # 무거운 import는 여기서

        local = asset("models", model)
        self.model = YOLO(str(local) if local.exists() else model)
        self.imgsz, self.conf, self.device = imgsz, conf, device

    def detect(self, frame: np.ndarray) -> list[Person]:
        r = self.model.track(frame, persist=True, tracker="bytetrack.yaml", classes=[0],
                             imgsz=self.imgsz, conf=self.conf, device=self.device, verbose=False)[0]
        if r.boxes is None or r.boxes.id is None or r.keypoints is None:
            return []
        ids = r.boxes.id.int().cpu().numpy()
        boxes = r.boxes.xyxy.cpu().numpy()
        kxy = r.keypoints.xy.cpu().numpy()
        kconf = r.keypoints.conf.cpu().numpy() if r.keypoints.conf is not None else np.ones(kxy.shape[:2])
        return [
            Person(int(i), boxes[n], np.concatenate([kxy[n], kconf[n][:, None]], axis=1))
            for n, i in enumerate(ids)
        ]


class DetectorThread(threading.Thread):
    def __init__(self, frames: LatestSlot[np.ndarray], factory):
        super().__init__(daemon=True, name="detector")
        self.frames = frames
        self.factory = factory  # 스레드 안에서 모델을 만든다 (로딩 중에도 화면이 멈추지 않게)
        self.results: LatestSlot[Detection] = LatestSlot()
        self.ready = False
        self.error: str | None = None
        self._stop = threading.Event()

    def run(self) -> None:
        try:
            detector: Detector = self.factory()
        except Exception as e:  # 모델 로딩 실패를 화면에 보여주기 위함
            self.error = f"인식 모델 로딩 실패: {e}"
            return
        self.ready = True
        seq, fps, last = 0, 0.0, time.perf_counter()
        while not self._stop.is_set():
            seq, frame = self.frames.wait_newer(seq, timeout=0.5)
            if frame is None:
                continue
            persons = detector.detect(frame)
            t = time.perf_counter()
            fps = 0.9 * fps + 0.1 * (1.0 / max(t - last, 1e-6)) if fps else 1.0 / max(t - last, 1e-6)
            last = t
            self.results.put(Detection(frame, persons, time.monotonic(), fps))

    def stop(self) -> None:
        self._stop.set()
