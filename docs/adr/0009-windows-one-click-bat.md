# ADR-0009: Windows 배포는 exe 대신 play.bat 원클릭 설치·실행으로 한다

- 상태: 제안됨 (Proposed) — ADR-0006(PyInstaller exe)을 대체
- 날짜: 2026-11-25

## 배경

PyInstaller exe는 Windows에서만 빌드할 수 있어 CI 구성이 필요하고, 결과물이 수백 MB~1GB에 이르며
torchvision 네이티브 라이브러리 누락 같은 패키징 문제를 계속 손봐야 한다(Mac 시험 빌드에서 실제로 발생).
제작자는 빌드·유지 비용을 들이지 않고 Windows에서 쉽게 실행되기를 원한다.

## 결정

- 저장소 루트의 `play.bat` 하나로 실행한다. 사용자는 GitHub가 자동 제공하는 저장소 zip
  (`archive/refs/heads/main.zip`)을 받아 압축을 풀고 더블클릭한다. 별도 빌드·릴리스가 없다.
- 첫 실행: Python 3.12/3.11을 `py` 런처로 찾고, 없으면 사용자 동의(`choice`) 후 winget으로 사용자 범위 설치.
  폴더 안 `.venv` 에 CPU용 torch(PyTorch CPU 인덱스, CUDA판보다 훨씬 작음)와 `pip install -e .` 로 의존성을 설치,
  끝나면 `.venv/installed.txt` 표시. 실패하면 `.venv` 를 지워 다음 실행 때 처음부터 다시 한다.
- 실행: `pythonw -m mugunghwa` (콘솔 창 없음). pythonw는 stdout/stderr가 None이라 패키지 `__init__` 에서 devnull로 연결.
  오류는 `error.log`(`paths.user_dir()`). `config.json`·`voices/` 도 같은 폴더.
- bat은 UTF-8 + CRLF(`.gitattributes`), 맨 위에서 `chcp 65001` 로 한글 출력.

## 결과

- 빌드·서명·CI가 필요 없고, 코드가 바뀌면 zip이 자동으로 최신이 된다.
- 첫 실행에 인터넷과 5~15분, 약 1.5GB가 필요하다. 오프라인 PC에서는 첫 설치를 할 수 없다.
- 인터넷에서 받은 bat에는 SmartScreen 경고가 뜰 수 있다(README에 안내).
- 이 bat은 macOS에서 작성했으며 실제 Windows에서 아직 실행 검증하지 않았다.
