# Build both the portable executable and the fast-starting installed version.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parents[1]
stage = root / 'build' / 'windows' / 'stage'
a = Analysis(
    [str(root / 'packaging' / 'windows' / 'launcher.py')],
    pathex=[str(root / 'backend')],
    binaries=[(str(stage / 'node.exe'), '.')],
    datas=[(str(stage / 'frontend'), 'frontend'), (str(stage / 'licenses'), 'licenses')]
          + collect_data_files('docx'),
    hiddenimports=['uvicorn.logging', 'uvicorn.loops.asyncio',
                   'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan.on',
                   'sqlalchemy.dialects.sqlite'],
    excludes=['pytest', 'IPython', 'matplotlib', 'numpy', 'pandas'],
    noarchive=False,
)
pyz = PYZ(a.pure)
portable = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='DisagreementProtocol-Portable', console=False, upx=False,
    version=str(root / 'packaging' / 'windows' / 'version.txt'))
installed = EXE(pyz, a.scripts, [], exclude_binaries=True,
    name='DisagreementProtocol', console=False, upx=False,
    version=str(root / 'packaging' / 'windows' / 'version.txt'))
coll = COLLECT(installed, a.binaries, a.datas,
    name='DisagreementProtocol', upx=False)
