import tempfile
import unittest
from datetime import date
from pathlib import Path
from contextlib import closing
import shutil
import sqlite3
from ProgramFeira import fechamento as f


class FechamentoTests(unittest.TestCase):
    def tearDown(self):
        f.definir({'versao': 0, 'historico': []})

    def test_transicao_contigua_historico_e_fim_de_mes(self):
        novo = f.propor({'versao': 0, 'historico': []}, '2090-11-01', 14, date(2090, 10, 23))
        h = novo['historico']
        self.assertEqual(f.periodo(2090, 9, h), ('2090-09-10', '2090-10-09'))
        self.assertEqual(f.periodo(2090, 10, h), ('2090-10-10', '2090-11-14'))
        self.assertEqual(f.periodo(2090, 11, h), ('2090-11-15', '2090-12-14'))
        self.assertEqual(f.dia_no_mes(2092, 2, [{'vigencia': '2090-01-01', 'dia': 31}]), 29)
        with self.assertRaises(ValueError):
            f.propor(novo, '2090-10-01', 12, date(2090, 10, 23))
        f.definir(novo)
        self.assertEqual(f.primeira_fatura('2090-11-14'), '2090-12-14')
        from ProgramFeira.resumos import periodo_anterior
        self.assertEqual(periodo_anterior('Período de fechamento', '2090-11-15', '2090-12-14'), ('2090-10-10', '2090-11-14'))

    def test_cache_verificado_com_backup_e_sem_regressao_de_versao(self):
        with tempfile.TemporaryDirectory() as pasta:
            banco = Path(pasta) / 'vendas.db'
            shutil.copy2(Path(__file__).resolve().parents[1] / 'ProgramFeira/assets/banco_inicial.db', banco)
            config = {'versao': 1, 'historico': [{'vigencia': '2090-11-01', 'dia': 14}]}
            self.assertTrue(f.guardar(banco, config, 'https://teste.supabase.co', 'usuario-ficticio'))
            self.assertEqual(f.carregar(banco), config)
            self.assertFalse(f.guardar(banco, config, 'https://teste.supabase.co', 'usuario-ficticio'))
            with self.assertRaises(ValueError):
                f.guardar(banco, {'versao': 0, 'historico': []}, 'https://teste.supabase.co', 'usuario-ficticio')
            with self.assertRaises(ValueError):
                f.guardar(banco, config, 'https://outro.supabase.co', 'outro-usuario')
            self.assertTrue(list((Path(pasta) / 'backups').glob('*.db')))
            with closing(sqlite3.connect(banco)) as c:
                self.assertEqual(c.execute('select count(*) from vendas').fetchone()[0], 0)
