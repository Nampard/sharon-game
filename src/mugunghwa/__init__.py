"""무궁화 꽃이 피었습니다 — 캠 챌린지.

개인정보: 카메라 영상은 메모리에서만 처리하고 저장·전송하지 않는다.
Ultralytics 라이브러리의 익명 사용 통계 전송과 온라인 점검(자동 설치 등)도 끈다
— 반드시 ultralytics 를 import 하기 전에 설정해야 하므로 패키지 진입점에 둔다.
"""
import os
import sys

os.environ.setdefault("YOLO_OFFLINE", "1")

# Windows 원클릭 실행(play.bat)은 콘솔 없는 pythonw 로 켠다. 이때 sys.stdout/stderr 가 None 이라
# 무언가 출력하려는 라이브러리가 멈출 수 있으므로 버리는 곳으로 연결해 둔다.
for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, "w", encoding="utf-8"))
