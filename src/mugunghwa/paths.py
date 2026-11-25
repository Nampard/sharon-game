"""에셋 경로 헬퍼. PyInstaller 번들(sys._MEIPASS)과 개발 환경 모두 지원 (ADR-0006)."""
from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def asset(*parts: str) -> Path:
    return project_root().joinpath("assets", *parts)


def user_dir() -> Path:
    """사용자가 고치는 파일(config.json, voices/)의 위치.
    exe로 실행하면 exe가 있는 폴더(어디서 더블클릭하든 같은 곳), 개발 중에는 현재 폴더."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()
