@echo off
chcp 65001 >nul
cd /d %~dp0
echo 股票纪律桌面宠物 - 环境自检
echo ==============================
python self_check.py
pause
