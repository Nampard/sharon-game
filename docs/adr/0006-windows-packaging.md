# ADR-0006: Windows 배포는 PyInstaller 폴더형 빌드를 Windows에서 만든다

- 상태: 제안됨 (Proposed)
- 날짜: 2026-11-25

## 배경

최종 사용자는 Python 없이 더블클릭으로 실행할 수 있어야 한다.
개발은 macOS에서 하지만 **PyInstaller는 교차 컴파일을 지원하지 않는다** (Windows exe는 Windows에서만 빌드 가능).

## 결정

- 도구: **PyInstaller**, `--onedir` (폴더형). `--onefile`은 실행할 때마다 수백 MB를 임시 폴더에 풀어 시작이 느려서 쓰지 않는다.
- 빌드 환경: **GitHub Actions `windows-latest` 러너** 또는 Windows PC. macOS에서는 개발·테스트만 한다.
- 모델 파일(`.pt`/`.onnx`), 사운드, 폰트는 `assets/` 에 두고 spec 파일의 `datas` 로 포함한다. 코드에서는 `sys._MEIPASS` 를 고려한 경로 헬퍼로 접근한다.
- 용량 축소(2단계): YOLO 모델을 ONNX로 내보내고 **ONNX Runtime**(필요 시 DirectML로 GPU 가속)으로 추론하면 PyTorch를 빼서 배포 크기를 크게 줄일 수 있다. 1단계에서는 PyTorch(CPU) 그대로 간다.
- 카메라: Windows에서는 `cv2.VideoCapture(index, cv2.CAP_DSHOW)` 를 기본으로 쓴다 (MSMF는 일부 웹캠에서 여는 데 수 초 걸림).

## 결과

- macOS에서는 Windows 빌드를 바로 확인할 수 없다 → CI에서 빌드 산출물(zip)을 받아 Windows에서 실행 테스트해야 한다.
- 서명되지 않은 exe는 Windows SmartScreen 경고가 뜬다. 공개 배포 시 코드 서명을 별도 결정한다.
- 백신이 PyInstaller exe를 오탐하는 경우가 있다.
