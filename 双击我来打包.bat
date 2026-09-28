@echo off
REM 双击这个来打包，即使 build.bat 崩溃窗口也保留
cd /d "%~dp0"
cmd /k build.bat
