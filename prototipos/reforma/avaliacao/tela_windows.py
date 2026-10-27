"""Ajusta somente o monitor da VM CI e permite restauração. Nunca usado pelo app."""

import argparse
import base64
import ctypes as C
from ctypes import wintypes as T
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument("--saida", required=True)
p.add_argument("--restaurar", action="store_true")
args = p.parse_args()
if sys.platform != "win32":
    raise SystemExit("Este ensaio requer a VM Windows")
u = C.windll.user32
u.EnumDisplaySettingsW.argtypes = [T.LPCWSTR, T.DWORD, C.c_void_p]
u.EnumDisplaySettingsW.restype = T.BOOL
u.ChangeDisplaySettingsExW.argtypes = [
    T.LPCWSTR,
    C.c_void_p,
    C.c_void_p,
    T.DWORD,
    C.c_void_p,
]
u.ChangeDisplaySettingsExW.restype = T.LONG


class Modo(C.Structure):
    _fields_ = [
        ("device", T.WCHAR * 32),
        ("spec", T.WORD),
        ("driver", T.WORD),
        ("size", T.WORD),
        ("extra", T.WORD),
        ("fields", T.DWORD),
        ("union", C.c_byte * 16),
        ("color", C.c_short),
        ("duplex", C.c_short),
        ("yresolution", C.c_short),
        ("ttoption", C.c_short),
        ("collate", C.c_short),
        ("form", T.WCHAR * 32),
        ("logpixels", T.WORD),
        ("bits", T.DWORD),
        ("width", T.DWORD),
        ("height", T.DWORD),
        ("flags", T.DWORD),
        ("frequency", T.DWORD),
        ("icmmethod", T.DWORD),
        ("icmintent", T.DWORD),
        ("media", T.DWORD),
        ("dither", T.DWORD),
        ("reserved1", T.DWORD),
        ("reserved2", T.DWORD),
        ("panningwidth", T.DWORD),
        ("panningheight", T.DWORD),
    ]


assert C.sizeof(Modo) == 220
path = Path(args.saida)
if args.restaurar:
    d = json.loads(path.read_text(encoding="utf-8"))
    m = Modo.from_buffer_copy(base64.b64decode(d["original"]))
    d["restauracao"] = u.ChangeDisplaySettingsExW(None, C.byref(m), None, 0, None)
    path.write_text(json.dumps(d, indent=2), encoding="utf-8")
    raise SystemExit(0)
m = Modo()
m.size = C.sizeof(Modo)
if not u.EnumDisplaySettingsW(None, 0xFFFFFFFF, C.byref(m)):
    raise RuntimeError("Não foi possível ler o modo da VM")
original = base64.b64encode(bytes(m)).decode()
antes = [m.width, m.height]
m.width = 1920
m.height = 1080
m.fields |= 0x180000
check = u.ChangeDisplaySettingsExW(None, C.byref(m), None, 2, None)
status = (
    u.ChangeDisplaySettingsExW(None, C.byref(m), None, 0, None) if check == 0 else check
)
atual = Modo()
atual.size = C.sizeof(Modo)
u.EnumDisplaySettingsW(None, 0xFFFFFFFF, C.byref(atual))
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(
        dict(
            antes=antes,
            depois=[atual.width, atual.height],
            teste=check,
            aplicacao=status,
            original=original,
            observacao="VM efêmera do Actions; configuração do monitor do usuário não é acessada.",
        ),
        indent=2,
    ),
    encoding="utf-8",
)
print("Resolução da VM:", antes, "->", [atual.width, atual.height])
