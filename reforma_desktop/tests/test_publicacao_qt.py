"""Contraprovas da liberação: evidências fictícias não executam publicação."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.publicar_desktop_qt import conferir
from ProgramFeira.atualizador import PACOTE


class PublicacaoQtTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.pasta = Path(temp.name)
        self.commit = 'a'*40
        (self.pasta/PACOTE).write_bytes(b'fixture; nao e binario Windows')
        self.sha = hashlib.sha256((self.pasta/PACOTE).read_bytes()).hexdigest()
        (self.pasta/'SHA256.txt').write_text(f'{self.sha}  {PACOTE}\n')
        self.salvar('VALIDACAO_WINDOWS.json', dict(versao='2.0.0', plataforma='win32', sucesso=True,
            empacotado=True, backup_seguranca=True, banco_isolado=True, interface='PySide6', commit_base=self.commit))
        self.transicao = dict(versao='2.0.0',commit_base=self.commit,pacote_sha256=self.sha,sucesso=True,
            binarios_reais=True,reinicio_confirmado=True,dados_preservados=True,preferencias_preservadas=True,
            troca=dict(origem='1.7.1',destino='2.0.0',sucesso=True,recuperacao_apos_falha=False),
            rollback=dict(origem='1.7.1',destino='2.0.0',sucesso=True,recuperacao_apos_falha=True))
        self.salvar('VALIDACAO_ATUALIZADOR.json', self.transicao)
        for suite in ('reforma_desktop-tests','tests','prototipos-reforma'):
            self.salvar(suite+'.json',dict(plataforma='Windows-ficticio',sucesso=True,executados=1,
                ignorados=[],falhas=[],erros=[]))
        self.salvar('REVISAO.json',dict(casos_conformes=True,commit_base=self.commit))

    def salvar(self,nome,dados):
        (self.pasta/nome).write_text(json.dumps(dados),encoding='utf-8')

    def test_aceita_conjunto_coerente_sem_publicar(self):
        self.assertEqual(len(conferir(self.pasta,self.commit,self.pasta)),4)

    def test_rejeita_zip_alterado_e_relatorio_de_outra_revisao(self):
        (self.pasta/PACOTE).write_bytes(b'alterado')
        with self.assertRaisesRegex(ValueError,'SHA-256'): conferir(self.pasta,self.commit,self.pasta)
        (self.pasta/PACOTE).write_bytes(b'fixture; nao e binario Windows')
        with self.assertRaisesRegex(ValueError,'revisão'): conferir(self.pasta,'b'*40,self.pasta)

    def test_rejeita_ausencia_de_rollback_e_troca_de_mesma_versao(self):
        for campo,valor in [('rollback',{}),('troca',dict(origem='2.0.0',destino='2.0.0',sucesso=True,recuperacao_apos_falha=False))]:
            with self.subTest(campo=campo):
                self.salvar('VALIDACAO_ATUALIZADOR.json',dict(self.transicao,**{campo:valor}))
                with self.assertRaises(ValueError): conferir(self.pasta,self.commit,self.pasta)

    def test_rejeita_suite_vazia_ou_testes_windows_ignorados(self):
        for dados in [dict(plataforma='Windows',sucesso=True,executados=0),
                      dict(plataforma='Windows',sucesso=True,executados=2,ignorados=[{'motivo':'nao executado'}])]:
            self.salvar('tests.json',dados)
            with self.assertRaisesRegex(ValueError,'regressão'): conferir(self.pasta,self.commit,self.pasta)
