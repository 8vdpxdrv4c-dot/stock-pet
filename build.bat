@echo off
chcp 65001 >nul
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    py -3 build_distribution.py %*
) else (
    python build_distribution.py %*
)
if errorlevel 1 (
    echo 打包失败，请查看上方错误和 build-exe.log。
    pause
    exit /b 1
)
echo 打包完成。默认程序：dist\StockPet.exe
pause
