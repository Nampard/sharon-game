"""pygame 화면 그리기. 게임 상태를 읽기만 한다.

디자인 토큰 (2~4m 떨어진 플레이어가 한눈에 읽는 화면):
- 인주(SEAL) 빨강: 멈춤·탈락. '도장'이 이 화면의 유일한 강한 장식이다.
- 단청 초록(PINE): 움직여도 되는 구간. 황(GOLD): 승리. 한지(HANJI): 흰색 대신 쓰는 글자·이름표 색.
- 색동(SAEKDONG): 술래 인형 소매에서 가져온 줄무늬. 남은 시간 막대로만 쓴다.
"""
from __future__ import annotations

import random
from pathlib import Path

import cv2
import numpy as np
import pygame

from .config import DIFFICULTY_LABELS, DIFFICULTY_ORDER
from .doll import Doll, make_doll
from .game import COUNTDOWN, GREEN, LOBBY, RED, RESULT, TITLE, Game
from .paths import asset
from .players import ALIVE, FINISHED, OUT

SEAL = (196, 20, 43)
PINE = (30, 140, 90)
GOLD = (231, 177, 42)
HANJI = (242, 235, 221)
INK = (24, 22, 28)
DIM = (150, 146, 140)
SAEKDONG = [(214, 40, 52), (245, 196, 48), (42, 150, 92), (44, 92, 196), (236, 120, 160), (242, 235, 221)]

CHANT = "무궁화꽃이피었습니다"
# 가사 타이밍은 목소리별: audio.chant_timing() → (글자 비중 또는 None=균등, 말 시작 초, 말 끝 초)

KOREAN_FONT_CANDIDATES = [
    "malgungothic", "malgun gothic", "applesdgothicneo", "apple sd gothic neo",
    "nanumgothic", "notosanscjkkr", "notosanskr", "notosans cjk kr",
]
KOREAN_FONT_FILES = [
    "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc", "/Library/Fonts/AppleGothic.ttf",
]


def _font_path() -> tuple[str | None, bool]:
    """(경로, 번들 폰트 여부). assets/fonts 의 폰트가 있으면 우선 사용."""
    folder = asset("fonts")
    bundled = sorted(folder.glob("*.[ot]t[fc]")) if folder.exists() else []
    if bundled:
        return str(bundled[0]), True
    for name in KOREAN_FONT_CANDIDATES:
        path = pygame.font.match_font(name, bold=True)
        if path:
            return path, False
    for f in KOREAN_FONT_FILES:
        if Path(f).exists():
            return f, False
    return None, False


class Renderer:
    def __init__(self) -> None:
        self._path, self._bundled = _font_path()
        self._fonts: dict[int, pygame.font.Font] = {}
        self.flash_until = 0.0
        self.shake_until = 0.0
        self.doll = make_doll()
        self.last_key = "-"
        self.chant_timing = lambda: (None, 0.0, 2.0)  # main에서 audio.chant_timing 으로 교체

    # ---- 글자 ----
    def font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            f = pygame.font.Font(self._path, size)
            if not self._bundled and size >= 28:
                f.set_bold(True)  # 시스템 고딕은 큰 글자에서 굵게
            self._fonts[size] = f
        return self._fonts[size]

    def render(self, msg: str, size: int, color) -> pygame.Surface:
        return self.font(size).render(msg, True, color)

    def text(self, surf, msg, size, color, center=None, topleft=None, midleft=None, shadow=True):
        img = self.render(msg, size, color)
        rect = img.get_rect()
        if center:
            rect.center = center
        if topleft:
            rect.topleft = topleft
        if midleft:
            rect.midleft = midleft
        if shadow:
            sh = self.render(msg, size, (0, 0, 0))
            sh.set_alpha(150)
            surf.blit(sh, rect.move(2, 3))
        surf.blit(img, rect)
        return rect

    def tag(self, surf, msg, size, bottomleft, fg=INK, bg=HANJI) -> pygame.Rect:
        """이름표: 한지색 바탕에 먹색 글자."""
        img = self.render(msg, size, fg)
        pad_x, pad_y = size // 3, size // 6
        rect = pygame.Rect(0, 0, img.get_width() + pad_x * 2, img.get_height() + pad_y * 2)
        rect.bottomleft = bottomleft
        pygame.draw.rect(surf, bg, rect, border_radius=3)
        surf.blit(img, (rect.x + pad_x, rect.y + pad_y))
        return rect

    def stamp(self, surf, msg, size, center, angle=-7.0, scale=1.0, alpha=255) -> None:
        """인주 도장: 빨간 바탕, 안쪽 한지색 테두리, 한지색 글자, 살짝 기울임."""
        img = self.render(msg, size, HANJI)
        pad = int(size * 0.38)
        w, h = img.get_width() + pad * 2, img.get_height() + pad * 2
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, SEAL, s.get_rect(), border_radius=max(4, size // 10))
        inset = max(3, size // 14)
        pygame.draw.rect(s, HANJI, s.get_rect().inflate(-inset * 2, -inset * 2),
                         max(2, size // 22), border_radius=max(3, size // 12))
        s.blit(img, (pad, pad))
        s = pygame.transform.rotozoom(s, angle, scale)
        s.set_alpha(alpha)
        surf.blit(s, s.get_rect(center=center))

    def on_shot(self, now: float) -> None:
        self.flash_until = now + 0.3
        self.shake_until = now + 0.4

    # ---- 메인 ----
    def draw(self, screen: pygame.Surface, frame: np.ndarray | None, game: Game, now: float,
             fps: float, status: str | None, debug: bool, settings=None) -> None:
        W, H = screen.get_size()
        canvas = pygame.Surface((W, H))
        canvas.fill(INK)

        scale, ox, oy = 1.0, 0, 0
        if frame is not None:
            fh, fw = frame.shape[:2]
            scale = max(W / fw, H / fh)  # 화면을 꽉 채운다 (잘리는 쪽은 가장자리)
            dw, dh = int(fw * scale), int(fh * scale)
            ox, oy = (W - dw) // 2, (H - dh) // 2
            rgb = cv2.cvtColor(cv2.resize(frame, (dw, dh)), cv2.COLOR_BGR2RGB)
            if game.state == RED:
                rgb = (rgb * np.array([1.0, 0.72, 0.72])).astype(np.uint8)
            canvas.blit(pygame.image.frombuffer(rgb.tobytes(), (dw, dh), "RGB"), (ox, oy))

        if game.state in (LOBBY, COUNTDOWN, GREEN, RED, RESULT):
            self._players(canvas, game, scale, ox, oy, debug)
        if game.state in (COUNTDOWN, GREEN, RED, RESULT):
            self._doll(canvas, game, W, H, now)
        if game.state in (GREEN, RED):
            self._hud(canvas, game, W, H, now)
        if game.state == RED:
            pygame.draw.rect(canvas, SEAL, canvas.get_rect(), 12)

        if settings is not None:
            self._settings(canvas, settings, W, H)
        else:
            {TITLE: self._title, LOBBY: self._lobby, COUNTDOWN: self._countdown,
             RESULT: self._result}.get(game.state, lambda *a: None)(canvas, game, W, H, now)

        if debug and game.state in (GREEN, RED):
            p = game.registry.params
            info = (f"인식 {fps:4.1f}fps   {DIFFICULTY_LABELS[game.cfg.difficulty]}   "
                    f"기준 {p.threshold:.3f} (+/-)   유예 {p.grace_ms:.0f}ms   마지막 키 {self.last_key}")
            self.text(canvas, info, 17, HANJI, topleft=(20, H - 32))
        if status:
            self.tag(canvas, status, 22, (20, H - 44), fg=HANJI, bg=SEAL)

        dx = dy = 0
        if now < self.shake_until:
            amp = 16 * (self.shake_until - now) / 0.4
            dx, dy = random.uniform(-amp, amp), random.uniform(-amp, amp)
        screen.fill(INK)
        screen.blit(canvas, (dx, dy))
        if now < self.flash_until:
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((255, 240, 230, int(190 * (self.flash_until - now) / 0.3)))
            screen.blit(flash, (0, 0))

    # ---- 참가자 ----
    def _brackets(self, s, rect: pygame.Rect, color, width=5) -> None:
        """사각형 대신 네 모서리 괄호: 술래가 겨누는 조준선 느낌."""
        L = max(14, min(rect.w, rect.h) // 5)
        x1, y1, x2, y2 = rect.left, rect.top, rect.right, rect.bottom
        for (cx, cy, sx, sy) in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
            pygame.draw.line(s, color, (cx, cy), (cx + sx * L, cy), width)
            pygame.draw.line(s, color, (cx, cy), (cx, cy + sy * L), width)

    def _players(self, s, game: Game, scale, ox, oy, debug):
        thr = game.registry.params.threshold
        for pl in game.registry.players:
            x1, y1, x2, y2 = (pl.bbox * scale + [ox, oy, ox, oy]).astype(int)
            rect = pygame.Rect(x1, y1, max(1, x2 - x1), max(1, y2 - y1))
            tag_pos = (rect.left, max(34, rect.top - 6))
            if pl.status == OUT:
                wash = pygame.Surface(rect.size, pygame.SRCALPHA)
                wash.fill((20, 18, 24, 120))
                s.blit(wash, rect)
                self._brackets(s, rect, SEAL, 4)
                self.tag(s, f"{pl.number}번", 26, tag_pos, fg=HANJI, bg=SEAL)
                self.stamp(s, "탈락", max(28, min(64, rect.w // 3)), rect.center, angle=-12)
                continue
            if pl.status == FINISHED:
                self._brackets(s, rect, GOLD, 6)
                self.tag(s, f"{pl.number}번 통과", 26, tag_pos, fg=INK, bg=GOLD)
                continue
            color = PINE if game.state != RED else HANJI
            if game.state == RED and pl.last_score is not None:
                r = min(pl.last_score / thr, 1.0)  # 움직일수록 초록→빨강
                color = tuple(int(PINE[i] + (SEAL[i] - PINE[i]) * r) for i in range(3))
            if not pl.visible:
                color = DIM
            self._brackets(s, rect, color, 5)
            t = self.tag(s, f"{pl.number}번", 26, tag_pos)
            if debug and game.state == RED:
                sc = "-" if pl.last_score is None else f"{pl.last_score:.3f}"
                self.text(s, sc, 17, HANJI, midleft=(t.right + 8, t.centery))

    # ---- 술래 / 진행 표시 ----
    def _doll(self, s, game: Game, W, H, now):
        facing = Doll.facing(game.state, game.state_since, now)
        glow = 1.0 if game.state == RED else 0.0
        self.doll.draw(s, (W - int(H * 0.17), int(H * 0.06)), int(H * 0.52), facing, now, glow)

    def _time_bar(self, s, game: Game, W):
        """색동 막대: 남은 시간만큼 오른쪽에서 줄어든다."""
        frac = game.time_left / max(game.cfg.time_limit_s, 1)
        h, stripe = 14, max(24, W // 48)
        width = int(W * frac)
        pygame.draw.rect(s, (40, 38, 44), (0, 0, W, h))
        for i, x in enumerate(range(0, width, stripe)):
            pygame.draw.rect(s, SAEKDONG[i % len(SAEKDONG)], (x, 0, min(stripe, width - x), h))

    def _hud(self, s, game: Game, W, H, now):
        self._time_bar(s, game, W)
        t = game.time_left
        reg = game.registry
        self.text(s, f"{int(t)}초", 40, HANJI if t > 10 else SEAL, topleft=(22, 22))
        self.text(s, f"남은 사람 {len(reg.alive)}명 / {len(reg.players)}명", 22, HANJI, topleft=(24, 72))

        if game.state == GREEN:
            self._chant(s, game, W, now)
        else:
            k = min(1.0, (now - game.state_since) / 0.12)  # 도장 찍히는 순간: 크게 → 제자리
            self.stamp(s, "멈춰", 76, (W // 2, int(H * 0.13)), angle=-6, scale=1.6 - 0.6 * k)

    def _chant(self, s, game: Game, W, now):
        """구호 가사: 소리에 맞춰 한 글자씩 켜진다. 페이크로 끊기면 그 자리에서 멈춘다."""
        weights, a, b = self.chant_timing()
        weights = weights if weights and len(weights) == len(CHANT) else [1.0] * len(CHANT)
        t = (now - game.state_since) * game.speed  # 속도 1.0 기준 시각
        p = (t - a) / max(0.2, b - a)
        total = sum(weights)
        lit, acc = 0, 0.0
        for w in weights:
            acc += w / total
            if p >= acc - (w / total) * 0.5:
                lit += 1
        size = 58
        gap = 6
        imgs_on = [self.render(ch, size, HANJI) for ch in CHANT]
        widths = [im.get_width() for im in imgs_on]
        spaces = {2: 22, 4: 22}  # '무궁화 꽃이 피었습니다' 띄어쓰기
        total_w = sum(widths) + gap * (len(CHANT) - 1) + sum(spaces.values())
        x = (W - total_w) // 2
        y = 30
        band = pygame.Rect(x - 18, y - 4, total_w + 36, imgs_on[0].get_height() + 8)
        bs = pygame.Surface(band.size, pygame.SRCALPHA)
        bs.fill((*INK, 175))
        s.blit(bs, band)
        for i, ch in enumerate(CHANT):
            on = i < lit
            col = HANJI if on else (128, 122, 116)
            img = self.render(ch, size, col)
            if on:
                bg = pygame.Rect(x - 4, y + 4, img.get_width() + 8, img.get_height() - 4)
                pygame.draw.rect(s, PINE, bg, border_radius=4)
            sh = self.render(ch, size, (0, 0, 0))
            sh.set_alpha(120)
            s.blit(sh, (x + 2, y + 3))
            s.blit(img, (x, y))
            x += img.get_width() + gap + spaces.get(i, 0)

    # ---- 화면별 ----
    def _overlay(self, s, alpha=190):
        o = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        o.fill((*INK, alpha))
        s.blit(o, (0, 0))

    def _difficulty_row(self, s, game: Game, x, y):
        self.text(s, "난이도", 22, DIM, midleft=(x, y), shadow=False)
        x += 90
        for i, key in enumerate(DIFFICULTY_ORDER):
            label = f"{i + 1} {DIFFICULTY_LABELS[key]}"
            selected = key == game.cfg.difficulty
            r = self.tag(s, label, 24, (x, y + 20), fg=HANJI,
                         bg=SEAL if selected else (60, 56, 62))
            x = r.right + 10

    def _title(self, s, game, W, H, now):
        self._overlay(s, 215)
        self.doll.draw(s, (int(W * 0.24), int(H * 0.08)), int(H * 0.84), 1.0, now, 0.0, body_front=True)
        x = int(W * 0.46)
        self.text(s, "무궁화 꽃이", 96, HANJI, topleft=(x, int(H * 0.14)))
        self.text(s, "피었습니다", 96, SEAL, topleft=(x, int(H * 0.14) + 108))
        self.text(s, "술래가 노래하는 동안 다가가서 버튼을 누르세요.", 26, HANJI, topleft=(x + 4, int(H * 0.50)))
        self.text(s, "술래가 돌아볼 때 움직이면 탈락입니다.", 26, HANJI, topleft=(x + 4, int(H * 0.50) + 40))
        self._difficulty_row(s, game, x + 4, int(H * 0.68))
        self.text(s, "스페이스를 누르면 참가자 등록으로 넘어갑니다", 24, GOLD, topleft=(x + 4, int(H * 0.80)), shadow=False)
        self.text(s, f"S 설정   F11 전체화면   ESC 종료   마지막으로 누른 키: {self.last_key}", 17, DIM,
                  topleft=(x + 4, H - 40), shadow=False)

    def _lobby(self, s, game, W, H, now):
        n = len(game.registry.players)
        band = pygame.Rect(0, H - 120, W, 120)
        o = pygame.Surface(band.size, pygame.SRCALPHA)
        o.fill((*INK, 210))
        s.blit(o, band)
        if n:
            self.text(s, f"카메라에 {n}명이 보입니다. 서로 간격을 두고 서 주세요.", 34, HANJI, topleft=(28, H - 106))
            self.text(s, f"스페이스를 누르면 이 {n}명으로 시작합니다.", 24, GOLD, topleft=(30, H - 56), shadow=False)
        else:
            self.text(s, "카메라 앞에 서 주세요. 아직 아무도 보이지 않습니다.", 34, HANJI, topleft=(28, H - 106))
            self.text(s, "몸 전체가 화면에 들어오면 번호가 붙습니다.", 24, DIM, topleft=(30, H - 56), shadow=False)

    def _countdown(self, s, game, W, H, now):
        n = max(1, int(game.state_until - now) + 1)
        frac = (game.state_until - now) % 1.0
        self.text(s, str(n), int(220 + 60 * frac), HANJI, center=(W // 2, H // 2 - 20))
        self.text(s, "버튼을 누르면 이깁니다. 술래가 볼 때 움직이면 탈락입니다.", 28, HANJI,
                  center=(W // 2, H // 2 + 140))

    def _result(self, s, game: Game, W, H, now):
        self._overlay(s, 200)
        cx = int(W * 0.42)
        if game.winner:
            self.text(s, f"{game.winner.number}번이 이겼습니다", 92, GOLD, center=(cx, int(H * 0.26)))
        else:
            self.text(s, "아무도 살아남지 못했습니다", 80, SEAL, center=(cx, int(H * 0.26)))
        players = game.registry.players
        cols = min(len(players), 6) or 1
        cell = min(170, int(W * 0.7) // cols)
        x0 = cx - cell * cols // 2
        for i, pl in enumerate(players):
            r, c = divmod(i, cols)
            x, y = x0 + c * cell + cell // 2, int(H * 0.5) + r * 120
            if pl.status == OUT:
                self.stamp(s, f"{pl.number}번", 40, (x, y), angle=-8)
                self.text(s, pl.reason, 18, DIM, center=(x, y + 52), shadow=False)
            else:
                bg = GOLD if pl.status == FINISHED else HANJI
                img = self.render(f"{pl.number}번", 40, INK)
                w, h = img.get_width() + 2 * (40 // 3), img.get_height() + 2 * (40 // 6)
                self.tag(s, f"{pl.number}번", 40, (x - w // 2, y + h // 2), bg=bg)
                self.text(s, "통과" if pl.status == FINISHED else "생존", 18, DIM, center=(x, y + 52), shadow=False)
        self.text(s, "스페이스를 누르면 다시 시작합니다", 24, HANJI, center=(cx, H - 60), shadow=False)

    def _settings(self, s, menu, W, H):
        """오른쪽 패널에 설정 목록, 왼쪽에는 선택한 카메라 화면이 그대로 보인다."""
        panel = pygame.Rect(int(W * 0.5), 0, W - int(W * 0.5), H)
        o = pygame.Surface(panel.size, pygame.SRCALPHA)
        o.fill((*INK, 232))
        s.blit(o, panel)
        x = panel.x + 48
        self.text(s, "설정", 64, HANJI, topleft=(x, 40))
        y = 150
        for i, row in enumerate(menu.rows()):
            selected = i == menu.row
            if selected:
                pygame.draw.rect(s, SEAL, (panel.x, y - 6, 8, 64))
            self.text(s, row.label, 24, HANJI if selected else DIM, topleft=(x, y), shadow=False)
            val = f"‹  {row.value}  ›" if selected else row.value
            self.text(s, val, 34, HANJI if selected else DIM, topleft=(x + 190, y - 6), shadow=False)
            if selected and row.hint:
                self.text(s, row.hint, 18, GOLD, topleft=(x, y + 36), shadow=False)
            y += 96
        if menu.audio.errors:
            self.text(s, "불러오지 못한 목소리: " + ", ".join(menu.audio.errors)[:60], 17, SEAL,
                      topleft=(x, H - 110), shadow=False)
        self.text(s, "위아래 화살표로 고르고 좌우 화살표로 바꿉니다", 20, HANJI, topleft=(x, H - 76), shadow=False)
        self.text(s, "S 또는 ESC를 누르면 저장하고 닫습니다", 20, DIM, topleft=(x, H - 46), shadow=False)
