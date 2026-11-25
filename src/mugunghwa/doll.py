"""술래 캐릭터: 색동 한복을 입은 거대한 소녀 인형 (자체 디자인, ADR-0007).

300x460 기준 좌표로 오프스크린 서피스에 그린 뒤 원하는 크기로 줄여 붙인다.
facing: 0=등(뒷모습), 1=얼굴(앞모습). 뒤도는 순간은 가로로 눌렀다 펴는 방식으로 연출.
"""
from __future__ import annotations

import math

import pygame

W, H = 300, 460
SKIN = (250, 232, 220)
CHEEK = (245, 150, 160)
HAIR = (22, 18, 20)
HAIR_HI = (60, 50, 55)
RIBBON = (200, 20, 40)          # 댕기
JEOGORI = (255, 250, 240)       # 저고리 몸판
GOREUM = (200, 20, 40)          # 옷고름
CHIMA = (150, 18, 50)           # 치마 (짙은 자주)
CHIMA_SHADE = (120, 10, 40)
SAEKDONG = [(220, 40, 50), (250, 200, 40), (40, 150, 90), (40, 90, 200), (240, 120, 160), (255, 255, 255)]
SHOE = (30, 30, 30)

TURN_S = 0.35


def _sleeve(s, x_dir: int, cx: int):
    """색동 소매: 어깨에서 아래로 내려온 줄무늬 팔."""
    x0 = cx + x_dir * 58
    for i, col in enumerate(SAEKDONG * 2):
        y = 190 + i * 13
        if y > 320:
            break
        rect = pygame.Rect(0, y, 34, 14)
        rect.centerx = x0 + x_dir * int(i * 1.5)
        pygame.draw.rect(s, col, rect)
    hand = (x0 + x_dir * 18, 336)
    pygame.draw.circle(s, SKIN, hand, 13)


def _body(s, cx: int, front: bool):
    # 치마 (사다리꼴 + 주름)
    pygame.draw.polygon(s, CHIMA, [(cx - 50, 230), (cx + 50, 230), (cx + 100, 420), (cx - 100, 420)])
    for i in range(-3, 4):
        pygame.draw.line(s, CHIMA_SHADE, (cx + i * 12, 240), (cx + i * 28, 418), 3)
    # 버선/신발
    for dx in (-30, 30):
        pygame.draw.ellipse(s, SHOE, (cx + dx - 18, 414, 36, 18))
    _sleeve(s, -1, cx)
    _sleeve(s, 1, cx)
    # 저고리 몸판
    pygame.draw.polygon(s, JEOGORI, [(cx - 52, 180), (cx + 52, 180), (cx + 58, 245), (cx - 58, 245)])
    if front:
        pygame.draw.polygon(s, (230, 225, 215), [(cx - 6, 180), (cx + 30, 180), (cx - 10, 240)])  # 깃
        pygame.draw.line(s, (180, 175, 165), (cx - 30, 182), (cx + 4, 236), 3)
        # 옷고름
        pygame.draw.polygon(s, GOREUM, [(cx + 2, 226), (cx + 14, 228), (cx + 4, 290), (cx - 6, 288)])
        pygame.draw.polygon(s, GOREUM, [(cx + 8, 226), (cx + 18, 230), (cx + 24, 280), (cx + 14, 282)])
        pygame.draw.circle(s, GOREUM, (cx + 8, 228), 8)
    pygame.draw.rect(s, CHIMA, (cx - 56, 238, 112, 10))  # 치마 허리
    # 목
    pygame.draw.rect(s, SKIN, (cx - 12, 160, 24, 26))


def _head_back(s, cx: int, cy: int):
    pygame.draw.circle(s, HAIR, (cx, cy), 70)
    for i in range(3):  # 윤기 하이라이트
        pygame.draw.arc(s, HAIR_HI, (cx - 52 + i * 8, cy - 56 + i * 6, 104 - i * 16, 112 - i * 12), 1.9, 2.7, 3)
    pygame.draw.line(s, HAIR_HI, (cx, cy - 68), (cx, cy + 40), 2)  # 가르마 뒤쪽 결


def _braid(s, cx: int, cy: int):
    """등 뒤로 늘어진 땋은 머리 + 댕기."""
    for k in range(7):
        y = cy + 60 + k * 18
        pygame.draw.ellipse(s, HAIR, (cx - 14, y, 28, 22))
        pygame.draw.line(s, HAIR_HI, (cx - 8, y + 4), (cx + 8, y + 16), 2)
    tail_y = cy + 60 + 7 * 18
    pygame.draw.polygon(s, RIBBON, [(cx - 16, tail_y), (cx + 16, tail_y), (cx + 12, tail_y + 60), (cx, tail_y + 48), (cx - 12, tail_y + 60)])


def _head_front(s, cx: int, cy: int, now: float, glow: float):
    # 뒷머리 실루엣
    pygame.draw.circle(s, HAIR, (cx, cy), 72)
    # 얼굴
    pygame.draw.ellipse(s, SKIN, (cx - 56, cy - 46, 112, 120))
    # 가르마 앞머리 (가운데 가르마로 양옆에 쓸어 넘김)
    pygame.draw.polygon(s, HAIR, [(cx, cy - 72), (cx - 70, cy - 20), (cx - 62, cy + 10), (cx - 30, cy - 34), (cx, cy - 46)])
    pygame.draw.polygon(s, HAIR, [(cx, cy - 72), (cx + 70, cy - 20), (cx + 62, cy + 10), (cx + 30, cy - 34), (cx, cy - 46)])
    # 볼
    for dx in (-32, 32):
        cheek = pygame.Surface((36, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(cheek, (*CHEEK, 150), cheek.get_rect())
        s.blit(cheek, (cx + dx - 18, cy + 24))
    # 눈 (검은 큰 눈 + 빛나는 홍채, 좌우로 훑기)
    scan = math.sin(now * 2.2) * 6
    for dx in (-24, 24):
        ex, ey = cx + dx, cy + 8
        pygame.draw.ellipse(s, (20, 20, 25), (ex - 15, ey - 12, 30, 24))
        if glow > 0:
            halo = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 30, 30, int(110 * glow)), (20, 20), 16)
            s.blit(halo, (ex - 20 + scan, ey - 20))
            pygame.draw.circle(s, (255, 40, 40), (int(ex + scan), ey), 8)
            pygame.draw.circle(s, (255, 220, 220), (int(ex + scan) - 2, ey - 3), 2)
        else:
            pygame.draw.circle(s, (70, 50, 40), (ex, ey), 7)
            pygame.draw.circle(s, (255, 255, 255), (ex - 3, ey - 4), 2)
        pygame.draw.arc(s, HAIR, (ex - 17, ey - 18, 34, 20), 0.3, 2.8, 3)  # 쌍꺼풀/속눈썹 선
    # 입 (작게 다문 미소)
    pygame.draw.arc(s, (190, 60, 70), (cx - 10, cy + 40, 20, 12), 3.5, 5.9, 3)
    # 댕기 리본이 옆으로 살짝 보임
    pygame.draw.polygon(s, RIBBON, [(cx + 58, cy + 40), (cx + 78, cy + 52), (cx + 64, cy + 64)])


HEAD_BOX = (0, 0, W, 190)  # 머리 영역 (몸과 따로 눌러서 '고개만 돌아가게')


class Doll:
    def __init__(self) -> None:
        self._surf = pygame.Surface((W, H), pygame.SRCALPHA)
        self._head = pygame.Surface((W, HEAD_BOX[3]), pygame.SRCALPHA)

    @staticmethod
    def facing(state: str, since: float, now: float) -> float:
        """상태와 전환 시각으로 얼굴 방향(0=뒤, 1=앞)을 구한다."""
        t = min(1.0, max(0.0, (now - since) / TURN_S))
        if state == "RED":
            return t
        if state == "GREEN":
            return 1.0 - t
        return 1.0 if state in ("COUNTDOWN", "RESULT") else 0.0  # 카운트다운엔 참가자를 노려보다가 GREEN에서 돌아섬

    def draw(self, target: pygame.Surface, midtop: tuple[int, int], height: int,
             facing: float, now: float, glow: float = 1.0, body_front: bool = False) -> pygame.Rect:
        """body_front=False면 몸은 등을 보인 채 고개만 돌아간다 (게임 중 연출)."""
        cx, cy = W // 2, 100
        s, head = self._surf, self._head
        s.fill((0, 0, 0, 0))
        head.fill((0, 0, 0, 0))
        _body(s, cx, body_front)
        if not body_front and facing < 0.5:
            _braid(s, cx, cy)  # 뒤통수를 보일 때만 땋은 머리가 보인다
        if facing >= 0.5:
            _head_front(head, cx, cy, now, glow)
        else:
            _head_back(head, cx, cy)

        # 고개 돌리는 연출: 머리만 가로로 눌렸다 펴짐
        squash = max(0.06, abs(2 * facing - 1))
        hw = max(1, int(W * squash))
        squashed = pygame.transform.smoothscale(head, (hw, HEAD_BOX[3]))
        s.blit(squashed, squashed.get_rect(midtop=(cx, 0)))

        scale = height / H
        img = pygame.transform.smoothscale(s, (int(W * scale), height))
        rect = img.get_rect(midtop=midtop)
        target.blit(img, rect)
        return rect


class ImageDoll:
    """assets/images/doll/ 의 PNG 스프라이트(뒤·앞·붉은 눈)를 쓰는 술래. 파일이 없으면 make_doll()이 코드 인형으로 대체."""

    FILES = {"back": "doll_back.png", "front": "doll_front.png", "red": "doll_front_red.png"}

    def __init__(self, folder) -> None:
        self.images = {k: _load_sprite(folder / f) for k, f in self.FILES.items()}
        self._cache: dict[tuple[str, int, int], pygame.Surface] = {}

    def _scaled(self, key: str, w: int, h: int) -> pygame.Surface:
        ck = (key, w, h)
        if ck not in self._cache:
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[ck] = pygame.transform.smoothscale(self.images[key], (w, h))
        return self._cache[ck]

    def draw(self, target: pygame.Surface, midtop: tuple[int, int], height: int,
             facing: float, now: float, glow: float = 1.0, body_front: bool = False) -> pygame.Rect:
        key = "back" if facing < 0.5 else ("red" if glow > 0 else "front")
        img = self.images[key]
        base_w = int(img.get_width() * height / img.get_height())
        squash = max(0.06, abs(2 * facing - 1))  # 몸 전체를 가로로 눌렀다 펴서 돌아서는 연출
        surf = self._scaled(key, max(1, int(base_w * squash)), height)
        rect = surf.get_rect(midtop=midtop)
        target.blit(surf, rect)
        return rect


def _load_sprite(path) -> pygame.Surface:
    """PNG 로드. 알파가 없고 배경이 초록(#00FF00 계열)이면 크로마키로 지운 뒤 여백을 잘라낸다."""
    import numpy as np

    img = pygame.image.load(str(path))
    img = img.convert_alpha() if pygame.display.get_init() and pygame.display.get_surface() else img
    rgb = pygame.surfarray.array3d(img).astype(int)
    try:
        alpha = pygame.surfarray.array_alpha(img)
    except ValueError:
        alpha = np.full(rgb.shape[:2], 255)
    if alpha.min() == 255:  # 투명 배경이 아니면 초록 배경 제거
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        green = (g > 150) & (g > r + 60) & (g > b + 60)
        alpha = np.where(green, 0, 255)
        # 가장자리 초록 번짐 줄이기
        spill = (g > r) & (g > b) & ~green
        rgb[..., 1] = np.where(spill, np.maximum(r, b), g)
    alpha = np.where(alpha < 48, 0, alpha)  # 생성 이미지의 옅은 배경 얼룩 제거
    out = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    pygame.surfarray.blit_array(out, rgb.astype(np.uint8))
    pa = pygame.surfarray.pixels_alpha(out)
    pa[:] = alpha.astype(np.uint8)
    del pa
    return out.subsurface(out.get_bounding_rect(min_alpha=48)).copy()


def make_doll():
    from .paths import asset

    folder = asset("images", "doll")
    if all((folder / f).exists() for f in ImageDoll.FILES.values()):
        try:
            return ImageDoll(folder)
        except Exception as e:  # 이미지가 깨져도 게임은 돌게
            print("인형 이미지 로딩 실패, 코드 인형 사용:", e)
    return Doll()
