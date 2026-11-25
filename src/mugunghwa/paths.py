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
