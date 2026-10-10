import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
sys.path.insert(0, str(root))
from packaging_resources import collect_resources

datas = collect_resources(root, root / 'build/package-data')
datas += collect_data_files('jieba')
a = Analysis([str(root / 'main.py')], pathex=[str(root)], datas=datas,
             hiddenimports=collect_submodules('keyring.backends') + collect_submodules('openai'),
             runtime_hooks=[str(root / 'packaging/runtime_log.py')],
             excludes=['tkinter', 'IPython', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
if os.environ.get('STOCKPET_BUILD_MODE', 'onefile') == 'onedir':
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StockPet',
              debug=False, strip=False, upx=False, console=False)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='StockPet')
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='StockPet',
              debug=False, strip=False, upx=False, console=False)
