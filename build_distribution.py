"""Build a standalone EXE, or optionally an application folder and installer."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPENDENCY_PROBE = "import PyQt5.QtWidgets, openai, jieba, keyring, PyInstaller"


def find_python(root=ROOT, requested=None):
    if requested:
        candidates = [Path(requested)]
    else:
        candidates = [root / ".venv/Scripts/python.exe", root / "venv/Scripts/python.exe",
                      root / ".venv/bin/python", root / "venv/bin/python",
                      Path.home() / ".workbuddy/binaries/python/envs/stock-pet/Scripts/python.exe",
                      Path(sys.executable)]
        if os.environ.get("STOCKPET_BUILD_PYTHON"):
            candidates.insert(0, Path(os.environ["STOCKPET_BUILD_PYTHON"]))
    for candidate in dict.fromkeys(candidates):
        if not candidate.is_file():
            continue
        try:
            result = subprocess.run([str(candidate), "-c", DEPENDENCY_PROBE], capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return str(candidate)
    raise RuntimeError("找不到依赖齐全的 Python。请创建 .venv 并安装 requirements.txt，"
                       "或通过 --python 指定已安装项目依赖的 python.exe。")


def find_compiler():
    compiler = shutil.which("ISCC")
    if compiler:
        return compiler
    for variable, suffix in (("LOCALAPPDATA", "Programs/Inno Setup 6"),
                             ("ProgramFiles(x86)", "Inno Setup 6"), ("ProgramFiles", "Inno Setup 6")):
        if os.environ.get(variable):
            candidate = Path(os.environ[variable]) / suffix / "ISCC.exe"
            if candidate.is_file():
                return str(candidate)
    return None


def run_logged(command, logfile, env):
    with logfile.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in process.stdout:
            log.write(line)
            print(line, end="", flush=True)
        if process.wait():
            raise RuntimeError(f"打包失败，详细日志：{logfile}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="默认生成 dist/StockPet.exe 单文件程序。")
    parser.add_argument("--onedir", action="store_true", help="生成程序目录，启动更快")
    parser.add_argument("--installer", action="store_true", help="生成程序目录和 Inno Setup 安装包")
    parser.add_argument("--python", help="指定用于打包的 Python 路径")
    parser.add_argument("--check", action="store_true", help="只检查依赖和打包资源")
    args = parser.parse_args(argv)
    try:
        python = find_python(requested=args.python)
        from packaging_resources import collect_resources
        resources = collect_resources(ROOT, ROOT / "build/package-data")
        print(f"打包环境：{python}", flush=True)
        print(f"资源检查通过：{len(resources)} 个文件", flush=True)
        compiler = find_compiler() if args.installer else None
        if args.installer and not compiler:
            raise RuntimeError("构建安装包需要 Inno Setup 6。直接运行 build.bat 可生成单文件 EXE，无需 Inno Setup。")
        if args.check:
            return 0
        env = dict(os.environ, PYTHONUTF8="1",
                   STOCKPET_BUILD_MODE="onedir" if args.onedir or args.installer else "onefile")
        run_logged([python, "-m", "PyInstaller", "--noconfirm", "--workpath",
                    str(ROOT / "build" / env["STOCKPET_BUILD_MODE"]), "StockPet.spec"],
                   ROOT / "build-exe.log", env)
        executable = ROOT / "dist" / ("StockPet/StockPet.exe" if env["STOCKPET_BUILD_MODE"] == "onedir" else "StockPet.exe")
        if not executable.is_file():
            raise RuntimeError(f"打包未生成预期文件：{executable}")
        print(f"EXE 已生成：{executable}", flush=True)
        if compiler:
            run_logged([compiler, "installer.iss"], ROOT / "build-installer.log", env)
            print(f"安装包已生成：{ROOT / 'dist/StockPet-Setup-1.0.0.exe'}", flush=True)
        return 0
    except (OSError, RuntimeError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
