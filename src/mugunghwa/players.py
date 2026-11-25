"""참가자 등록과 track ID 재연결 (ADR-0003)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .judge import JudgeParams, MotionJudge
from .model import Person

ALIVE, OUT, FINISHED = "alive", "out", "finished"


def iou(a: np.ndarray, b: np.ndarray) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return float(inter / area) if area > 0 else 0.0


@dataclass
class Player:
    number: int
    track_id: int
    bbox: np.ndarray
    keypoints: np.ndarray
    judge: MotionJudge
    last_seen: float = 0.0
    status: str = ALIVE
    reason: str = ""
    visible: bool = True
    last_score: float | None = None
    old_track_ids: set[int] = field(default_factory=set)

    @property
    def height(self) -> float:
        return float(self.bbox[3] - self.bbox[1])


class PlayerRegistry:
    def __init__(self, params: JudgeParams):
        self.params = params
        self.players: list[Player] = []
        self.locked = False

    def preview(self, persons: list[Person], now: float) -> None:
        """LOBBY: 지금 보이는 사람을 왼쪽부터 번호 매겨 보여준다 (아직 확정 아님)."""
        ordered = sorted(persons, key=lambda p: p.bbox[0])
        self.players = [
            Player(i + 1, p.track_id, p.bbox, p.keypoints, MotionJudge(self.params), now)
            for i, p in enumerate(ordered)
        ]

    def lock(self) -> None:
        self.locked = True

    def reset(self) -> None:
        self.players = []
        self.locked = False

    def set_params(self, params: JudgeParams) -> None:
        self.params = params
        for pl in self.players:
            pl.judge = MotionJudge(params)

    def update(self, persons: list[Person], now: float) -> list[tuple[Player, Person]]:
        """게임 중: 등록된 참가자와 이번 프레임 인물을 짝짓는다. 새로운 사람(관객)은 무시."""
        by_id = {p.track_id: p for p in persons}
        known_ids = {pl.track_id for pl in self.players} | {
            t for pl in self.players for t in pl.old_track_ids}
        matched: list[tuple[Player, Person]] = []
        used: set[int] = set()

        for pl in self.players:
            person = by_id.get(pl.track_id)
            if person is not None:
                matched.append((pl, person))
                used.add(person.track_id)

        # ID가 바뀐 참가자 재연결: 마지막 위치와 겹치는 '모르는 ID'를 찾는다
        for pl in self.players:
            if pl.status == OUT or any(m[0] is pl for m in matched):
                continue
            best, best_score = None, 0.0
            for person in persons:
                if person.track_id in used or person.track_id in known_ids:
                    continue
                score = iou(pl.bbox, person.bbox)
                if score < 0.3:
                    c1 = (pl.bbox[:2] + pl.bbox[2:]) / 2
                    c2 = (person.bbox[:2] + person.bbox[2:]) / 2
                    if np.linalg.norm(c1 - c2) < 0.4 * max(pl.height, 1.0):
                        score = 0.3
                if score >= 0.3 and score > best_score:
                    best, best_score = person, score
            if best is not None:
                pl.old_track_ids.add(pl.track_id)
                pl.track_id = best.track_id
                used.add(best.track_id)
                matched.append((pl, best))

        seen = {id(m[0]) for m in matched}
        for pl in self.players:
            pl.visible = id(pl) in seen
        for pl, person in matched:
            pl.bbox, pl.keypoints, pl.last_seen = person.bbox, person.keypoints, now
        return matched

    @property
    def alive(self) -> list[Player]:
        return [p for p in self.players if p.status == ALIVE]
