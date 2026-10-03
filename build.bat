@echo off
chcp 65001 >nul
cd /d "%~dp0"
python build_distribution.py
if errorlevel 1 (
    echo 打包失败，请检查当前 Python 环境及 Inno Setup 安装。
    pause
    exit /b 1
)
echo 安装包已生成：dist\StockPet-Setup-1.0.0.exe
pause
