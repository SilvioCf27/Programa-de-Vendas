# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

raiz = Path(SPECPATH)
a = Analysis(
    [str(raiz / 'executar.py')],
    pathex=[str(raiz)],
    binaries=[],
    datas=[
        (str(raiz / 'ProgramFeira/assets'), 'ProgramFeira/assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'IPython', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='GestaoDaFeira', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    icon=str(raiz / 'ProgramFeira/assets/gestao-da-feira.ico') if sys.platform == 'win32' else None,
    version=str(raiz / 'tools/versao_windows.txt') if sys.platform == 'win32' else None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='GestaoDaFeira')
