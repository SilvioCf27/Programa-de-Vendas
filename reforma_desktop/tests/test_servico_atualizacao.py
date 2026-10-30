"""Adaptador real respeita versão própria, verificação e propriedade do stage."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ProgramFeira import atualizador as nucleo
from reforma_desktop.servico_atualizacao import ServicoAtualizacao
from reforma_desktop.versao import VERSAO


class AtualizacaoRealTests(unittest.TestCase):
    def test_versao_qt_nao_altera_versao_estavel(self):
        s = ServicoAtualizacao('/ficticio/vendas.db')
        with patch.object(nucleo, 'consultar', return_value=None) as consultar:
            self.assertIsNone(s.consultar())
        consultar.assert_called_once_with(versao_atual=VERSAO)
        self.assertEqual(nucleo.VERSAO, '1.7.1')

    def test_consulta_nao_oferece_versao_igual_ao_desktop(self):
        def baixar(url, destino, limite):
            Path(destino).write_text(json.dumps({'tag_name':'v2.0.0', 'draft':False, 'prerelease':False}))
        with patch.object(nucleo, 'baixar', baixar):
            self.assertIsNone(nucleo.consultar(versao_atual='2.0.0'))

    def test_falha_de_instalacao_preserva_preparacao_e_sucesso_transfere_propriedade(self):
        s = ServicoAtualizacao('/ficticio/vendas.db')
        p = {'stage': Path('/ficticio/.feira-atualizacao-teste')}
        s.preparacao = p
        with patch.object(nucleo, 'instalar', side_effect=OSError('falha-ficticia')):
            with self.assertRaises(OSError): s.instalar()
        self.assertIs(s.preparacao, p)
        with patch.object(nucleo, 'instalar', return_value=object()) as instalar:
            self.assertEqual(s.instalar(), {'reiniciar':True})
        instalar.assert_called_once_with(p, s.banco)
        self.assertIsNone(s.preparacao)
        with patch('shutil.rmtree') as apagar:
            s.limpar()
        apagar.assert_not_called()

    def test_nao_prepara_sem_windows_empacotado(self):
        s = ServicoAtualizacao('/ficticio/vendas.db')
        with patch('sys.platform', 'linux'), patch.object(nucleo, 'preparar') as preparar:
            with self.assertRaises(ValueError): s.preparar({'versao':'v2.0.1'})
        preparar.assert_not_called()

    def test_recibo_de_abertura_tem_versao_qt_e_mesmas_guardas(self):
        with tempfile.TemporaryDirectory() as temp:
            raiz = Path(temp)
            stage = raiz/'.feira-atualizacao-teste'; stage.mkdir()
            exe = raiz/'GestaoDaFeira/GestaoDaFeira.exe'
            recibo = stage/'abriu.json'
            with patch('sys.executable', str(exe)), patch('sys.argv', ['exe','--confirmar-atualizacao',str(recibo)]):
                nucleo.confirmar_inicio(versao=VERSAO)
                self.assertEqual(json.loads(recibo.read_text())['versao'], VERSAO)
                with self.assertRaises(ValueError): nucleo.confirmar_inicio(versao=VERSAO)
