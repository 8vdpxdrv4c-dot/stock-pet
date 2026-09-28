@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0
title 环境诊断
echo ============================================
echo   StockPet 环境诊断
echo ============================================
echo.
echo [1] 当前路径: %CD%
echo [2] python 在哪里: & where python
echo [3] python 版本: & python --version
echo [4] pip 版本: & python -m pip --version
echo [5] 关键库:
python -c "import PyQt5; print('  PyQt5 OK')" 2>&1
python -c "import akshare; print('  akshare', akshare.__version__)" 2>&1
python -c "import openai; print('  openai', openai.__version__)" 2>&1
python -c "import keyring; print('  keyring', keyring.get_keyring().__class__.__name__)" 2>&1
python -c "import PyInstaller; print('  PyInstaller', PyInstaller.__version__)" 2>&1
echo [6] 网络: & python -c "import requests; r=requests.get('https://api.deepseek.com', timeout=10); print('  DeepSeek HTTP', r.status_code)" 2>&1
echo ============================================
echo 诊断结束，截图发我
echo ============================================
pause
