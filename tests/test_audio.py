import json
import os
import random
import wave

import numpy as np
import pytest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from mugunghwa import audio as audio_mod  # noqa: E402
from mugunghwa.audio import RANDOM_VOICE, Audio, speech_bounds  # noqa: E402

SR = 44100


@pytest.fixture(scope="module", autouse=True)
def mixer():
    pygame.mixer.init(SR, -16, 2, 512)
    yield
    pygame.mixer.quit()


def write_voice(folder, lead_s=1.0, speech_s=1.5, tail_s=2.0, meta=None):
    folder.mkdir(parents=True)
    t = np.arange(int(SR * speech_s)) / SR
    speech = 0.5 * np.sin(2 * np.pi * 300 * t)
    x = np.concatenate([np.zeros(int(SR * lead_s)), speech, np.zeros(int(SR * tail_s))])
    with wave.open(str(folder / "chant.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    if meta:
        (folder / "voice.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def test_speech_bounds_ignores_silence():
    x = np.concatenate([np.zeros(SR), np.ones(SR // 2) * 0.5, np.zeros(SR)])
    a, b = speech_bounds(x, SR)
    assert abs(a - SR) < SR * 0.03 and abs(b - SR * 1.5) < SR * 0.03


@pytest.fixture
def voices(tmp_path, monkeypatch):
    """내장 목소리 폴더는 비우고, 실행 폴더(voices/)에만 녹음 두 개를 둔다."""
    monkeypatch.setattr(audio_mod, "asset", lambda *p: tmp_path / "none" / "/".join(p))
    monkeypatch.chdir(tmp_path)
    write_voice(tmp_path / "voices" / "철수", lead_s=1.0, speech_s=1.5)
    write_voice(tmp_path / "voices" / "robot", lead_s=0.2, speech_s=1.0, meta={"name": "기계음"})
    return tmp_path


def test_user_voices_loaded_and_trimmed(voices):
    a = Audio([1.0, 2.0], "철수")
    assert set(a.voices) == {"철수", "기계음"}
    assert RANDOM_VOICE in a.options
    v = a.voices["철수"]
    # 앞 무음 1초는 잘려 말이 거의 바로 시작하고, 끝은 울림 여유만 남는다
    assert v.speech_start < 0.1
    assert abs((v.speech_end - v.speech_start) - 1.5) < 0.05
    assert a.prepare_chant(1.0) < 1.5 + 0.1 + 0.8 + 0.05
    assert abs(a.prepare_chant(2.0) - a.prepare_chant(1.0) / 2) < 0.02


def test_missing_saved_voice_falls_back(voices):
    a = Audio([1.0], "없는목소리")
    assert a.selected in a.voices


def test_random_voice_changes_between_rounds(voices):
    a = Audio([1.0], RANDOM_VOICE, rng=random.Random(3))
    picked = set()
    for _ in range(20):
        a.prepare_chant(1.0)
        picked.add(a.current.name)
    assert picked == {"철수", "기계음"}


def test_no_voices_runs_silently(tmp_path, monkeypatch):
    """새로 받은 저장소처럼 목소리가 하나도 없어도 게임 진행에 필요한 값이 나온다."""
    monkeypatch.setattr(audio_mod, "asset", lambda *p: tmp_path / "none" / "/".join(p))
    monkeypatch.chdir(tmp_path)
    a = Audio([1.0, 2.0], "기계음")
    assert a.voices == {} and a.options == []
    assert a.prepare_chant(2.0) == 1.5
    a.play_chant(2.0)
    assert a.chant_timing()[0] is None
