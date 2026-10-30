"""Diagnóstico do preparador sem rede e somente com arquivos fictícios."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import preparar_validacao as cli
from reforma_desktop import perfil_validacao as perfil
from reforma_desktop.ambiente import MARCADOR, CONTEUDO


class DiagnosticoPreparadorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.raiz = Path(temp.name)
        self.origem = self.raiz / 'estudo'
        self.origem.mkdir()
        (self.origem / MARCADOR).write_text(CONTEUDO, encoding='utf-8')
        (self.origem / 'vendas.db').write_bytes(b'banco ficticio intocado')
        self.destino = self.raiz / 'destino'
        self.args = ['preparar_validacao.py', '--origem-estudo', str(self.origem),
                     '--destino', str(self.destino), '--url-projeto-teste',
                     'https://projeto-ficticio.supabase.co', '--chave-publica',
                     'credencial-ficticia-nao-exibir']

    def executar(self, versao):
        saida, erro = StringIO(), StringIO()
        with patch('sys.argv', self.args), patch.object(cli.sqlite3, 'sqlite_version_info', versao), \
                redirect_stdout(saida), redirect_stderr(erro):
            resultado = cli.main()
        texto = saida.getvalue() + erro.getvalue()
        self.assertNotIn(self.args[-1], texto)
        self.assertNotIn('projeto-ficticio', texto)
        return resultado, texto

    def test_sqlite_antigo_recusa_antes_de_tocar_arquivos(self):
        antes = {p.name: p.read_bytes() for p in self.origem.iterdir()}
        for versao in [(3, 39, 4), (3, 50, 1)]:
            with self.subTest(versao=versao), patch.object(perfil, 'preparar') as preparar, \
                    patch.object(cli.sqlite3, 'connect') as conectar:
                resultado, texto = self.executar(versao)
                self.assertEqual(resultado, 1)
                self.assertIn('.'.join(map(str, versao)), texto)
                self.assertIn('mínimo de segurança 3.50.2', texto)
                self.assertIn('Nenhum arquivo foi alterado', texto)
                preparar.assert_not_called()
                conectar.assert_not_called()
                self.assertFalse(self.destino.exists())
                self.assertEqual(antes, {p.name: p.read_bytes() for p in self.origem.iterdir()})

    def test_minimo_e_versao_superior_seguem_preparacao_e_conferencia(self):
        for versao in [(3, 50, 2), (3, 53, 1)]:
            with self.subTest(versao=versao), \
                    patch.object(perfil, 'preparar', return_value=self.destino) as preparar, \
                    patch.object(perfil, 'conferir', return_value={'tabelas': {'vendas': 0}}) as conferir:
                resultado, texto = self.executar(versao)
                self.assertEqual(resultado, 0)
                preparar.assert_called_once_with(self.origem, self.destino, self.args[-3], self.args[-1])
                conferir.assert_called_once_with(self.destino)
                self.assertIn('Perfil offline verificado', texto)

    def test_falha_inesperada_continua_sanitizada(self):
        with patch.object(perfil, 'preparar', side_effect=RuntimeError(self.args[-1])):
            resultado, texto = self.executar((3, 50, 2))
        self.assertEqual(resultado, 1)
        self.assertIn('Preparação não concluída', texto)
        self.assertNotIn('Traceback', texto)

    def test_falha_na_conferencia_nao_e_anunciada_como_sucesso(self):
        with patch.object(perfil, 'preparar', return_value=self.destino), \
                patch.object(perfil, 'conferir', side_effect=ValueError(self.args[-1])):
            resultado, texto = self.executar((3, 50, 2))
        self.assertEqual(resultado, 1)
        self.assertNotIn('Perfil offline verificado', texto)


if __name__ == '__main__':
    unittest.main()
