"""진입점: 스레드 시작 + pygame 메인 루프."""
from __future__ import annotations

import time
from dataclasses import replace

import pygame

from . import keys
from .audio import Audio
from .camera import Camera
from .config import load_config
from .detector import DetectorThread, YoloPoseDetector
from .game import LOBBY, RESULT, TITLE, Game
from .render import Renderer
from .settings import SettingsMenu

DIFF_KEYS = {"1": "easy", "2": "normal", "3": "hard", "4": "hell"}


def _set_params(game: Game, params) -> None:
    game.registry.params = params
    for pl in game.registry.players:
        pl.judge.params = params


def main() -> None:
    cfg = load_config()
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.display.set_caption("무궁화 꽃이 피었습니다 - 캠 챌린지")
    flags = pygame.RESIZABLE | (pygame.FULLSCREEN if cfg.fullscreen else 0)
    screen = pygame.display.set_mode((cfg.window_width, cfg.window_height), flags)
    pygame.key.stop_text_input()  # 한글 입력기(IME)가 키 입력을 가로채지 않게
    win_keys = [cfg.win_key] if isinstance(cfg.win_key, str) else list(cfg.win_key)

    audio = Audio(cfg.chant_speeds, cfg.voice)
    cfg.voice = audio.selected  # 저장된 목소리 폴더가 사라졌으면 다른 목소리로 바뀐다
    renderer = Renderer()
    renderer.chant_timing = audio.chant_timing
    game = Game(cfg, audio.prepare_chant)

    camera = Camera(cfg.camera_index, cfg.camera_width, cfg.camera_height, cfg.mirror)
    camera.try_open(time.monotonic())
    settings = SettingsMenu(cfg, camera, audio,
                            on_difficulty=lambda: game.registry.set_params(cfg.judge_params()))
    detector = DetectorThread(
        camera.frames, lambda: YoloPoseDetector(cfg.model, cfg.imgsz, cfg.det_conf, cfg.device))
    detector.start()

    clock = pygame.time.Clock()
    det_seq = 0
    debug = cfg.debug
    running = True
    while running:
        now = time.monotonic()
        camera.try_open(now)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                renderer.last_key = keys.describe(ev)
                if settings.open:
                    settings.handle(ev, now)
                elif keys.matches(ev, "s") and game.state == TITLE:
                    settings.show()
                elif keys.matches(ev, "escape"):
                    running = False
                elif keys.matches(ev, "f11"):
                    pygame.display.toggle_fullscreen()
                elif keys.matches(ev, *win_keys) and game.state not in (TITLE, LOBBY, RESULT):
                    game.press_button(now)
                elif keys.matches(ev, "space"):
                    if game.state in (TITLE, RESULT):
                        audio.stop_chant()
                        game.to_lobby(now)
                    elif game.state == LOBBY:
                        game.start(now)
                elif keys.matches(ev, "d"):
                    debug = not debug
                elif game.state in (TITLE, LOBBY) and any(keys.matches(ev, k) for k in DIFF_KEYS):
                    cfg.difficulty = next(v for k, v in DIFF_KEYS.items() if keys.matches(ev, k))
                    game.registry.set_params(cfg.judge_params())
                elif keys.matches(ev, "equals", "kp_plus", "minus", "kp_minus"):
                    up = keys.matches(ev, "equals", "kp_plus")
                    p = game.registry.params
                    _set_params(game, replace(p, threshold=round(p.threshold * (1.15 if up else 1 / 1.15), 4)))

        seq, det = detector.results.get()
        if det is not None and seq != det_seq:
            det_seq = seq
            game.on_detection(det.persons, now)
        game.update(now)

        for e in game.pop_events():
            if e.kind == "chant":
                audio.play_chant(e.speed)
            elif e.kind in ("turn", "snap"):
                audio.stop_chant()
                audio.play("turn")
            elif e.kind == "shot":
                audio.play("shot")
                renderer.on_shot(now)
            elif e.kind in ("beep", "win"):
                audio.play("beep")
            elif e.kind == "end":
                audio.stop_chant()

        status = camera.error or detector.error
        if status is None and not detector.ready:
            status = "인식 모델 불러오는 중..."
        if det is not None and not settings.open:
            frame = det.frame
        else:
            frame = camera.frames.get()[1]  # 설정 중에는 카메라 원본을 바로 보여 준다 (전환 확인용)
        renderer.draw(screen, frame, game, now, det.fps if det else 0.0, status, debug,
                      settings if settings.open else None)
        pygame.display.flip()
        clock.tick(60)

    camera.stop()
    detector.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
