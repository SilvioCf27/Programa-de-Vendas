import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InicializacaoTests(unittest.TestCase):
    def test_importacoes_ao_executar_main_isolado_fora_da_raiz(self):
        main = ROOT / 'ProgramFeira/main.py'
        # Executa o cabeçalho real em processo isolado, sem criar banco nem janela.
        codigo = """
from pathlib import Path
p = Path(__import__('sys').argv[1])
s = p.read_text(encoding='utf-8').split('criar_tabela()', 1)[0]
exec(compile(s, str(p), 'exec'), {'__name__': '__main__', '__package__': None, '__file__': str(p)})
"""
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run([sys.executable, '-I', '-c', codigo, str(main)], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_configuracao_vscode_executa_modulo(self):
        config = json.loads((ROOT / '.vscode/launch.json').read_text(encoding='utf-8'))['configurations'][0]
        self.assertEqual(config['module'], 'ProgramFeira.main')
        self.assertEqual(config['cwd'], '${workspaceFolder}')
