"""게임 설정과 난이도 프리셋. 실행 폴더의 config.json 으로 덮어쓸 수 있다."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from .judge import JudgeParams

@dataclass(frozen=True)
class Rules:
    """술래의 행동 규칙 (난이도별)."""
    red_min_s: float = 2.0
    red_max_s: float = 4.0
    fake_chance: float = 0.0    # 구호를 중간에 끊고 갑자기 돌아볼 확률
    snap_chance: float = 0.0    # 돌아선 직후(0.35~0.7초) 다시 홱 돌아볼 확률
    accelerate: bool = False    # 라운드가 지날수록 느린 구호 속도를 제외


# judge: 움직임 판정(ADR-0004), rules: 술래 행동
DIFFICULTIES: dict[str, dict] = {
    "easy": dict(
        judge=dict(threshold=0.06, center_threshold=0.08, grace_ms=700, confirm_frames=4),
        rules=Rules(2.0, 4.0)),
    "normal": dict(
        judge=dict(threshold=0.035, center_threshold=0.05, grace_ms=450, confirm_frames=3),
        rules=Rules(1.5, 4.5, fake_chance=0.2, snap_chance=0.15, accelerate=True)),
    "hard": dict(
        judge=dict(threshold=0.025, center_threshold=0.04, grace_ms=350, confirm_frames=2),
        rules=Rules(1.2, 5.0, fake_chance=0.3, snap_chance=0.25, accelerate=True)),
    "hell": dict(
        judge=dict(threshold=0.018, center_threshold=0.03, grace_ms=280, confirm_frames=2),
        rules=Rules(1.0, 6.0, fake_chance=0.4, snap_chance=0.35, accelerate=True)),
}
DIFFICULTY_LABELS = {"easy": "쉬움", "normal": "보통", "hard": "어려움", "hell": "지옥"}
DIFFICULTY_ORDER = ["easy", "normal", "hard", "hell"]


@dataclass
class GameConfig:
    camera_index: int = 0
    camera_width: int = 1280
    camera_height: int = 720
    mirror: bool = True

    model: str = "yolo11n-pose.pt"
    imgsz: int = 640
    device: str | None = None      # None=자동, "cpu", "mps", "cuda:0"
    det_conf: float = 0.4
    kp_conf: float = 0.5
    smooth_frames: int = 3

    difficulty: str = "normal"
    voice: str = "소녀 메가폰"       # 목소리 폴더 이름 또는 "무작위" (audio.py)
    time_limit_s: float = 90.0
    countdown_s: float = 3.0
    chant_speeds: list[float] = field(default_factory=lambda: [0.7, 0.85, 1.0, 1.25, 1.5, 1.8, 2.2])
    # 승리 버튼(대형 키보드 스위치)이 보내는 키 이름 — 문자열 하나 또는 목록 (게임 중에만 승리 버튼으로 동작)
    win_key: str | list[str] = field(default_factory=lambda: ["space", "return"])
    button_ends_game: bool = True  # True: 첫 버튼 = 게임 종료, False: 누른 사람만 통과하고 계속
    missing_out_ms: float = 1500.0  # RED 중 이만큼 안 보이면 이탈 탈락

    window_width: int = 1280
    window_height: int = 720
    fullscreen: bool = False
    debug: bool = True

    def judge_params(self) -> JudgeParams:
        preset = DIFFICULTIES[self.difficulty]["judge"]
        return JudgeParams(kp_conf=self.kp_conf, smooth_frames=self.smooth_frames, **preset)

    def rules(self) -> Rules:
        return DIFFICULTIES[self.difficulty]["rules"]


SAVED_IN_SETTINGS = ("camera_index", "voice", "difficulty", "time_limit_s")


def save_config(cfg: GameConfig, path: str | Path = "config.json",
                keys: tuple[str, ...] = SAVED_IN_SETTINGS) -> None:
    """설정 화면에서 바꾼 값만 config.json 에 덮어쓴다 (사용자가 직접 적은 다른 값은 유지)."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    data.update({k: getattr(cfg, k) for k in keys})
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config(path: str | Path = "config.json") -> GameConfig:
    cfg = GameConfig()
    p = Path(path)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        known = {f.name for f in fields(GameConfig)}
        cfg = replace(cfg, **{k: v for k, v in data.items() if k in known})
    return cfg
