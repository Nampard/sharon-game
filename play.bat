@echo off
chcp 65001 >nul
rem 무궁화 꽃이 피었습니다 - Windows 원클릭 실행
rem 처음 실행하면 게임 폴더 안 .venv 에 필요한 프로그램을 설치하고, 다음부터는 바로 게임을 켭니다.
setlocal
cd /d "%~dp0"
title 무궁화 꽃이 피었습니다

if exist ".venv\installed.txt" goto run

echo.
echo  처음 실행입니다. 게임에 필요한 프로그램을 이 폴더 안에 설치합니다.
echo  인터넷 속도에 따라 5~15분 걸리고, 약 1.5GB를 씁니다. 창을 닫지 마세요.
echo.

call :find_python
if defined PY goto have_python

echo  Python 3.12 가 설치되어 있지 않습니다.
where winget >nul 2>nul
if errorlevel 1 goto no_winget
choice /m " winget 으로 Python 3.12 를 지금 설치할까요"
if errorlevel 2 goto cancelled
winget install -e --id Python.Python.3.12 --scope user
call :find_python
if defined PY goto have_python
echo  Python 설치를 확인하지 못했습니다. 이 창을 닫고 play.bat 을 다시 실행해 주세요.
pause
exit /b 1

:have_python
echo  사용할 Python: %PY%
"%PY%" -m venv .venv || goto fail
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto fail
rem 그래픽카드용(CUDA) 대신 CPU용 torch 를 받아 용량을 줄인다
".venv\Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu || goto fail
".venv\Scripts\python.exe" -m pip install -e . || goto fail
echo ok> ".venv\installed.txt"
echo.
echo  설치가 끝났습니다. 게임을 시작합니다.

:run
rem pythonw 는 검은 콘솔 창 없이 게임 창만 띄운다. 오류가 나면 이 폴더의 error.log 를 확인한다.
start "" ".venv\Scripts\pythonw.exe" -m mugunghwa
exit /b 0

:find_python
set "PY="
for %%V in (3.12 3.11) do call :try_py %%V
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b 0

:try_py
if defined PY exit /b 0
py -%1 -c "import sys" >nul 2>nul
if errorlevel 1 exit /b 0
for /f "delims=" %%P in ('py -%1 -c "import sys; print(sys.executable)"') do set "PY=%%P"
exit /b 0

:no_winget
echo  https://www.python.org/downloads/ 에서 Python 3.12 를 설치한 뒤 play.bat 을 다시 실행해 주세요.
pause
exit /b 1

:cancelled
echo  설치를 취소했습니다.
pause
exit /b 1

:fail
echo.
echo  설치 중 오류가 났습니다. 인터넷 연결을 확인하고 play.bat 을 다시 실행해 주세요.
if exist ".venv" rmdir /s /q ".venv"
pause
exit /b 1
