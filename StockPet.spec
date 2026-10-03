from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
datas = [(str(root / 'config.json'), '.')]
datas.append((str(root / 'assets' / 'cat' / 'eating-idle-v3-sheet.png'), 'assets/cat'))
datas.append((str(root / 'assets' / 'cat' / 'transform-walk-sheet.png'), 'assets/cat'))
datas.append((str(root / 'assets' / 'cat' / 'eye-reference.png'), 'assets/cat'))
for folder in ('sitting-idle', 'eating-idle', 'eating-video-v7', 'sleep-idle', 'walking-idle', 'recycle-walking-video'):
    for file in (root / 'assets' / 'cat' / folder).glob('*.png'):
        datas.append((str(file), 'assets/cat/' + folder))
datas += collect_data_files('jieba')
for file in (root / 'knowledge').rglob('*.md'):
    datas.append((str(file), str(file.parent.relative_to(root))))
if (root / 'knowledge' / 'registry.json').is_file():
    datas.append((str(root / 'knowledge' / 'registry.json'), 'knowledge'))
a = Analysis([str(root / 'main.py')], pathex=[str(root)], datas=datas,
             hiddenimports=collect_submodules('keyring.backends') + collect_submodules('openai'),
             runtime_hooks=[str(root / 'packaging' / 'runtime_log.py')],
             excludes=['tkinter', 'IPython', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StockPet',
          debug=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='StockPet')
