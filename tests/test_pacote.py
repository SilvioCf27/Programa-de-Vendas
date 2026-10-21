import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PacoteTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'), 'Sem sessão gráfica')
    def test_verificacao_isola_banco_e_recursos_fora_do_diretorio(self):
        with tempfile.TemporaryDirectory() as pasta:
            relatorio = Path(pasta) / 'resultado.json'
            pessoal = Path(pasta) / 'dados-pessoais'
            pessoal.mkdir()
            banco = pessoal / 'vendas.db'
            banco.write_bytes(b'nao tocar neste arquivo')
            env = dict(os.environ, PROGRAMFEIRA_DATA_DIR=str(pessoal))
            retorno = subprocess.run([sys.executable, str(ROOT / 'executar.py'), '--verificar-pacote', str(relatorio)], cwd=pasta, env=env, capture_output=True, text=True, timeout=60)
            resultado = json.loads(relatorio.read_text(encoding='utf-8'))
            self.assertEqual(retorno.returncode, 0, resultado)
            self.assertTrue(resultado['sucesso'])
            self.assertEqual(resultado['registros_iniciais'], 0)
            self.assertEqual(resultado['fontes'], 4)
            self.assertTrue(resultado['excel'])
            self.assertTrue(resultado['backup'])
            self.assertEqual(banco.read_bytes(), b'nao tocar neste arquivo')
