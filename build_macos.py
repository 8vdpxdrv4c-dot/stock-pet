"""Build and smoke-test a native macOS app, then create a drag-install DMG."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from build_distribution import find_python, run_logged
from packaging_resources import collect_resources

ROOT = Path(__file__).resolve().parent


def make_icon(env):
    iconset = ROOT / "build/macos/StockPet.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    source = ROOT / "assets/cat/sitting-idle/idle_000.png"
    for size in (16, 32, 128, 256, 512):
        for scale, suffix in ((1, ""), (2, "@2x")):
            pixels = str(size * scale)
            subprocess.run(["sips", "--resampleHeightWidth", pixels, pixels, str(source),
                            "--out", str(iconset / f"icon_{size}x{size}{suffix}.png")],
                           check=True, capture_output=True, env=env)
    subprocess.run(["iconutil", "--convert", "icns", str(iconset), "--output",
                    str(ROOT / "build/macos/StockPet.icns")], check=True, env=env)


def main(argv=None):
    parser = argparse.ArgumentParser(description="在 Mac 上生成 StockPet.app 和 DMG 安装包。")
    parser.add_argument("--python", help="用于构建的 Python，可指定 .venv/bin/python")
    parser.add_argument("--check", action="store_true", help="仅检查环境和资源")
    args = parser.parse_args(argv)
    try:
        if sys.platform != "darwin":
            raise RuntimeError("macOS 应用必须在 Mac 或 macOS CI 上打包，Windows 无法交叉生成 .app。")
        python = find_python(requested=args.python)
        resources = collect_resources(ROOT, ROOT / "build/package-data-macos")
        arch = subprocess.check_output([python, "-c", "import platform; print(platform.machine())"],
                                       text=True).strip()
        if arch not in ("arm64", "x86_64"):
            raise RuntimeError(f"不支持的 Python 架构：{arch}")
        print(f"macOS 构建环境：{python} ({arch})；{len(resources)} 个资源文件", flush=True)
        if args.check:
            return 0
        env = dict(os.environ, PYTHONUTF8="1")
        make_icon(env)
        output = ROOT / "dist/macos" / arch
        run_logged([python, "-m", "PyInstaller", "--noconfirm", "--clean", "--workpath",
                    str(ROOT / "build/macos/pyinstaller"), "--distpath", str(output),
                    "StockPet-macOS.spec"], ROOT / "build-macos.log", env)
        app = output / "StockPet.app"
        executable = app / "Contents/MacOS/StockPet"
        if not executable.is_file():
            raise RuntimeError(f"缺少打包成品：{executable}")
        # Use the Cocoa plugin, as an offscreen-only check would miss native plugin failures.
        smoke_env = dict(env)
        smoke_env.pop("QT_QPA_PLATFORM", None)
        subprocess.run([str(executable), "--smoke-test"], env=smoke_env, check=True, timeout=120)
        print("macOS 成品自检通过", flush=True)
        dmg = output / f"StockPet-macOS-{arch}.dmg"
        with tempfile.TemporaryDirectory(prefix="stockpet-dmg-") as folder:
            stage = Path(folder)
            shutil.copytree(app, stage / app.name, symlinks=True)
            (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
            shutil.copyfile(ROOT / "docs/macOS安装说明.txt", stage / "安装说明.txt")
            subprocess.run(["hdiutil", "create", "-volname", "StockPet", "-srcfolder", str(stage),
                            "-ov", "-format", "UDZO", str(dmg)], env=env, check=True, timeout=300)
        subprocess.run(["hdiutil", "verify", str(dmg)], check=True, env=env, timeout=120)
        print(f"安装包已生成：{dmg}", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
