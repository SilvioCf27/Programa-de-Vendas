"""Dados inventados para os testes. Não representam vendas de uma pessoa."""
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
VENDAS = (
    ('2025-01-03', 10, 20, 30),
    ('2025-10-10', 100, 0, 0),
    ('2025-12-31', 0, 25.50, 0),
    ('2026-01-02', 40, 10, 0),
    ('2026-01-04', 20, 15, 15),
    ('2026-03-13', 0, 0, 125.75),
    ('2026-10-16', 80, 30, 40),
    ('2026-12-25', 0, 0, 0),
    ('2027-01-01', 0, 0, 0),
)


def criar_banco(destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'ProgramFeira/assets/banco_inicial.db', destino)
    with closing(sqlite3.connect(destino)) as c, c:
        c.executemany('INSERT INTO vendas(data,dinheiro,pix,cartao) VALUES (?,?,?,?)', VENDAS)
    return destino
