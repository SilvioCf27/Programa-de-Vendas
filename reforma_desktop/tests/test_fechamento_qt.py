"""Fechamento por vigência Qt sobre núcleo/cliente existentes, sem rede real."""
from datetime import date
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'reforma_desktop/tests'))
import test_nuvem_qt as fixtures
from ProgramFeira import fechamento, financeiro
from ProgramFeira.database import banco
from PySide6 import QtWidgets as W
from reforma_desktop.servico_nuvem_estudo import ClienteEstudo


class FechamentoTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.NuvemTests.setUpClass.__func__)
    setUp = fixtures.NuvemTests.setUp
    janela = fixtures.NuvemTests.janela
    esperar = fixtures.NuvemTests.esperar
    vincular = fixtures.NuvemTests.vincular

    def conectar(self,j):
        j.nuvem.conectar()
        self.esperar(j.nuvem)
        j.nuvem.agendador.parar()

    def editor(self,j):
        e = j.configurar_fechamento()
        self.addCleanup(e.close)
        e.carregar()
        self.esperar(j.nuvem)
        self.assertTrue(e.conferida,j.nuvem.status)
        return e

    def futuro(self,e,dia=15,ano=2090,mes=11):
        e.ano.setValue(ano)
        e.mes.setCurrentIndex(mes-1)
        e.dia.setValue(dia)

    def salvar(self,j,e):
        with patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.Yes):
            e.enviar()
        self.esperar(j.nuvem)

    def test_leitura_sem_sessao_nao_altera_banco(self):
        j = self.janela()
        antes = banco.CAMINHO_BANCO.read_bytes()
        e = j.configurar_fechamento(); self.addCleanup(e.close)
        self.assertFalse(e.salvar.isEnabled())
        self.assertFalse(e.consultar.isEnabled())
        self.assertFalse(e.dia.isEnabled())
        self.assertIn('dia 09',e.historico.toPlainText())
        self.assertEqual(antes,banco.CAMINHO_BANCO.read_bytes())

    def test_previa_transicao_fevereiro_e_compra_no_fechamento(self):
        j = self.janela(); self.conectar(j)
        e = self.editor(j)
        self.futuro(e)
        self.assertIn('10/10/2090 a 15/11/2090',e.previa.text())
        self.assertIn('16/11/2090 a 15/12/2090',e.previa.text())
        self.futuro(e,31,2092,2)
        self.assertIn('10/01/2092 a 29/02/2092',e.previa.text())
        self.assertIn('01/03/2092 a 31/03/2092',e.previa.text())
        self.assertEqual(fechamento.primeira_fatura('2092-02-29',e.proposta['historico']),'2092-03-31')
        self.assertEqual(fechamento.estado()['versao'],0)

    def test_salvar_preserva_historico_fechado_e_parcelas_existentes(self):
        financeiro.inicializar()
        financeiro.salvar_lancamento('despesa','2090-10-09','Compra fictícia','100','Cartão de crédito','Outros',3,data_compra='2090-10-09')
        antes = financeiro.listar_lancamentos('0001-01-01','9999-12-31')
        periodo_antigo = fechamento.periodo(2026,9)
        j = self.janela(); self.conectar(j)
        e = self.editor(j); self.futuro(e)
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Rede proibida')):
            self.salvar(j,e)
        self.assertEqual(e.config,{'versao':1,'historico':[{'vigencia':'2090-11-01','dia':15}]})
        self.assertEqual(fechamento.periodo(2026,9),periodo_antigo)
        self.assertEqual(financeiro.listar_lancamentos('0001-01-01','9999-12-31'),antes)
        self.assertTrue(list((self.pasta/'backups').glob('*antes-alterar-fechamento*.db')))
        outro = ClienteEstudo(self.pasta)
        self.assertEqual(outro.fechamentos(j.nuvem.sessao),e.config)
        self.assertEqual(fechamento.carregar(banco.CAMINHO_BANCO),e.config)
        self.assertIn('fictícia salva',j.nuvem.status)

    def test_vigencia_atual_ano_incompleto_e_cancelamento_nao_gravam(self):
        j = self.janela(); self.conectar(j)
        e = self.editor(j)
        e.ano.setValue(2026);e.mes.setCurrentIndex(9)
        self.assertIn('próximo mês',e.erro.text())
        self.assertFalse(e.salvar.isEnabled())
        self.futuro(e)
        with patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.No), patch.object(j.nuvem,'salvar_fechamento') as salvar:
            e.enviar();salvar.assert_not_called()
        e.ano.lineEdit().setText('20')
        with patch.object(j.nuvem,'salvar_fechamento') as salvar:
            e.enviar();salvar.assert_not_called()
        self.assertIn('Confirme',e.erro.text())
        self.assertEqual(fechamento.estado()['versao'],0)

    def test_versao_concorrente_exige_consulta_e_preserva_campos(self):
        j = self.janela(); self.conectar(j)
        e = self.editor(j); self.futuro(e,15)
        j.nuvem.cliente.salvar_fechamento(j.nuvem.sessao,0,'2090-11-01',20)
        self.salvar(j,e)
        self.assertIn('mudou no serviço fictício',j.nuvem.status)
        self.assertFalse(e.conferida)
        self.assertEqual(e.dia.value(),15)
        self.assertEqual(fechamento.estado()['versao'],0)
        e.carregar();self.esperar(j.nuvem)
        self.assertEqual(e.config['versao'],1)
        self.assertEqual(e.dia.value(),15)
        self.salvar(j,e)
        self.assertEqual(e.config,{'versao':2,'historico':[{'vigencia':'2090-11-01','dia':15}]})

    def test_nao_insere_regra_antes_da_mais_recente_e_permite_revisar_futura(self):
        j = self.janela(); self.conectar(j)
        e = self.editor(j);self.futuro(e,15);self.salvar(j,e)
        self.futuro(e,20,2091,3);self.salvar(j,e)
        self.futuro(e,10,2090,12)
        self.assertIn('mais recente',e.erro.text())
        self.assertFalse(e.salvar.isEnabled())
        self.futuro(e,23,2091,3);self.salvar(j,e)
        self.assertEqual(e.config['historico'],[{'vigencia':'2090-11-01','dia':15},{'vigencia':'2091-03-01','dia':23}])
        self.assertEqual(e.config['versao'],3)

    def test_backup_local_com_falha_exige_reconciliar_regra_confirmada(self):
        j = self.janela();self.conectar(j)
        e = self.editor(j);self.futuro(e)
        with patch('ProgramFeira.database.armazenamento.criar_backup',side_effect=OSError('Sem acesso')):
            self.salvar(j,e)
        self.assertIn('confirmou a regra',j.nuvem.status)
        self.assertEqual(fechamento.estado()['versao'],0)
        self.assertFalse(e.conferida)
        e.carregar();self.esperar(j.nuvem)
        self.assertEqual(fechamento.estado()['versao'],1)
        self.assertTrue(e.conferida)

    def test_servico_indisponivel_preserva_regra_e_pede_nova_consulta(self):
        j = self.janela();self.conectar(j)
        e = self.editor(j);self.futuro(e)
        j.nuvem.cliente.indisponivel = True
        self.salvar(j,e)
        self.assertFalse(e.conferida)
        self.assertEqual(fechamento.estado()['versao'],0)
        self.assertIn('indisponível',j.nuvem.status)
        j.nuvem.cliente.indisponivel = False
        e.carregar();self.esperar(j.nuvem)
        self.assertTrue(e.conferida)

    def test_regra_externa_recebida_atualiza_cache_sem_aplicar_filtro_pendente(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j = self.janela();n = self.vincular(j)
        j.mes.setCurrentIndex(9)
        consulta = j.consulta
        n.cliente.salvar_fechamento(n.sessao,0,'2090-11-01',15)
        n.agendador._disparar();self.esperar(n)
        self.assertEqual(fechamento.estado()['versao'],1)
        self.assertEqual(j.consulta,consulta)
        self.assertEqual(j.mes.currentIndex(),9)
        self.assertIn('Regra de fechamento recebida',n.status)
        self.assertTrue(list((self.pasta/'backups').glob('*antes-alterar-fechamento*.db')))
