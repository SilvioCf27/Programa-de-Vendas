"""Regressão das seis lacunas, com dados fictícios e sem alterar o núcleo estável."""
from datetime import date
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'reforma_desktop/tests'))
import test_configuracoes_qt as fixtures
from PySide6 import QtCore as Q, QtWidgets as W, QtTest
from ProgramFeira.database import banco
from reforma_desktop.aplicacao import FormularioVenda
from reforma_desktop.diagnostico_qt import instalar, registrar_seguro


class CorrecaoTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.ConfiguracoesTests.setUpClass.__func__)
    setUp=fixtures.ConfiguracoesTests.setUp
    janela=fixtures.ConfiguracoesTests.janela

    def eventos(self):
        for _ in range(5):self.app.processEvents()

    def esperar(self,condicao):
        fim=time.monotonic()+10
        while condicao() and time.monotonic()<fim:
            self.app.processEvents();time.sleep(.005)
        self.assertFalse(condicao())
        self.eventos()

    def incompleta(self,campo):
        campo.setFocus()
        campo.setSelectedSection(W.QDateEdit.Section.YearSection)
        QtTest.QTest.keyClicks(campo,'2')
        self.assertFalse(campo.hasAcceptableInput())

    def logs(self,pasta=None):
        resultado=[]
        for p in ((pasta or self.pasta)/'logs').glob('*.jsonl'):
            resultado.extend(json.loads(linha) for linha in p.read_text(encoding='utf-8').splitlines())
        return resultado

    def test_venda_data_parcial_recusa_sem_backup_e_permite_corrigir(self):
        j=self.janela();f=j.abrir_formulario();self.eventos()
        f.data.setDate(Q.QDate(2035,1,2));f.campos[0].setText('10')
        antes=set((self.pasta/'backups').glob('*.db'))
        self.incompleta(f.data);f.gravar()
        self.assertEqual(banco.listar_vendas(),[])
        self.assertEqual(set((self.pasta/'backups').glob('*.db')),antes)
        self.assertIn('Confirme uma data válida',f.erro.text())
        self.assertTrue(f.salvar.isEnabled())
        f.data.setDate(Q.QDate(2035,1,3));f.gravar()
        self.assertIsNotNone(banco.buscar_venda_por_data('2035-01-03'))

    def test_clique_e_enter_nao_confirmam_ano_parcial_por_perda_de_foco(self):
        j=self.janela()
        for acao in ('clique','enter'):
            with self.subTest(acao=acao):
                f=j.abrir_formulario();self.eventos()
                f.data.setDate(Q.QDate(2035,1,2));f.campos[0].setText('10')
                self.incompleta(f.data)
                if acao=='clique':QtTest.QTest.mouseClick(f.salvar,Q.Qt.MouseButton.LeftButton)
                else:QtTest.QTest.keyClick(f.data,Q.Qt.Key.Key_Return)
                self.eventos()
                self.assertEqual(banco.listar_vendas(),[])
                # Mesmo após a normalização visual, só uma confirmação explícita libera.
                f.gravar()
                self.assertEqual(banco.listar_vendas(),[])
                f.data.calendarWidget().clicked.emit(Q.QDate(2035,1,2))
                f.gravar()
                self.assertIsNotNone(banco.buscar_venda_por_data('2035-01-02'))
                venda=banco.buscar_venda_por_data('2035-01-02')
                self.servico.excluir([venda])

    def analises(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j=self.janela();j.mostrar('Análises');self.eventos()
        p=j.analises
        for s in (p.a,p.b):
            s.tipo.setCurrentText('Intervalo')
            s.inicio.setDate(Q.QDate(2026,10,1));s.fim.setDate(Q.QDate(2026,10,31))
        p.comparar()
        return j,p

    def test_ab_valida_as_quatro_datas_sem_substituir_resultado(self):
        j,p=self.analises()
        original=p.ultima_comparacao
        for campo in (p.a.inicio,p.a.fim,p.b.inicio,p.b.fim):
            with self.subTest(campo=campo.accessibleName()):
                valor=campo.date()
                self.incompleta(campo);p.comparar()
                self.assertIs(p.ultima_comparacao,original)
                self.assertIn('Não atualizado',p.aviso.text())
                campo.setDate(valor)
        p.comparar()
        self.assertIn('Comparação aplicada',p.aviso.text())

    def test_clique_comparar_preserva_comparacao_com_data_incompleta(self):
        j,p=self.analises();anterior=p.ultima_comparacao
        self.incompleta(p.a.inicio)
        b=next(b for b in p.findChildren(W.QPushButton) if b.text()=='Comparar períodos')
        QtTest.QTest.mouseClick(b,Q.Qt.MouseButton.LeftButton);self.eventos()
        self.assertIs(p.ultima_comparacao,anterior)
        self.assertIn('Não atualizado',p.aviso.text())

    def test_ab_pendente_incompleto_nao_impede_atualizar_consulta_aplicada(self):
        j,p=self.analises()
        limites=p.ultima_comparacao['limites']
        self.incompleta(p.a.inicio)
        venda=banco.buscar_venda_por_data('2026-10-23')
        self.servico.salvar('2026-10-23','20','20','30',venda)
        j.atualizar()
        self.assertEqual(p.ultima_comparacao['limites'],limites)
        self.assertEqual(p.ultima_comparacao['a']['total'],70)
        self.assertIn('Seleção incompleta',p.aviso.text())

    def test_datas_ocultas_nao_bloqueiam_comparar_mes(self):
        j,p=self.analises()
        self.incompleta(p.a.inicio)
        p.a.tipo.setCurrentText('Mês');p.b.tipo.setCurrentText('Mês')
        p.comparar()
        self.assertIn('Comparação aplicada',p.aviso.text())

    def test_enter_numerico_e_retorno_respeitam_pagina_id_e_foco(self):
        for dia in range(1,8):self.servico.salvar(f'2026-10-{dia:02}','1','0','0')
        j=self.janela();j.limpar()
        j.tabela.tamanho.setCurrentText('5');j.tabela.mover(1)
        t=j.tabela.table;j.scroll.ensureWidgetVisible(t);j.activateWindow();self.eventos()
        for tecla in (Q.Qt.Key.Key_Return,Q.Qt.Key.Key_Enter):
            t.setCurrentCell(0,2);t.setFocus();self.eventos()
            alvo=j.tabela.visiveis[0][0]
            with patch.object(j,'abrir_formulario') as abrir:
                QtTest.QTest.keyClick(t,tecla);self.eventos()
                self.assertEqual(abrir.call_count,1)
                self.assertEqual(abrir.call_args[0][0][0],alvo)
        # Enter em outro controle não pode editar a linha da tabela.
        j.busca.setFocus();self.eventos()
        with patch.object(j,'abrir_formulario') as abrir:
            QtTest.QTest.keyClick(j.busca,Q.Qt.Key.Key_Return);self.eventos()
            abrir.assert_not_called()

    def test_hook_callback_sanitiza_log_e_aviso_e_restaura_hook(self):
        anterior=sys.excepthook;avisos=[]
        restaurar=instalar(self.pasta,avisos.append)
        try:
            try:raise RuntimeError('SEGREDO-CALLBACK-123')
            except RuntimeError as erro:sys.excepthook(type(erro),erro,erro.__traceback__)
        finally:restaurar()
        self.assertIs(sys.excepthook,anterior)
        registros=self.logs()
        self.assertEqual(len(registros),1)
        self.assertEqual(registros[0]['tipo'],'RuntimeError')
        self.assertEqual(set(registros[0]),{'data','versao','tipo','pilha'})
        self.assertNotIn('SEGREDO',json.dumps(registros)+str(avisos))
        self.assertTrue(avisos)

    def test_hook_fora_da_thread_principal_so_registra_sem_usar_widgets(self):
        avisos=[];restaurar=instalar(self.pasta,avisos.append)
        def executar():
            try:raise RuntimeError('SEGREDO-THREAD-123')
            except RuntimeError as erro:sys.excepthook(type(erro),erro,erro.__traceback__)
        try:
            t=threading.Thread(target=executar);t.start();t.join(timeout=5)
            self.assertFalse(t.is_alive())
        finally:restaurar()
        self.assertFalse(avisos)
        self.assertEqual(self.logs()[0]['tipo'],'RuntimeError')
        self.assertNotIn('SEGREDO',str(self.logs()))

    def test_tres_trabalhadores_registram_erro_original_sem_mensagem(self):
        from reforma_desktop.conexao_nuvem import Tarefa as Nuvem
        from reforma_desktop.atualizacoes import Tarefa as Atualizacao
        from reforma_desktop.operacoes_backup import Operacao
        j=self.janela()
        def falhar():raise RuntimeError('SEGREDO-WORKER-123')
        for classe in (Nuvem,Atualizacao,Operacao):
            t=classe(falhar,j);spy=QtTest.QSignalSpy(t.resultado)
            t.start();self.esperar(t.isRunning);t.wait();self.eventos()
            self.assertEqual(spy.count(),1)
            self.assertFalse(spy.at(0)[0])
            t.deleteLater()
        self.assertEqual(len(self.logs()),3)
        self.assertTrue(all(r['tipo']=='RuntimeError' for r in self.logs()))
        self.assertNotIn('SEGREDO',str(self.logs()))

    def test_falha_do_registro_nao_esconde_resultado_original(self):
        with patch('reforma_desktop.diagnostico_qt.registrar',side_effect=OSError('sem acesso')):
            self.assertFalse(registrar_seguro(RuntimeError('ficticio'),self.pasta))
        self.assertFalse(registrar_seguro(RuntimeError('ficticio'),None))

    def test_falha_na_abertura_registra_diagnostico_sem_imprimir_segredo(self):
        import executar_reforma
        pasta=self.pasta/'entrada'
        saida=io.StringIO()
        with patch.dict(os.environ),patch.object(sys,'argv',['executar_reforma.py','--pasta-estudo',str(pasta)]),patch('reforma_desktop.aplicacao.iniciar',side_effect=RuntimeError('SEGREDO-ABERTURA-123')),patch.object(sys,'stderr',saida):
            self.assertEqual(executar_reforma.main(),1)
        self.assertNotIn('SEGREDO',saida.getvalue())
        self.assertEqual(self.logs(pasta)[0]['tipo'],'RuntimeError')
        self.assertNotIn('SEGREDO',str(self.logs(pasta)))

    def test_backup_ativo_impede_fechar_principal_e_depois_libera(self):
        j=self.janela();c=j.configuracoes();self.eventos()
        liberar=threading.Event();self.addCleanup(liberar.set)
        c.executar(lambda:liberar.wait(5),lambda r:None)
        j.close()
        self.assertTrue(j.isVisible());self.assertIsNotNone(c.operacao)
        liberar.set();self.esperar(lambda:c.operacao is not None)
        c.close();j.close()
        self.assertFalse(j.isVisible())

    def test_thread_filha_ativa_sem_flags_tambem_impede_encerramento(self):
        from reforma_desktop.operacoes_backup import Operacao
        j=self.janela();liberar=threading.Event();self.addCleanup(liberar.set)
        t=Operacao(lambda:liberar.wait(5),j)
        t.start();j.close()
        self.assertTrue(j.isVisible())
        liberar.set();self.esperar(t.isRunning);t.wait();t.deleteLater()
        j.close();self.assertFalse(j.isVisible())

    def test_virada_so_confirma_dia_apos_sucesso_e_repete_se_falhar(self):
        j=self.janela();j.dia_exibido=date(2026,10,26)
        with patch.object(j,'atualizar',side_effect=[sqlite3.OperationalError('SEGREDO-SQLITE-123'),None]) as atualizar:
            j.verificar_dia()
            self.assertEqual(j.dia_exibido,date(2026,10,26))
            self.assertIn('nova tentativa',j.status.text())
            self.assertTrue(j.relogio.isActive())
            j.verificar_dia();j.verificar_dia()
        self.assertEqual(atualizar.call_count,2)
        self.assertEqual(j.dia_exibido,date(2026,10,27))
        self.assertIn('Consulta atualizada',j.status.text())
        j.dia_exibido=date(2026,10,26)
        j.status.setText('Exportação concluída.')
        with patch.object(j,'atualizar'):
            j.verificar_dia()
        self.assertEqual(j.status.text(),'Exportação concluída.')
        self.assertEqual(self.logs()[0]['tipo'],'OperationalError')
        self.assertNotIn('SEGREDO',str(self.logs()))
