"""Qt/núcleo reais em ensaio com downloads e processos fictícios privados."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'reforma_desktop/tests'))
import test_configuracoes_qt as fixtures
from ProgramFeira import atualizador as nucleo, financeiro, backup_drive
from ProgramFeira.database import banco
from PySide6 import QtCore as Q, QtWidgets as W


class AtualizacaoTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.ConfiguracoesTests.setUpClass.__func__)
    setUp = fixtures.ConfiguracoesTests.setUp

    def esperar(self,c):
        fim = time.monotonic()+20
        while c.ocupado and time.monotonic()<fim:
            self.app.processEvents();time.sleep(.005)
        self.assertFalse(c.ocupado)
        self.app.processEvents()

    def janela(self):
        j = fixtures.ConfiguracoesTests.janela(self)
        self.addCleanup(self.esperar,j.atualizador)
        self.addCleanup(j.atualizador.parar)
        return j

    def preparar(self,j,cenario='normal'):
        c = j.atualizador
        c.selecionar_cenario(cenario)
        c.verificar();self.esperar(c)
        self.assertIsNotNone(c.release,c.status)
        c.preparar();self.esperar(c)
        return c

    def test_ensaio_reutiliza_nucleo_sem_rede_processos_ou_mudanca_do_banco(self):
        self.servico.salvar('2026-10-23','10','20','30')
        financeiro.inicializar()
        financeiro.salvar_lancamento('despesa','2026-10-23','Despesa fictícia','12,34')
        financeiro.salvar_taxa_anual(2025,'2025-01-01','2025-12-31','100')
        j = self.janela()
        extras = {'backup_drive.json':json.dumps({'pasta':str(self.pasta/'nao-tocar-drive')}),'sessao-nuvem.dpapi':'sessao-ficticia-nao-ler'}
        for nome,valor in extras.items():
            p = self.pasta/nome;p.write_text(valor,encoding='utf-8')
            self.addCleanup(p.unlink,missing_ok=True)
        antes = banco.CAMINHO_BANCO.read_bytes()
        chamadas_reais = nucleo.preparar,nucleo.instalar,nucleo.consultar
        with patch.object(nucleo,'baixar',side_effect=AssertionError('Download real proibido')), patch.object(nucleo.subprocess,'run',side_effect=AssertionError('Execução real proibida')), patch.object(nucleo.subprocess,'Popen',side_effect=AssertionError('Processo real proibido')), patch.object(backup_drive,'executar',side_effect=AssertionError('Drive proibido')):
            c = self.preparar(j)
            self.assertIsNotNone(c.preparacao,c.status)
            antigo = c.servico.preparacao['alvo']/'GestaoDaFeira.exe'
            conteudo = antigo.read_bytes()
            c.instalar();self.esperar(c)
        self.assertIsNotNone(c.resultado,c.status)
        self.assertEqual(antigo.read_bytes(),conteudo)
        self.assertEqual(banco.CAMINHO_BANCO.read_bytes(),antes)
        self.assertEqual(chamadas_reais,(nucleo.preparar,nucleo.instalar,nucleo.consultar))
        for nome,valor in extras.items():self.assertEqual((self.pasta/nome).read_text(encoding='utf-8'),valor)
        with closing(sqlite3.connect(c.resultado['backup'])) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(),('ok',))
            for tabela in ['vendas','financeiro_lancamentos','financeiro_taxas_anuais']:
                self.assertEqual(db.execute('SELECT count(*) FROM '+tabela).fetchone(),(1,))
        self.assertIn('Nenhum programa foi instalado',c.status)
        self.assertTrue(j.isVisible())

    def test_sem_versao_nova_e_publicacao_incompleta_nao_preparam(self):
        j = self.janela();d = j.atualizacoes();self.addCleanup(d.close)
        c = j.atualizador
        self.assertEqual(d.windowModality(),Q.Qt.WindowModality.ApplicationModal)
        for cenario,trecho in [('atual','nenhuma versão mais recente'),('incompleta','incompleta')]:
            c.selecionar_cenario(cenario)
            c.verificar();self.esperar(c)
            self.assertIsNone(c.release)
            self.assertFalse(d.botoes['preparar'].isEnabled())
            self.assertIn(trecho,c.status)
            self.assertIsNone(c.servico.temporaria)

    def test_hash_incorreto_recusa_pacote_e_limpa_preparacao(self):
        j = self.janela();c = self.preparar(j,'hash')
        self.assertIsNone(c.preparacao)
        self.assertIsNone(c.release)
        self.assertIsNone(c.servico.temporaria)
        self.assertIn('integridade',c.status)
        self.assertNotIn('inicio-do-helper-simulado',c.servico.chamadas)

    def test_candidata_reprovada_nao_chega_ao_helper(self):
        j = self.janela();c = self.preparar(j,'candidata')
        self.assertIsNone(c.preparacao)
        self.assertIn('verificação do executável',c.status)
        self.assertIn('teste-da-candidata-simulado',c.servico.chamadas)
        self.assertNotIn('inicio-do-helper-simulado',c.servico.chamadas)

    def test_cancelar_confirmacao_nao_instala_e_confirmar_nao_reinicia(self):
        j = self.janela();d = j.atualizacoes();self.addCleanup(d.close)
        c = self.preparar(j)
        with patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.No), patch.object(c,'instalar') as instalar:
            d.confirmar();instalar.assert_not_called()
        self.assertIsNone(c.resultado)
        with patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.Yes):d.confirmar()
        self.esperar(c)
        self.assertIsNotNone(c.resultado,c.status)
        self.assertTrue(j.isVisible())
        self.assertFalse(d.botoes['instalar'].isEnabled())

    def test_helper_com_falha_preserva_banco_e_permite_novo_ensaio(self):
        j = self.janela();antes = banco.CAMINHO_BANCO.read_bytes()
        c = self.preparar(j,'instalador')
        c.instalar();self.esperar(c)
        self.assertIsNone(c.resultado)
        self.assertIsNone(c.preparacao)
        self.assertIn('Nenhum programa foi instalado',c.status)
        self.assertEqual(banco.CAMINHO_BANCO.read_bytes(),antes)
        c = self.preparar(j)
        c.instalar();self.esperar(c)
        self.assertIsNotNone(c.resultado,c.status)

    def test_edicao_nuvem_e_backup_em_andamento_impedem_ensaio(self):
        j = self.janela();c = j.atualizador
        editor = W.QDialog(j);editor.open();self.addCleanup(editor.close)
        c.verificar();self.assertFalse(c.ocupado)
        self.assertIn('Finalize a edição',c.status)
        editor.close()
        j.nuvem.ocupado = True
        try:c.verificar();self.assertFalse(c.ocupado)
        finally:j.nuvem.ocupado = False
        self.assertIn('Aguarde',c.status)
        d = j.configuracoes();self.addCleanup(d.close)
        d.operacao = object()
        try:c.verificar();self.assertFalse(c.ocupado)
        finally:d.operacao = None
        self.assertIn('Finalize',c.status)

    def test_preferencia_atomicidade_persistencia_e_timer_de_consulta(self):
        j = self.janela();c = j.atualizador
        self.assertFalse(c.automatica)
        self.assertIsNone(c.timer)
        c.alterar_automatica(True)
        self.assertEqual(c.timer.interval(),12000)
        self.assertTrue(json.loads(c.preferencia.read_text())['consultar'])
        with patch('reforma_desktop.atualizacoes.os.replace',side_effect=OSError('Sem acesso')):c.alterar_automatica(False)
        self.assertTrue(c.automatica)
        self.assertTrue(json.loads(c.preferencia.read_text())['consultar'])
        self.assertIn('modo anterior',c.status)
        outro = self.janela()
        self.assertTrue(outro.atualizador.automatica)
        self.assertEqual(outro.atualizador.timer.interval(),12000)
        outro.atualizador.parar()
        c.alterar_automatica(False)
        self.assertIsNone(c.timer)

    def test_consulta_automatica_adia_edicao_e_nunca_prepara_ou_instala(self):
        j = self.janela();c = j.atualizador
        c.alterar_automatica(True)
        editor = W.QDialog(j);editor.open();self.addCleanup(editor.close)
        c.automaticamente()
        self.assertEqual(c.timer.interval(),30000)
        self.assertFalse(c.ocupado)
        editor.close()
        with patch.object(c.servico,'preparar',side_effect=AssertionError('Preparou automaticamente')),patch.object(c.servico,'instalar',side_effect=AssertionError('Instalou automaticamente')):
            c.automaticamente();self.esperar(c)
        self.assertIsNotNone(c.release)
        self.assertIsNone(c.preparacao)
        self.assertIsNone(c.resultado)

    def test_trabalhador_responsivo_bloqueia_fechamento_e_sanitiza_falha(self):
        j = self.janela();d = j.atualizacoes();self.addCleanup(d.close)
        c = j.atualizador
        liberar = threading.Event();self.addCleanup(liberar.set)
        def consulta():
            liberar.wait(3)
            raise RuntimeError('nao-expor-credencial-ficticia')
        with patch.object(c.servico,'consultar',side_effect=consulta):
            c.verificar()
            j.close();d.reject()
            self.assertTrue(j.isVisible());self.assertTrue(d.isVisible())
            vistos = []
            Q.QTimer.singleShot(0,lambda:vistos.append(True))
            self.app.processEvents()
            liberar.set();self.esperar(c)
        self.assertTrue(vistos)
        self.assertTrue(j.isEnabled())
        self.assertNotIn('nao-expor',c.status)
        self.assertFalse(c.ocupado)
