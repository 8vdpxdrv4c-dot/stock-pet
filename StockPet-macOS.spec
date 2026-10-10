import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
sys.path.insert(0, str(root))
from packaging_resources import collect_resources

datas = collect_resources(root, root / 'build/package-data-macos')
datas += collect_data_files('jieba')
a = Analysis([str(root / 'main.py')], pathex=[str(root)], datas=datas,
             hiddenimports=collect_submodules('keyring.backends') + collect_submodules('openai'),
             runtime_hooks=[str(root / 'packaging/runtime_log.py')],
             excludes=['tkinter', 'IPython', 'pytest', 'winreg', 'win_recycle'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StockPet',
          debug=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='StockPet')
app = BUNDLE(coll, name='StockPet.app',
             icon=str(root / 'build/macos/StockPet.icns'),
             bundle_identifier='com.stockpet.desktop',
             info_plist={'CFBundleDisplayName': 'StockPet',
                         'CFBundleShortVersionString': '1.0.0',
                         'CFBundleVersion': '1.0.0',
                         'NSHighResolutionCapable': True,
                         'LSUIElement': True})
