"""설정 화면: 카메라·목소리·난이도·제한 시간. 닫을 때 config.json 에 저장한다."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from . import keys
from .audio import RANDOM_VOICE, Audio
from .camera import Camera
from .config import DIFFICULTY_LABELS, DIFFICULTY_ORDER, GameConfig, save_config

MAX_CAMERAS = 6
TIME_LIMITS = [45, 60, 90, 120, 180]


@dataclass
class Row:
    key: str
    label: str
    value: str
    hint: str


class SettingsMenu:
    ROWS = ("camera", "voice", "difficulty", "time")

    def __init__(self, cfg: GameConfig, camera: Camera, audio: Audio, on_difficulty):
        self.cfg, self.camera, self.audio = cfg, camera, audio
        self.on_difficulty = on_difficulty
        self.open = False
        self.row = 0
        self.saved_note = ""

    def show(self) -> None:
        self.open, self.row, self.saved_note = True, 0, ""

    def close(self) -> None:
        self.open = False
        self.audio.stop_chant()
        try:
            save_config(self.cfg)
            self.saved_note = "설정을 저장했습니다"
        except OSError as e:
            self.saved_note = f"설정을 저장하지 못했습니다: {e}"

    def rows(self) -> list[Row]:
        voices = self.audio.options
        voice = self.audio.selected if voices else "없음"
        return [
            Row("camera", "카메라", f"{self.cfg.camera_index}번",
                "좌우 화살표로 바꾸면 왼쪽에 그 카메라 화면이 나옵니다"),
            Row("voice", "술래 목소리", voice,
                "Enter로 들어보기, R로 voices 폴더 다시 읽기"),
            Row("difficulty", "난이도", DIFFICULTY_LABELS[self.cfg.difficulty], ""),
            Row("time", "제한 시간", f"{int(self.cfg.time_limit_s)}초", ""),
        ]

    def handle(self, ev: pygame.event.Event, now: float) -> None:
        if keys.matches(ev, "escape", "s"):
            self.close()
        elif keys.matches(ev, "up"):
            self.row = (self.row - 1) % len(self.ROWS)
        elif keys.matches(ev, "down"):
            self.row = (self.row + 1) % len(self.ROWS)
        elif keys.matches(ev, "left", "right"):
            self._change(1 if keys.matches(ev, "right") else -1, now)
        elif keys.matches(ev, "return", "space") and self.ROWS[self.row] == "voice":
            self.audio.preview(self.audio.selected)
        elif keys.matches(ev, "r"):
            self.audio.reload_voices()
            self.cfg.voice = self.audio.selected

    def _change(self, step: int, now: float) -> None:
        key = self.ROWS[self.row]
        if key == "camera":
            self.cfg.camera_index = (self.cfg.camera_index + step) % MAX_CAMERAS
            self.camera.switch(self.cfg.camera_index, now)
        elif key == "voice":
            opts = self.audio.options
            if opts:
                i = opts.index(self.audio.selected) if self.audio.selected in opts else 0
                self.audio.select(opts[(i + step) % len(opts)])
                self.cfg.voice = self.audio.selected
        elif key == "difficulty":
            i = DIFFICULTY_ORDER.index(self.cfg.difficulty)
            self.cfg.difficulty = DIFFICULTY_ORDER[(i + step) % len(DIFFICULTY_ORDER)]
            self.on_difficulty()
        elif key == "time":
            cur = int(self.cfg.time_limit_s)
            i = TIME_LIMITS.index(cur) if cur in TIME_LIMITS else 2
            self.cfg.time_limit_s = float(TIME_LIMITS[(i + step) % len(TIME_LIMITS)])


__all__ = ["SettingsMenu", "RANDOM_VOICE"]
