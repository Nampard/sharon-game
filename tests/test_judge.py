import numpy as np

from mugunghwa.judge import JudgeParams, MotionJudge

P = JudgeParams(threshold=0.04, center_threshold=0.06, grace_ms=500, confirm_frames=3, smooth_frames=3)
H = 400.0  # 사람 키(픽셀)


def standing(x0=300.0, y0=100.0, h=H):
    kp = np.zeros((17, 3))
    kp[:, 0] = x0 + np.linspace(-40, 40, 17) * h / H
    kp[:, 1] = y0 + np.linspace(0, h, 17)
    kp[:, 2] = 0.9
    return kp, np.array([x0 - 60 * h / H, y0, x0 + 60 * h / H, y0 + h])


def run(frames, judge=None, start_ms=600, step_ms=66):
    judge = judge or MotionJudge(P)
    res = None
    for i, (kp, box) in enumerate(frames):
        res = judge.update(kp, box, start_ms + i * step_ms)
    return judge, res


def test_still_with_jitter_survives():
    rng = np.random.default_rng(0)
    kp, box = standing()
    frames = []
    for _ in range(60):
        k = kp.copy()
        k[:, :2] += rng.normal(0, 0.006 * H, (17, 2))  # 키의 0.6% 떨림
        frames.append((k, box + rng.normal(0, 1, 4)))
    _, res = run(frames)
    assert not res.eliminated


def test_arm_move_eliminated():
    kp, box = standing()
    frames = [(kp, box)] * 3
    moved = kp.copy()
    moved[[9, 10], 0] += 0.1 * H  # 팔꿈치+손목이 키의 10% 이동
    frames += [(moved, box)] * 6
    _, res = run(frames)
    assert res.eliminated


def test_single_joint_spike_ignored():
    kp, box = standing()
    spiked = kp.copy()
    spiked[10, :2] += 0.3 * H  # 손목 하나만 크게 튐 (추정 오류)
    frames = [(kp, box)] * 3 + [(spiked, box)] * 10
    _, res = run(frames)
    assert not res.eliminated


def test_walking_forward_eliminated_by_center():
    kp, box = standing()
    frames = [(kp, box)] * 3
    for i in range(1, 8):
        frames.append((kp + [0, 0.03 * H * i, 0], box + [0, 0.03 * H * i, 0, 0.03 * H * i]))
    _, res = run(frames)
    assert res.eliminated


def test_grace_period_ignores_motion():
    judge = MotionJudge(P)
    for i in range(7):
        kp, box = standing(x0=300 + i * 50)
        res = judge.update(kp, box, i * 60)  # 모두 유예 시간(500ms) 안
    assert res.score is None and not res.eliminated


def test_far_person_same_relative_motion_detected():
    # 멀리 있는 사람(키 100px)도 같은 비율로 움직이면 잡힌다
    kp, box = standing(h=100)
    moved = kp.copy()
    moved[[9, 10], 0] += 0.1 * 100
    _, res = run([(kp, box)] * 3 + [(moved, box)] * 6)
    assert res.eliminated


def test_low_confidence_joints_ignored():
    kp, box = standing()
    moved = kp.copy()
    moved[[9, 10], 0] += 0.2 * H
    moved[[9, 10], 2] = 0.1  # 신뢰도 낮은 관절
    _, res = run([(kp, box)] * 3 + [(moved, box)] * 6)
    assert not res.eliminated
