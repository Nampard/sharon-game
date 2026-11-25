import random

import numpy as np

from mugunghwa.config import DIFFICULTIES, GameConfig, Rules
from mugunghwa.game import COUNTDOWN, GREEN, LOBBY, RED, RESULT, Game
from mugunghwa.model import Person
from mugunghwa.players import FINISHED, OUT


def person(tid, x0, h=300.0, dx=0.0):
    kp = np.zeros((17, 3))
    kp[:, 0] = x0 + np.linspace(-30, 30, 17)
    kp[:, 1] = 100 + np.linspace(0, h, 17)
    kp[:, 2] = 0.9
    kp[[9, 10], 0] += dx
    return Person(tid, np.array([x0 - 50, 100, x0 + 50, 100 + h]), kp)


class FixedRulesConfig(GameConfig):
    """테스트용: 술래 행동을 고정(RED 3초, 페이크 없음)."""
    _rules = Rules(3.0, 3.0)

    def rules(self):
        return self._rules


def new_game(rules=None, **kw):
    cfg = FixedRulesConfig(countdown_s=1, chant_speeds=[1.0], difficulty="easy", **kw)
    if rules:
        cfg._rules = rules
    return Game(cfg, prepare_chant=lambda s: 2.0, rng=random.Random(0))


def to_red(g, persons):
    g.to_lobby(0)
    g.on_detection(persons, 0)
    assert g.start(0)
    g.update(0.0)
    assert g.state == COUNTDOWN
    g.update(1.0)
    assert g.state == GREEN
    g.update(3.0)
    assert g.state == RED
    return 3.0


def test_lobby_numbers_left_to_right_and_ignores_newcomers():
    g = new_game()
    g.to_lobby(0)
    g.on_detection([person(7, 600), person(3, 200)], 0)
    assert [(p.number, p.track_id) for p in g.registry.players] == [(1, 3), (2, 7)]
    g.start(0)
    g.on_detection([person(3, 200), person(7, 600), person(99, 1000)], 0.1)
    assert len(g.registry.players) == 2


def test_moving_in_red_gets_shot_still_survives():
    g = new_game()
    t = to_red(g, [person(1, 200), person(2, 600)])
    for i in range(20):
        now = t + 0.6 + i * 0.07
        dx = 40 if i > 4 else 0
        g.on_detection([person(1, 200), person(2, 600, dx=dx)], now)
    p1, p2 = g.registry.players
    assert p1.status != OUT
    assert p2.status == OUT and p2.reason == "움직임 감지"
    assert any(e.kind == "shot" and e.player is p2 for e in g.pop_events())


def test_moving_in_green_is_fine():
    g = new_game()
    g.to_lobby(0)
    g.on_detection([person(1, 200)], 0)
    g.start(0)
    g.update(1.0)
    for i in range(10):
        g.on_detection([person(1, 200 + i * 30)], 1.0 + i * 0.1)
    assert g.registry.players[0].status != OUT


def test_button_press_picks_closest_and_ends_game():
    g = new_game()
    t = to_red(g, [person(1, 200, h=200), person(2, 600, h=400)])
    g.on_detection([person(1, 200, h=200), person(2, 600, h=400)], t + 0.1)
    winner = g.press_button(t + 0.2)
    assert winner.number == 2 and winner.status == FINISHED
    assert g.state == RESULT and g.winner is winner


def test_track_id_switch_reconnects():
    g = new_game()
    t = to_red(g, [person(1, 200)])
    g.on_detection([person(5, 205)], t + 0.1)  # 같은 자리, 새 ID
    pl = g.registry.players[0]
    assert pl.track_id == 5 and pl.visible


def test_leaving_frame_in_red_is_out():
    g = new_game()
    t = to_red(g, [person(1, 200), person(2, 600)])
    g.on_detection([person(1, 200), person(2, 600)], t + 0.6)
    for i in range(30):
        g.on_detection([person(1, 200)], t + 0.7 + i * 0.07)
    assert g.registry.players[1].status == OUT
    assert g.registry.players[1].reason == "화면 이탈"


def test_time_limit_ends_game():
    g = new_game(time_limit_s=5)
    to_red(g, [person(1, 200)])
    g.update(6.1)
    assert g.state == RESULT
    assert g.registry.players[0].reason == "시간 초과"


def test_all_out_ends_game():
    g = new_game()
    t = to_red(g, [person(1, 200)])
    for i in range(20):
        g.on_detection([person(1, 200, dx=60 if i > 4 else 0)], t + 0.6 + i * 0.07)
    assert g.state == RESULT


def test_button_ignored_in_lobby():
    g = new_game()
    g.to_lobby(0)
    g.on_detection([person(1, 200)], 0)
    assert g.press_button(0.1) is None and g.state == LOBBY


def test_snap_back_catches_early_movers():
    g = new_game(rules=Rules(1.0, 1.0, snap_chance=1.0))
    t = to_red(g, [person(1, 200)])
    g.update(t + 1.0)                      # RED 끝 → GREEN (돌아섬)
    assert g.state == GREEN and g.snap_at is not None
    g.update(g.snap_at)                    # 곧바로 다시 돌아봄
    assert g.state == RED
    assert any(e.kind == "snap" for e in g.pop_events())


def test_fake_cuts_chant_short():
    g = new_game(rules=Rules(1.0, 1.0, fake_chance=1.0))
    t = to_red(g, [person(1, 200)])        # 첫 구호는 끊지 않음
    g.update(t + 1.0)
    assert g.state == GREEN and g.cut
    assert g.state_until - g.state_since < g.chant_full


def test_acceleration_drops_slow_speeds():
    cfg = FixedRulesConfig(chant_speeds=[0.7, 1.0, 1.5, 2.0], difficulty="easy")
    cfg._rules = Rules(accelerate=True)
    g = Game(cfg, prepare_chant=lambda s: 2.0, rng=random.Random(1))
    g.round = 10
    assert all(g._pick_speed() >= 1.5 for _ in range(50))


def test_presets_get_stricter():
    order = ["easy", "normal", "hard", "hell"]
    thr = [DIFFICULTIES[d]["judge"]["threshold"] for d in order]
    assert thr == sorted(thr, reverse=True)


def test_save_config_keeps_user_keys(tmp_path):
    import json
    from mugunghwa.config import load_config, save_config
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"device": "mps", "voice": "old"}), encoding="utf-8")
    cfg = load_config(p)
    cfg.voice, cfg.camera_index = "철수", 1
    save_config(cfg, p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["device"] == "mps" and data["voice"] == "철수" and data["camera_index"] == 1
