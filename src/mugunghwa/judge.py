"""움직임 판정 (ADR-0004). 카메라·pygame에 의존하지 않는 순수 로직."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class JudgeParams:
    threshold: float = 0.04         # 관절 이동량 / 키(bbox 높이)
    center_threshold: float = 0.06  # 몸 중심 이동량 / 키
    grace_ms: float = 500.0         # 뒤돌아본 직후 판정 유예
    confirm_frames: int = 3         # 연속 초과 프레임 수
    smooth_frames: int = 3          # 이동 평균 프레임 수
    kp_conf: float = 0.5            # 사용할 관절 최소 신뢰도
    min_moving_joints: int = 2      # 동시에 움직여야 하는 관절 수 (단일 관절 튐 무시)


@dataclass
class JudgeResult:
    score: float | None   # 관절 점수 (판정 전이면 None)
    center: float | None  # 중심 점수
    moving: bool
    eliminated: bool


def _center(bbox: np.ndarray) -> np.ndarray:
    return np.array([(bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0])


def joint_score(base_kp: np.ndarray, cur_kp: np.ndarray, height: float,
                kp_conf: float, min_joints: int) -> float | None:
    """관절별 이동량을 키로 나눈 뒤 `min_joints`번째로 큰 값을 돌려준다.

    가장 큰 값 하나만 보면 포즈 추정이 한 관절에서 튈 때 오판하고, 중앙값을 보면
    팔만 움직이는 경우를 놓친다. 'N번째로 큰 값'은 팔(팔꿈치+손목)이나
    다리(무릎+발목)처럼 함께 움직이는 관절 묶음은 잡고 단일 관절 튐은 무시한다.
    """
    mask = (base_kp[:, 2] >= kp_conf) & (cur_kp[:, 2] >= kp_conf)
    if mask.sum() < max(min_joints, 4):
        return None
    d = np.linalg.norm(cur_kp[mask, :2] - base_kp[mask, :2], axis=1) / max(height, 1.0)
    d.sort()
    return float(d[-min_joints])


class MotionJudge:
    """참가자 한 명의 RED 구간 판정기. RED가 시작될 때마다 `reset()` 한다."""

    def __init__(self, params: JudgeParams):
        self.params = params
        self.reset()

    def reset(self) -> None:
        self._base_buf: list[tuple[np.ndarray, np.ndarray]] = []
        self._base: tuple[np.ndarray, np.ndarray] | None = None
        self._recent: deque[tuple[np.ndarray, np.ndarray]] = deque(maxlen=self.params.smooth_frames)
        self._over = 0
        self.eliminated = False

    @staticmethod
    def _mean(frames) -> tuple[np.ndarray, np.ndarray]:
        kps = np.stack([f[0] for f in frames])
        boxes = np.stack([f[1] for f in frames])
        return kps.mean(axis=0), boxes.mean(axis=0)

    def update(self, keypoints: np.ndarray, bbox: np.ndarray, ms_since_red: float) -> JudgeResult:
        """keypoints: (17, 3) [x, y, conf], bbox: [x1, y1, x2, y2] (픽셀)."""
        p = self.params
        if self.eliminated:
            return JudgeResult(None, None, True, True)
        if ms_since_red < p.grace_ms:
            return JudgeResult(None, None, False, False)

        frame = (np.asarray(keypoints, dtype=float), np.asarray(bbox, dtype=float))
        if self._base is None:
            # 유예가 끝난 뒤 처음 몇 프레임의 평균을 기준 자세로 삼는다 (기준 자체의 떨림 감소)
            self._base_buf.append(frame)
            if len(self._base_buf) >= p.smooth_frames:
                self._base = self._mean(self._base_buf)
            return JudgeResult(None, None, False, False)

        self._recent.append(frame)
        cur_kp, cur_box = self._mean(self._recent)
        base_kp, base_box = self._base
        height = float(base_box[3] - base_box[1])

        score = joint_score(base_kp, cur_kp, height, p.kp_conf, p.min_moving_joints)
        center = float(np.linalg.norm(_center(cur_box) - _center(base_box)) / max(height, 1.0))

        moving = (score is not None and score > p.threshold) or center > p.center_threshold
        self._over = self._over + 1 if moving else 0
        if self._over >= p.confirm_frames:
            self.eliminated = True
        return JudgeResult(score, center, moving, self.eliminated)
