"""Fontes privadas da aplicação; não instala nem modifica fontes do computador."""
from pathlib import Path
import sys

PASTA_FONTES = Path(__file__).resolve().parents[1] / 'assets/fonts'
_registradas = False


def registrar_fontes():
    global _registradas
    if _registradas:
        return
    _registradas = True
    if sys.platform == 'win32':
        import ctypes
        adicionar = ctypes.WinDLL('gdi32').AddFontResourceExW
        adicionar.argtypes = (ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p)
        adicionar.restype = ctypes.c_int
        for arquivo in PASTA_FONTES.rglob('*.ttf'):
            adicionar(str(arquivo), 0x10, None)  # FR_PRIVATE: apenas este processo.
    # Em outras plataformas o tema usa fontes instaladas de aparência equivalente.
