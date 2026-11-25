"""키 입력을 '물리 키 위치(스캔코드)' 기준으로 판별한다.

한글 자판에서는 D 키가 'ㅇ' 키코드로 들어와 `ev.key == K_d` 가 실패한다 (macOS·Windows 공통).
스캔코드는 자판 언어와 무관하므로 이를 우선 사용하고, 키코드는 보조로 확인한다.
"""
from __future__ import annotations

import pygame


def scancode(name: str) -> int | None:
    """'d', '1', 'return', 'space', 'f11', 'kp_plus' 같은 이름 → SDL 스캔코드."""
    return getattr(pygame, "KSCAN_" + name.upper(), None)


def matches(ev: pygame.event.Event, *names: str) -> bool:
    for name in names:
        sc = scancode(name)
        if sc is not None and getattr(ev, "scancode", None) == sc:
            return True
        try:
            if ev.key == pygame.key.key_code(name):
                return True
        except ValueError:
            pass
    return False


def describe(ev: pygame.event.Event) -> str:
    """디버그 표시용: 대형 스위치가 어떤 키를 보내는지 확인할 때 쓴다."""
    name = pygame.key.name(ev.key) or "?"
    return f"{name} (scancode {getattr(ev, 'scancode', '?')})"
