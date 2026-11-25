"""임시 사운드 생성기 (ADR-0007: 직접 만든 자산).

- gunshot/beep/turn: numpy로 합성 (모든 OS)
- chant: macOS `say` 한국어 음성 → assets/voices/기계음/chant.wav (macOS 전용, 다른 OS에서는 건너뜀)

사용: .venv/bin/python tools/make_sounds.py [--voice Yuna]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parents[1] / "assets" / "sounds"


def write_wav(path: Path, mono: np.ndarray) -> None:
    mono = np.clip(mono, -1, 1)
    stereo = np.repeat((mono * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


def gunshot() -> np.ndarray:
    rng = np.random.default_rng(42)
    t = np.arange(int(SR * 1.6)) / SR
    crack = rng.normal(0, 1, t.size) * np.exp(-t * 60)
    boom = np.sin(2 * np.pi * 70 * t * np.exp(-t * 3)) * np.exp(-t * 9)
    tail = np.convolve(rng.normal(0, 1, t.size) * np.exp(-t * 4), np.ones(40) / 40, "same")
    x = 1.0 * crack + 0.9 * boom + 0.25 * tail
    # 간단한 에코
    for d, g in ((0.11, 0.35), (0.23, 0.2), (0.41, 0.1)):
        n = int(d * SR)
        x[n:] += g * x[:-n]
    return 0.95 * x / np.abs(x).max()


def beep(freq=880.0, dur=0.18) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(1, t * 200) * np.exp(-t * 8)
    return 0.5 * np.sin(2 * np.pi * freq * t) * env


def turn() -> np.ndarray:
    """술래가 뒤도는 기계음 (하강 스윕)."""
    t = np.arange(int(SR * 0.5)) / SR
    f = 900 * np.exp(-t * 4) + 120
    phase = 2 * np.pi * np.cumsum(f) / SR
    return 0.45 * np.sign(np.sin(phase)) * np.exp(-t * 5) * np.minimum(1, t * 100)


# (문구, say 속도, 음높이 배율, 뒤 쉼(초)) — 느리게 끌다가 끝을 빠르게 몰아치는 리듬
CHANT_SEGMENTS = [
    ("무궁화", 105, 1.22, 0.06),
    ("꽃이", 120, 1.14, 0.10),
    ("피었습니다", 230, 1.26, 0.0),
]


def _say(text: str, rate: int, voice: str, d: Path) -> np.ndarray:
    aiff, wav = d / "s.aiff", d / "s.wav"
    subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", str(aiff), text], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", str(aiff), str(wav)], check=True)
    with wave.open(str(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
    nz = np.flatnonzero(np.abs(x) > 0.01)  # 앞뒤 무음 자르기
    return x[nz[0]:nz[-1] + 1] if nz.size else x


def _pitch(x: np.ndarray, factor: float) -> np.ndarray:
    """리샘플링으로 음높이를 올린다 (길이도 함께 짧아짐 → 인형 같은 높은 목소리)."""
    idx = np.arange(0, len(x) - 1, factor)
    return np.interp(idx, np.arange(len(x)), x)


def _hall(x: np.ndarray) -> np.ndarray:
    """빈 공간 울림: 짧은 반사음 여러 개 + 꼬리."""
    tail = int(SR * 0.6)
    y = np.concatenate([x, np.zeros(tail)])
    for d, g in ((0.045, 0.32), (0.083, 0.24), (0.131, 0.17), (0.197, 0.11), (0.29, 0.07)):
        n = int(d * SR)
        y[n:] += g * y[:-n].copy()
    return y


def chant(voice: str) -> bool:
    if sys.platform != "darwin" or not shutil.which("say"):
        print("chant: macOS가 아니라 건너뜀 (voices/<이름>/chant.wav 로 직접 녹음을 넣으세요)")
        return False
    parts = []
    with tempfile.TemporaryDirectory() as d:
        for text, rate, pitch, gap in CHANT_SEGMENTS:
            seg = _pitch(_say(text, rate, voice, Path(d)), pitch)
            fade = np.minimum(1, np.minimum(np.arange(len(seg)), np.arange(len(seg))[::-1]) / 300)
            parts += [seg * fade, np.zeros(int(gap * SR))]
    y = _hall(np.concatenate(parts))
    voice_dir = OUT.parent / "voices" / "기계음"
    voice_dir.mkdir(parents=True, exist_ok=True)
    write_wav(voice_dir / "chant.wav", 0.9 * y / np.abs(y).max())
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Yuna")
    ap.add_argument("--skip-chant", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    write_wav(OUT / "gunshot.wav", gunshot())
    write_wav(OUT / "beep.wav", beep())
    write_wav(OUT / "turn.wav", turn())
    if not args.skip_chant:
        chant(args.voice)
    print("생성 완료:", sorted(p.name for p in OUT.glob("*.wav")))


if __name__ == "__main__":
    main()
