@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYW=C:\Users\yaoja\.workbuddy\binaries\python\envs\stock-pet\Scripts\pythonw.exe"
set "PY=C:\Users\yaoja\.workbuddy\binaries\python\envs\stock-pet\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] 找不到项目虚拟环境: %PY%
  echo 请先执行: python -m pip install -r requirements.txt
  pause
  exit /b 1
)

if exist "%PYW%" (
  start "" "%PYW%" main.py
) else (
  start "" "%PY%" main.py
)
exit /b 0
