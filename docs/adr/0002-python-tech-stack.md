# ADR-0002: Python + OpenCV + pygame 스택을 쓴다

- 상태: 제안됨 (Proposed)
- 날짜: 2026-11-25

## 배경

요구사항: Windows에서 실행, 웹캠으로 여러 사람을 인식, "멈춤" 구간에 움직인 사람을 총소리와 함께 탈락.
개발 머신은 macOS이고 배포 대상은 Windows다.

검토한 후보:

| 후보 | 장점 | 단점 |
|---|---|---|
| **Python (OpenCV + Ultralytics + pygame)** | 비전 모델 생태계가 가장 풍부, 프로토타입 속도 빠름, macOS/Windows 동일 코드 | exe 용량이 큼(수백 MB), Python 런타임 성능 한계 |
| Unity (C#) + Barracuda/Sentis | 연출·사운드·UI가 강력 | 멀티 인물 포즈 모델 연동이 번거로움, 학습 곡선 |
| C# WinForms/WPF + OpenCvSharp + ONNX Runtime | 작은 네이티브 exe | macOS에서 개발·실행 불가, 비전 코드 작성량 많음 |
| 웹(브라우저) + MediaPipe JS | 설치 없음 | "Windows 버전" 요구와 어긋남, 다인원 성능 불확실 |

## 결정

- 언어: **Python 3.11**
- 카메라 입력/영상 처리: **OpenCV (`opencv-python`)**
- 사람 인식·추적: **Ultralytics YOLO pose** (상세는 ADR-0003)
- 화면·사운드·게임 루프: **pygame** (상세는 ADR-0005)
- 의존성 관리: `pyproject.toml` + `uv` (없으면 `pip`/venv)

## 결과

- macOS에서 개발하고 같은 코드를 Windows에서 실행할 수 있다. 단, 카메라 백엔드(Windows는 `CAP_DSHOW`/`CAP_MSMF`)는 플랫폼별로 분기해야 한다.
- 배포 파일이 크다(PyTorch 포함 시 수백 MB). ADR-0006에서 ONNX 변환으로 줄이는 방안을 다룬다.
- 성능이 부족하면 인식 부분만 ONNX Runtime/DirectML로 교체할 수 있도록 인식 모듈을 인터페이스 뒤에 둔다.
