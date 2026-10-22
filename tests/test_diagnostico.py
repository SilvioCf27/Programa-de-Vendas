import json
from pathlib import Path
import tempfile
import unittest
from ProgramFeira.diagnostico import registrar


class DiagnosticoTests(unittest.TestCase):
    def test_log_contem_tipo_e_pilha_sem_mensagem_ou_variaveis(self):
        with tempfile.TemporaryDirectory() as pasta:
            try:
                raise ValueError('senha-secreta token-secreto R$ 123,45')
            except ValueError as erro:
                self.assertTrue(registrar(erro, pasta))
            texto = (Path(pasta) / 'logs/erros.jsonl').read_text(encoding='utf-8')
            self.assertNotIn('senha-secreta', texto)
            self.assertNotIn('token-secreto', texto)
            self.assertNotIn('123,45', texto)
            dados = json.loads(texto)
            self.assertEqual(dados['tipo'], 'ValueError')
            self.assertTrue(dados['pilha'])

    def test_falha_de_log_nao_interrompe_operacao(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'arquivo'
            caminho.write_text('nao e pasta')
            self.assertFalse(registrar(ValueError('falha'), caminho))
