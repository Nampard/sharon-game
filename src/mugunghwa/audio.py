"""사운드: 목소리별 구호(속도별 변형), 총소리, 효과음. 파일이 없으면 무음으로 동작한다.

목소리 폴더 (ADR-0008):
  assets/voices/<이름>/chant.wav   — 게임에 들어 있는 목소리 (기본: 기계음)
  voices/<이름>/chant.wav          — 실행 폴더 옆에 사용자가 추가하는 목소리 (exe 배포 후에도 추가 가능)
  chant.wav 대신 chant.ogg / chant.mp3 도 된다. 선택: voice.json {"name": "표시 이름", "weights": [글자 10개 비중]}
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pygame

from .paths import asset

SOUND_FILES = {"shot": "gunshot.wav", "beep": "beep.wav", "turn": "turn.wav"}
CHANT_NAMES = ("chant.wav", "chant.ogg", "chant.mp3")
RANDOM_VOICE = "무작위"
LEAD_S, TAIL_S = 0.05, 0.8  # 말 앞에 남길 여백, 말 끝 뒤에 남길 울림


def voice_dirs() -> list[Path]:
    """게임 내장 목소리 + 실행 폴더의 사용자 목소리 폴더 목록 (이름순, 같은 이름이면 사용자 것이 우선)."""
    found: dict[str, Path] = {}
    for root in (asset("voices"), Path.cwd() / "voices"):
        if not root.is_dir():
            continue
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            if any((d / n).exists() for n in CHANT_NAMES):
                found[d.name] = d
    return list(found.values())


def speech_bounds(mono: np.ndarray, sr: int) -> tuple[int, int]:
    """음량 포락선으로 말이 시작·끝나는 샘플 위치를 찾는다 (녹음 앞뒤 무음·잡음 무시)."""
    x = np.abs(mono.astype(float))
    win = max(1, int(sr * 0.02))
    env = np.convolve(x, np.ones(win) / win, mode="same")
    if env.max() <= 0:
        return 0, len(mono)
    idx = np.flatnonzero(env > env.max() * 0.08)
    return int(idx[0]), int(idx[-1]) + 1


def _resample(arr: np.ndarray, speed: float) -> np.ndarray:
    """재생 속도 변경 (음높이도 같이 변함 — 빠를수록 높고 급해져서 긴장감에 좋다)."""
    n = arr.shape[0]
    idx = np.linspace(0, n - 1, max(1, int(n / speed)))
    src = np.arange(n)
    if arr.ndim == 1:
        out = np.interp(idx, src, arr)
    else:
        out = np.stack([np.interp(idx, src, arr[:, c]) for c in range(arr.shape[1])], axis=1)
    return np.ascontiguousarray(out.astype(arr.dtype))


@dataclass
class Voice:
    name: str
    path: Path
    weights: list[float] | None = None  # 글자별 시간 비중 (None이면 균등)
    speech_start: float = 0.0           # 속도 1.0 기준 초
    speech_end: float = 0.0
    chants: dict[float, pygame.mixer.Sound] = field(default_factory=dict)


def load_voice(folder: Path, speeds: list[float]) -> Voice:
    meta = {}
    if (folder / "voice.json").exists():
        meta = json.loads((folder / "voice.json").read_text(encoding="utf-8"))
    file = next(folder / n for n in CHANT_NAMES if (folder / n).exists())
    arr = pygame.sndarray.array(pygame.mixer.Sound(str(file)))
    sr = pygame.mixer.get_init()[0]
    mono = arr.mean(axis=1) if arr.ndim == 2 else arr
    a, b = speech_bounds(mono, sr)
    # 앞쪽 무음은 잘라서 술래가 바로 말하게 하고, 끝은 울림만 조금 남긴다
    start = max(0, a - int(LEAD_S * sr))
    end = min(len(arr), b + int(TAIL_S * sr))
    arr = np.ascontiguousarray(arr[start:end])
    v = Voice(meta.get("name", folder.name), folder, meta.get("weights"),
              (a - start) / sr, (b - start) / sr)
    for s in speeds:
        v.chants[s] = pygame.sndarray.make_sound(arr if s == 1.0 else _resample(arr, s))
    return v


class Audio:
    def __init__(self, speeds: list[float], voice: str = "기계음", rng: random.Random | None = None):
        self.enabled = pygame.mixer.get_init() is not None
        self.speeds = speeds
        self.rng = rng or random.Random()
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.voices: dict[str, Voice] = {}
        self.selected = voice      # 목소리 이름 또는 RANDOM_VOICE
        self.current: Voice | None = None  # 이번 구호에 쓰는 목소리
        self.errors: list[str] = []
        if not self.enabled:
            return
        for key, name in SOUND_FILES.items():
            path = asset("sounds", name)
            if path.exists():
                self.sounds[key] = pygame.mixer.Sound(str(path))
        self.reload_voices()
        self.chant_channel = pygame.mixer.Channel(0)
        pygame.mixer.set_reserved(1)

    def reload_voices(self) -> None:
        self.voices.clear()
        self.errors.clear()
        for d in voice_dirs():
            try:
                v = load_voice(d, self.speeds)
                self.voices[v.name] = v
            except Exception as e:  # 깨진 녹음 파일 하나 때문에 게임이 멈추지 않게
                self.errors.append(f"{d.name}: {e}")
        if self.selected != RANDOM_VOICE and self.selected not in self.voices:
            self.selected = next(iter(self.voices), self.selected)
        self.current = self.voices.get(self.selected) or next(iter(self.voices.values()), None)

    @property
    def options(self) -> list[str]:
        names = list(self.voices)
        return names + [RANDOM_VOICE] if len(names) > 1 else names

    def select(self, name: str) -> None:
        self.selected = name
        if name in self.voices:
            self.current = self.voices[name]

    def prepare_chant(self, speed: float) -> float:
        """GREEN 시작마다 호출: 이번 구호의 목소리를 정하고 길이(초)를 돌려준다."""
        if self.selected == RANDOM_VOICE and self.voices:
            self.current = self.rng.choice(list(self.voices.values()))
        snd = self.current.chants.get(speed) if self.current else None
        return snd.get_length() if snd else 3.0 / speed

    def chant_timing(self) -> tuple[list[float] | None, float, float]:
        """화면 가사용: (글자 비중, 말 시작 초, 말 끝 초) — 속도 1.0 기준."""
        if not self.current:
            return None, 0.0, 2.0
        return self.current.weights, self.current.speech_start, self.current.speech_end

    def play_chant(self, speed: float) -> None:
        snd = self.current.chants.get(speed) if self.current else None
        if snd:
            self.chant_channel.play(snd)

    def preview(self, name: str) -> None:
        """설정 화면에서 목소리 들어보기."""
        v = self.voices.get(name)
        if v and 1.0 in v.chants:
            self.chant_channel.play(v.chants[1.0])
        elif name == RANDOM_VOICE and self.voices:
            self.chant_channel.play(self.rng.choice(list(self.voices.values())).chants[1.0])

    def stop_chant(self) -> None:
        if self.enabled:
            self.chant_channel.stop()

    def play(self, key: str) -> None:
        snd = self.sounds.get(key)
        if snd:
            snd.play()
