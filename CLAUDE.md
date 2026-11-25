# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

웹캠으로 여러 사람을 인식하는 Windows용 "무궁화 꽃이 피었습니다" 게임 (오징어 게임 분위기, 비상업).
술래가 뒤돌아보는 RED 구간에 움직인 참가자를 총소리와 함께 탈락시키고, 모니터 앞 물리 버튼(키 입력)을 누르면 승리.
설계 결정은 `docs/adr/` 에 있다 — 동작을 바꾸기 전에 해당 ADR을 먼저 확인할 것.

## 명령

```bash
/opt/homebrew/bin/python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'   # 설치 (Python 3.11~3.12)
.venv/bin/python -m mugunghwa                                # 실행 (카메라 권한 필요)
.venv/bin/pytest -q                                          # 전체 테스트
.venv/bin/pytest tests/test_judge.py::test_arm_move_eliminated   # 단일 테스트
.venv/bin/python tools/make_sounds.py                        # 임시 사운드 재생성 (구호 TTS는 macOS 전용)
```

설정은 실행 폴더의 `config.json` (예시: `config.example.json`, 필드는 `src/mugunghwa/config.py` 의 `GameConfig`). 게임 안 설정 화면(제목에서 S)이 카메라·목소리·난이도·제한 시간을 바꾸고 이 파일에 저장한다(ADR-0008).

키는 `keys.py` 로 스캔코드(물리 위치) 기준 판별 — 한글 자판에서도 동작. 게임 중 키: SPACE 메뉴 진행/확정, 게임 중(GREEN/RED)에는 SPACE·Enter(`win_key`)가 승리 버튼, 1/2/3/4 난이도(쉬움/보통/어려움/지옥), `+`/`-` 임계값 조정, D 디버그, F11 전체화면.

## 아키텍처

세 스레드가 `LatestSlot`(큐가 아닌 "최신 값 하나" 덮어쓰기 슬롯, `model.py`)으로 연결된다:
`Camera`(camera.py, 메인 스레드에서 열고(macOS 권한 요청 조건) 캡처는 스레드, 좌우반전) → `DetectorThread`(detector.py, YOLO11n-pose + ByteTrack → `Detection`) → pygame 메인 루프(main.py).

- 메인 루프는 **새 Detection이 들어온 경우에만** `Game.on_detection()` 을 호출한다. 판정 속도는 인식 fps에 묶이고, 화면은 60fps로 따로 돈다. 화면에는 Detection의 프레임을 그려 박스와 영상이 어긋나지 않게 한다.
- `game.py` 의 `Game` 은 상태 머신(TITLE→LOBBY→COUNTDOWN→GREEN⇄RED→RESULT)이며 pygame/카메라에 의존하지 않는다. 시간(`now`)을 인자로 받고, 부수효과는 `Event` 목록(`pop_events()`)으로 내보내며 main.py가 이를 사운드/연출로 바꾼다. GREEN 길이는 구호 오디오 길이(`chant_length(speed)`)로 정해진다.
- `players.py`: LOBBY에서 보인 track ID만 참가자로 등록(왼쪽부터 번호). 게임 중 새 ID는 무시하되, 참가자 ID가 끊기면 마지막 박스와 IoU/중심거리로 "모르는 ID"를 재연결.
- `judge.py`(ADR-0004): 참가자별 `MotionJudge`. RED 시작 후 유예 → 기준 자세(평균) → 관절별 이동량/키 중 **두 번째로 큰 값** + 몸 중심 이동량, 연속 N프레임 초과 시 탈락. 순수 numpy라 `tests/` 에서 합성 키포인트로 검증한다.
- 승리 버튼은 누른 사람을 알 수 없으므로 "보이는 생존자 중 bbox가 가장 큰 사람"을 승자로 본다.
- 난이도 = 판정 기준(`DIFFICULTIES[d]["judge"]` → `JudgeParams`) + 술래 규칙(`["rules"]` → `Rules`: 구호 끊기·재확인·가속·RED 범위). 게임 로직은 `cfg.rules()` 를 매번 읽는다.
- `render.py` 는 상태를 읽기만 한다. 색·도장·모서리 괄호 등 디자인 토큰은 파일 상단 주석 참고. 구호 가사 진행은 `audio.chant_timing()`(목소리별 말 시작·끝 + 선택적 글자 비중)으로 소리와 맞춘다. 술래 인형은 `doll.make_doll()` 이 고른다: `assets/images/doll/` 스프라이트 3장(back/front/front_red)이 있으면 `ImageDoll`(옅은 알파 제거·여백 자르기 후 전체를 가로로 눌러 돌아서는 연출), 없으면 코드로 그린 `Doll`. 방향은 `Doll.facing(state, since, now)`. 한글 폰트는 `assets/fonts/` → 시스템 폰트(맑은 고딕/Apple SD 고딕) 순으로 찾는다.
- 목소리: `assets/voices/<이름>/` + 실행 폴더 `voices/<이름>/` 의 chant.wav (`audio.voice_dirs`). 게임은 GREEN마다 `prepare_chant(speed)` 를 불러 목소리(무작위 포함)와 길이를 정한다. `voices/` 는 지인 녹음이라 git 제외. 기계음 `assets/voices/*/chant.*` 도 macOS 음성 약관 때문에 git 제외(ADR-0007) — 새로 받은 저장소에는 목소리가 없을 수 있다.
- 에셋 접근은 반드시 `paths.asset()` 사용 (PyInstaller `sys._MEIPASS` 대응). 모델은 `assets/models/yolo11n-pose.pt`.

## 주의

- 개인정보: 카메라 영상은 메모리에서만 처리하고 저장·전송하지 않는다. `mugunghwa/__init__.py` 가 ultralytics import 전에 `YOLO_OFFLINE=1` 을 설정해 익명 통계 전송·온라인 점검을 끈다 — ultralytics를 이 패키지 밖에서 먼저 import 하지 말 것. 모델 파일은 `assets/models/` 에 있어야 한다(오프라인이라 자동 다운로드 안 됨).

- Windows exe는 Windows에서만 빌드 가능 (PyInstaller `--onedir`, ADR-0006). 카메라 백엔드는 Windows `CAP_DSHOW`, macOS `CAP_AVFOUNDATION`.
- 드라마의 인형·음성·음악·로고는 넣지 않는다 (ADR-0007). 에셋 추가 시 `assets/CREDITS.md` 갱신.
- 판정 임계값·시간 값은 코드에 박지 말고 `GameConfig`/`DIFFICULTIES` 에 둔다.
- 승인된 ADR을 뒤집을 때는 새 ADR을 추가하고 `docs/adr/README.md` 표를 갱신한다.
