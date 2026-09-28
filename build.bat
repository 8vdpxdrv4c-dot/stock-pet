@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title StockPet 打包脚本

echo ============================================
echo   股票纪律桌面宠物 - Windows 一键打包
echo ============================================
echo.

echo [检查] Python 环境...
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没找到 Python。请到 https://www.python.org/downloads/ 安装 Python 3.9+，安装时勾选 Add Python to PATH
    pause
    exit /b 1
)
python -c "import sys; assert sys.version_info>=(3,9), '需要 3.9+'"
if errorlevel 1 (
    echo [错误] Python 版本不对或 Windows 商店占位符。请到 python.org 装正式版。
    pause
    exit /b 1
)

echo [1/5] 安装依赖...
python -m pip install --upgrade pip
if errorlevel 1 ( echo [失败] & pause & exit /b 1 )
python -m pip install -r requirements.txt
if errorlevel 1 ( echo [失败] 依赖安装失败 & pause & exit /b 1 )

echo [2/5] PyInstaller 打包（3-10 分钟）...
python -m PyInstaller --noconfirm --windowed --onefile --name StockPet --collect-all akshare --collect-submodules openai --add-data "config.json;." --add-data "assets;assets" main.py
if errorlevel 1 (
    echo [失败] 打包出错，把上面日志截图发我
    pause
    exit /b 1
)

echo [3/5] 复制配置...
if not exist dist\config.json copy /Y config.json dist\config.json >nul
if not exist dist\assets xcopy /E /I /Y assets dist\assets >nul

echo [5/5] 完成！exe 在 dist\StockPet.exe
pause >nul
exit /b 0
