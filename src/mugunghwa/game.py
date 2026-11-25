"""게임 상태 머신 (ADR-0005). 화면·사운드와 분리돼 있어 시간을 주입해 테스트할 수 있다."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from .config import GameConfig
from .model import Person
from .players import ALIVE, FINISHED, OUT, Player, PlayerRegistry

TITLE, LOBBY, COUNTDOWN, GREEN, RED, RESULT = "TITLE", "LOBBY", "COUNTDOWN", "GREEN", "RED", "RESULT"


@dataclass
class Event:
    kind: str                 # "chant" | "turn" | "shot" | "win" | "beep" | "end"
    player: Player | None = None
    speed: float = 1.0


class Game:
    def __init__(self, cfg: GameConfig, prepare_chant: Callable[[float], float],
                 rng: random.Random | None = None):
        self.cfg = cfg
        self.prepare_chant = prepare_chant  # GREEN마다 호출: 목소리를 정하고 구호 길이(초)를 돌려줌
        self.rng = rng or random.Random()
        self.registry = PlayerRegistry(cfg.judge_params())
        self.state = TITLE
        self.state_since = 0.0
        self.state_until = 0.0
        self.game_start = 0.0
        self.speed = 1.0
        self.round = 0              # 지금까지 시작한 GREEN 횟수
        self.chant_full = 0.0       # 이번 구호 전체 길이 (끊겨도 원래 길이, 화면 가사 진행용)
        self.cut = False            # 이번 구호가 중간에 끊기는지 (화면에는 미리 알리지 않음)
        self.snap_at: float | None = None  # 돌아선 직후 다시 돌아볼 시각
        self.events: list[Event] = []
        self.last_beep = -1
        self.winner: Player | None = None
        self._now = 0.0

    # ---- 전이 ----
    def _enter(self, state: str, now: float, duration: float = 0.0) -> None:
        self.state, self.state_since, self.state_until = state, now, now + duration

    def to_title(self, now: float) -> None:
        self.registry.reset()
        self.winner = None
        self._enter(TITLE, now)

    def to_lobby(self, now: float) -> None:
        self.registry.reset()
        self.winner = None
        self._enter(LOBBY, now)

    def start(self, now: float) -> bool:
        """LOBBY에서 참가자를 확정하고 카운트다운을 시작한다."""
        if self.state != LOBBY or not self.registry.players:
            return False
        self.registry.lock()
        self.last_beep = -1
        self.round = 0
        self._enter(COUNTDOWN, now, self.cfg.countdown_s)
        return True

    def _pick_speed(self) -> float:
        speeds = sorted(self.cfg.chant_speeds)
        if self.cfg.rules().accelerate:
            # 2라운드마다 가장 느린 속도를 하나씩 후보에서 뺀다 (최소 2개는 남김)
            speeds = speeds[min(self.round // 2, max(0, len(speeds) - 2)):]
        return self.rng.choice(speeds)

    def _green(self, now: float, from_red: bool) -> None:
        rules = self.cfg.rules()
        self.speed = self._pick_speed()
        self.chant_full = self.prepare_chant(self.speed)
        self.cut = self.round > 0 and self.rng.random() < rules.fake_chance
        duration = self.chant_full * (self.rng.uniform(0.4, 0.75) if self.cut else 1.0)
        self.snap_at = (now + self.rng.uniform(0.35, 0.7)
                        if from_red and self.rng.random() < rules.snap_chance else None)
        self.round += 1
        self._enter(GREEN, now, duration)
        self.events.append(Event("chant", speed=self.speed))

    def _red(self, now: float, snap: bool = False) -> None:
        for pl in self.registry.alive:
            pl.judge.reset()
            pl.last_score = None
        rules = self.cfg.rules()
        self.snap_at = None
        self._enter(RED, now, self.rng.uniform(rules.red_min_s, rules.red_max_s))
        self.events.append(Event("snap" if snap else "turn"))

    def _end(self, now: float) -> None:
        self._enter(RESULT, now)
        self.events.append(Event("end"))

    def _shoot(self, pl: Player, reason: str) -> None:
        pl.status, pl.reason = OUT, reason
        self.events.append(Event("shot", player=pl))

    # ---- 입력 ----
    @property
    def time_left(self) -> float:
        if self.state in (GREEN, RED):
            return max(0.0, self.cfg.time_limit_s - (self._now - self.game_start))
        return self.cfg.time_limit_s

    def on_detection(self, persons: list[Person], now: float) -> None:
        self._now = now
        if self.state == LOBBY:
            self.registry.preview(persons, now)
            return
        if self.state not in (COUNTDOWN, GREEN, RED):
            return
        matched = self.registry.update(persons, now)
        if self.state != RED:
            return
        ms = (now - self.state_since) * 1000.0
        for pl, person in matched:
            if pl.status != ALIVE:
                continue
            res = pl.judge.update(person.keypoints, person.bbox, ms)
            pl.last_score = res.score
            if res.eliminated:
                self._shoot(pl, "움직임 감지")
        if ms >= self.registry.params.grace_ms:
            for pl in self.registry.alive:
                if not pl.visible and (now - pl.last_seen) * 1000.0 > self.cfg.missing_out_ms:
                    self._shoot(pl, "화면 이탈")
        if not self.registry.alive:
            self._end(now)

    def press_button(self, now: float) -> Player | None:
        """승리 버튼: 지금 보이는 생존자 중 카메라에 가장 가까운(가장 큰) 사람이 누른 것으로 본다."""
        if self.state not in (GREEN, RED):
            return None
        candidates = [p for p in self.registry.alive if p.visible]
        if not candidates:
            return None
        pl = max(candidates, key=lambda p: p.height)
        pl.status, pl.reason = FINISHED, "버튼 도착"
        self.winner = self.winner or pl
        self.events.append(Event("win", player=pl))
        if self.cfg.button_ends_game or not self.registry.alive:
            self._end(now)
        return pl

    # ---- 시간 진행 ----
    def update(self, now: float) -> None:
        self._now = now
        if self.state == COUNTDOWN:
            remaining = int(self.state_until - now) + 1
            if remaining != self.last_beep and remaining > 0:
                self.last_beep = remaining
                self.events.append(Event("beep"))
            if now >= self.state_until:
                self.game_start = now
                self._green(now, from_red=False)
            return
        if self.state not in (GREEN, RED):
            return
        if now - self.game_start >= self.cfg.time_limit_s:
            for pl in self.registry.alive:
                self._shoot(pl, "시간 초과")
            self._end(now)
            return
        if self.state == GREEN and self.snap_at is not None and now >= self.snap_at:
            self._red(now, snap=True)  # 돌아선 척하다 다시 돌아봄
            return
        if now >= self.state_until:
            if self.state == GREEN:
                self._red(now)
            else:
                self._green(now, from_red=True)

    def pop_events(self) -> list[Event]:
        ev, self.events = self.events, []
        return ev
