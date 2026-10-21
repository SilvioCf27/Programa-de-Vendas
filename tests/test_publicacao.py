"""Protege o pacote público contra inclusão acidental de dados de uso."""
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicacaoTests(unittest.TestCase):
    def test_unico_banco_distribuido_esta_vazio(self):
        bancos = list((ROOT / 'ProgramFeira').rglob('*.db'))
        esperado = ROOT / 'ProgramFeira/assets/banco_inicial.db'
        self.assertEqual(bancos, [esperado])
        with closing(sqlite3.connect(esperado.resolve().as_uri() + '?mode=ro', uri=True)) as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
            self.assertEqual(c.execute('SELECT count(*) FROM vendas').fetchone()[0], 0)
            tabelas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tabelas, {'vendas', 'sqlite_sequence'})
            self.assertEqual(c.execute('PRAGMA freelist_count').fetchone()[0], 0)

    def test_nao_distribui_planilhas_backups_ou_relatorios(self):
        for pasta in ('dados-originais', 'backups', 'relatorios'):
            arquivos = [p for p in (ROOT / pasta).rglob('*') if p.is_file()] if (ROOT / pasta).exists() else []
            self.assertEqual(arquivos, [])
        self.assertEqual(list((ROOT / 'ProgramFeira').rglob('*.xlsx')), [])
        self.assertEqual(list((ROOT / 'ProgramFeira').rglob('*.csv')), [])
