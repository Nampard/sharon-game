# 에셋 출처 (ADR-0007)

| 파일 | 출처 | 라이선스 |
|---|---|---|
| voices/기계음/chant.wav | macOS `say` (Yuna 음성)를 속도·음높이·울림 가공 — `tools/make_sounds.py` | **저장소·배포본에 포함하지 않음** (Apple 약관상 개인적 용도만 안전). 각자 `tools/make_sounds.py` 로 생성 |
| sounds/gunshot.wav, beep.wav, turn.wav | `tools/make_sounds.py` 로 numpy 합성 | 프로젝트 자체 제작 |
| models/yolo11n-pose.pt | Ultralytics 공식 릴리스 | AGPL-3.0 |
| voices/소녀 메가폰/chant.wav | 제작자 본인 녹음을 `tools/voicefx`(NAudio.Core, MIT)로 음높이·메가폰 변조, 2026-11-25 | 제작자 본인 목소리, 본인 의사로 공개 |
| images/doll/doll_back.png, doll_front.png, doll_front_red.png | Codex(ChatGPT 계정) 이미지 생성, 2026-11-25. 프롬프트에 "오징어 게임 인형과 닮지 않은 색동 한복 인형"으로 명시 | OpenAI 이용약관상 생성물은 사용자 소유 |
| 술래 인형(대체용) | `src/mugunghwa/doll.py` 코드로 직접 그림 — 이미지가 없을 때 사용 | 프로젝트 자체 제작 |
