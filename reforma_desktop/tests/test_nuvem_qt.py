"""Núcleo real de sincronização com UI Qt e serviço local sem tráfego de rede."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'reforma_desktop/tests'))
import test_configuracoes_qt as fixtures
from ProgramFeira import financeiro, sessao_windows, nuvem, sincronizacao, automacao_nuvem
from ProgramFeira.database import banco
from PySide6 import QtCore as Q, QtWidgets as W
from reforma_desktop.painel_nuvem import Revisao
from reforma_desktop.servico_nuvem_estudo import URL, EMAIL


class NuvemTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.ConfiguracoesTests.setUpClass.__func__)
    setUp = fixtures.ConfiguracoesTests.setUp

    def esperar(self, n):
        limite = time.monotonic() + 20
        while n.ocupado and time.monotonic() < limite:
            self.app.processEvents()
            time.sleep(.005)
        self.assertFalse(n.ocupado)
        self.app.processEvents()

    def janela(self):
        j = fixtures.ConfiguracoesTests.janela(self)
        self.addCleanup(self.esperar, j.nuvem)
        self.addCleanup(j.nuvem.agendador.parar)
        return j

    def vincular(self, j):
        n = j.nuvem
        n.conectar(); self.esperar(n)
        self.assertEqual(n.sessao.email, EMAIL)
        n.conferir(); self.esperar(n)
        self.assertIsNotNone(n.preparacao, n.status)
        n.transferir(); self.esperar(n)
        n.sincronizar(); self.esperar(n)
        self.assertTrue(n.vinculado, n.status)
        n.agendador.parar()
        return n

    def test_transferencia_vinculo_e_duas_direcoes_sem_rede(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela()
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Rede proibida')):
            n = self.vincular(j)
            self.servico.salvar('2026-10-25','5','6','7')
            n.sincronizar(); self.esperar(n)
            self.assertIn('Enviadas: 1', n.status)
            dia = n.cliente.simular_venda_externa()
            n.sincronizar(); self.esperar(n)
        self.assertEqual(dia, '2026-10-25')
        self.assertEqual(banco.buscar_venda_por_data(dia)[3], 7)
        self.assertIn('recebidas: 1', n.status)
        self.assertEqual(j.resultado['indicadores']['quantidade'], 2)

    def test_transferencia_confirmada_na_ui_e_mudanca_apos_conferencia(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela(); n = j.nuvem
        painel = j.conexao_nuvem()
        n.conectar(); self.esperar(n)
        n.conferir(); self.esperar(n)
        self.assertFalse(n.cliente.arquivo.exists())
        with patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.No):
            painel.transferir()
        self.assertIsNotNone(n.preparacao)
        self.servico.salvar('2026-10-25','1','0','0')
        with patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.Yes):
            painel.transferir()
        self.esperar(n)
        self.assertIn('mudou após a conferência', n.status)
        self.assertFalse(n.cliente.arquivo.exists())
        self.assertTrue(n.agendador.pausado)
        painel.close()

    def test_financas_parcelas_taxas_e_ajuste_anual_preservados(self):
        financeiro.inicializar()
        financeiro.salvar_lancamento('despesa','2026-10-09','Compra fictícia','100','Cartão de crédito','Outros',3,data_compra='2026-10-09')
        financeiro.salvar_lancamento('taxa','2026-10-23','Maquininha fictícia','1,23','Outro','Feira')
        financeiro.salvar_taxa_anual(2025,'2025-01-01','2025-12-31','10')
        n = self.vincular(self.janela())
        estado = n.cliente.ler()
        parcelas = [r for r in estado['dados']['financeiro_lancamentos'].values() if r['tipo']=='despesa']
        self.assertEqual(len(parcelas),3)
        self.assertEqual(sum(r['valor_centavos'] for r in parcelas),10000)
        self.assertTrue(all(r['data_compra']=='2026-10-09' for r in parcelas))
        self.assertEqual(len(estado['dados']['financeiro_taxas_anuais']),1)
        with closing(sqlite3.connect(banco.CAMINHO_BANCO)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(),('ok',))

    def test_automatico_60_segundos_preserva_consulta_e_filtro_pendente(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela(); n = self.vincular(j)
        j.mes.setCurrentIndex(9)
        consulta = j.consulta
        n.cliente.simular_venda_externa()
        n.agendador._disparar(); self.esperar(n)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],21)
        self.assertEqual(j.consulta,consulta)
        self.assertEqual(j.mes.currentIndex(),9)
        self.assertEqual(n.relogio.tarefas[n.agendador.tarefa].interval(),60000)
        n.cliente.simular_venda_externa()
        painel = j.configuracoes()
        n.agendador.parar(); n.agendador._disparar()
        self.assertFalse(n.ocupado)
        self.assertEqual(n.relogio.tarefas[n.agendador.tarefa].interval(),5000)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],21)
        painel.close()

    def test_sem_mudanca_nao_cria_backup_e_gravacao_agenda_envio(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela(); n = self.vincular(j)
        anteriores = set((self.pasta/'backups').glob('*.db'))
        n.agendador._disparar(); self.esperar(n)
        self.assertEqual(anteriores,set((self.pasta/'backups').glob('*.db')))
        self.servico.salvar('2026-10-25','1','2','3')
        j.atualizar()
        self.assertEqual(n.relogio.tarefas[n.agendador.tarefa].interval(),2000)

    def test_falha_temporaria_backoff_e_resposta_perdida_sem_duplicar(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela(); n = self.vincular(j)
        n.cliente.indisponivel = True
        n.agendador._disparar(); self.esperar(n)
        self.assertFalse(n.agendador.pausado)
        self.assertEqual(n.relogio.tarefas[n.agendador.tarefa].interval(),60000)
        n.agendador.parar(); n.agendador._disparar(); self.esperar(n)
        self.assertEqual(n.relogio.tarefas[n.agendador.tarefa].interval(),120000)
        n.cliente.indisponivel = False
        self.servico.salvar('2026-10-25','1','2','3')
        n.cliente.perder_resposta = True
        n.sincronizar(); self.esperar(n)
        self.assertIn('perdida após confirmação', n.status)
        n.sincronizar(); self.esperar(n)
        self.assertEqual(len(n.cliente.ler()['dados']['vendas']),2)
        self.assertEqual(len(banco.listar_vendas()),2)

    def test_conflito_escolha_explicita_e_revisao_desatualizada_recusada(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela(); n = self.vincular(j)
        venda = banco.buscar_venda_por_data('2026-10-23')
        self.servico.salvar('2026-10-23','10','40','30',venda)
        n.cliente.simular_venda_externa()
        n.sincronizar(); self.esperar(n)
        self.assertTrue(n.agendador.pausado)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],40)
        n.conferir_conflitos(); self.esperar(n)
        self.assertEqual(len(n.revisao['conflitos']),1)
        r = Revisao(j,n.revisao,lambda revisao,escolhas:n.sincronizar(revisao,escolhas))
        self.addCleanup(r.close)
        r.escolher('nuvem')
        n.cliente.simular_venda_externa()
        with patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.Yes):
            r.confirmar_escolhas()
        self.esperar(n)
        self.assertIn('mudaram desde a revisão',n.status)
        self.assertIsNone(n.revisao)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],40)
        n.conferir_conflitos(); self.esperar(n)
        r2 = Revisao(j,n.revisao,lambda revisao,escolhas:n.sincronizar(revisao,escolhas))
        self.addCleanup(r2.close)
        r2.escolher('nuvem')
        with patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.Yes):
            r2.confirmar_escolhas()
        self.esperar(n)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],22)
        self.assertFalse(n.agendador.pausado)

    def test_renovacao_dpapi_e_desconexao_na_pasta_do_estudo(self):
        j = self.janela(); n = self.vincular(j)
        n.sessao = replace(n.sessao,expira_em=1)
        n.cliente._ultima_sessao = None
        n.sincronizar(); self.esperar(n)
        self.assertGreater(n.sessao.expira_em,time.time())
        arquivo = self.pasta/sessao_windows.NOME
        if sessao_windows.DISPONIVEL:
            self.assertTrue(arquivo.exists())
            self.assertNotIn(b'renovavel-ficticio',arquivo.read_bytes())
            recuperada = sessao_windows.carregar(self.pasta,URL)
            self.assertEqual(recuperada.token,'')
            self.assertEqual(recuperada.email,EMAIL)
            novo = self.janela()
            self.assertIsNotNone(novo.nuvem.sessao)
            novo.nuvem.agendador.parar()
        else:
            self.assertFalse(arquivo.exists())
            self.assertIn('não é persistida',n.status)
        n.desconectar()
        self.assertIsNone(n.sessao)
        self.assertFalse(arquivo.exists())
        self.assertTrue(n.vinculado)
        self.assertTrue(n.cliente.arquivo.exists())

    def test_trabalhador_nao_fecha_janela_e_sanitiza_erro_inesperado(self):
        j = self.janela(); n = j.nuvem
        liberar = threading.Event()
        self.addCleanup(liberar.set)
        def trabalhar():
            liberar.wait(3)
            raise RuntimeError('senha-ou-token-que-nao-pode-aparecer')
        n.rodar(trabalhar,lambda r:None,'Aguarde')
        j.close()
        self.assertTrue(j.isVisible())
        vistos = []
        Q.QTimer.singleShot(0,lambda:vistos.append(True))
        self.app.processEvents()
        liberar.set(); self.esperar(n)
        self.assertTrue(vistos)
        self.assertNotIn('senha-ou-token',n.status)
        self.assertTrue(j.isEnabled())
        self.assertTrue(n.agendador.pausado)

    def test_sessao_expirada_pausa_sem_novas_tentativas(self):
        n = self.vincular(self.janela())
        n.sessao = replace(n.sessao,refresh_token='',expira_em=1)
        n.cliente._ultima_sessao = None
        n.sincronizar(); self.esperar(n)
        self.assertTrue(n.agendador.pausado)
        self.assertIsNone(n.agendador.tarefa)
        self.assertIn('Entre novamente',n.status)

    def test_consulta_em_andamento_adia_aplicacao_se_edicao_for_aberta(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela(); n = self.vincular(j)
        n.cliente.simular_venda_externa()
        liberar = threading.Event()
        self.addCleanup(liberar.set)
        original = n.cliente.sincronizar
        def consultar(*args,**kwargs):
            liberar.wait(3)
            return original(*args,**kwargs)
        with patch.object(n.cliente,'sincronizar',side_effect=consultar):
            n.agendador._disparar()
            self.assertTrue(j.isEnabled())
            editor = W.QDialog(j)
            self.addCleanup(editor.close)
            editor.open()
            self.app.processEvents()
            liberar.set(); self.esperar(n)
            self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],20)
            self.assertEqual(n.relogio.tarefas[n.agendador.tarefa].interval(),5000)
            editor.close()
        n.agendador.parar(); n.agendador._disparar(); self.esperar(n)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],21)

    def test_servico_ausente_nao_parece_exclusao_de_todos_os_registros(self):
        self.servico.salvar('2026-10-23','10','20','30')
        n = self.vincular(self.janela())
        n.cliente.arquivo.unlink()
        n.sincronizar(); self.esperar(n)
        self.assertIn('arquivo do serviço fictício está ausente',n.status)
        self.assertEqual(len(banco.listar_vendas()),1)
        self.assertTrue(n.agendador.pausado)

    def test_restauracao_pausa_automacao_na_reabertura(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela(); n = self.vincular(j)
        copia = banco.criar_backup()
        c = j.configuracoes()
        with patch.object(c,'arquivo_backup',return_value=str(copia)), patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.Yes):
            c.restaurar()
        limite = time.monotonic()+15
        while c.operacao is not None and time.monotonic()<limite:
            self.app.processEvents(); time.sleep(.005)
        self.assertTrue(c.reiniciar,c.status.text())
        self.assertFalse(automacao_nuvem.carregar_preferencia(self.pasta))
        c.reject()
        novo = self.janela()
        self.assertFalse(novo.nuvem.automatico)
        self.assertIsNone(novo.nuvem.agendador.tarefa)

    def test_preferencia_com_falha_preserva_modo(self):
        n = self.janela().nuvem
        with patch.object(automacao_nuvem,'salvar_preferencia',side_effect=OSError()):
            n.alterar_automatico(False)
        self.assertTrue(n.automatico)
        self.assertIn('anterior foi preservado',n.status)
