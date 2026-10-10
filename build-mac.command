#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
trap 'status=$?; if [ "$status" -ne 0 ]; then echo "打包失败，请查看上方错误或 build-macos.log。"; fi; read -r -p "按回车关闭窗口…"; exit "$status"' EXIT
if [ "$(uname -s)" != "Darwin" ]; then
  echo "请在 Mac 上运行此脚本。"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "请先从 https://www.python.org/downloads/macos/ 安装 Python 3.11 或 3.12。"
  exit 1
fi
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python build_macos.py --python .venv/bin/python
open dist/macos
