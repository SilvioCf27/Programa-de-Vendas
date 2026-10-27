"""Equivalência financeira e formulários Qt em SQLite temporário, sem nuvem."""
import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'prototipos/reforma'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6 import QtCore as Q, QtWidgets as W
from reforma_desktop.aplicacao import preparar_interface as preparar
from ProgramFeira import financeiro as f, fechamento
from ProgramFeira.database import banco
from reforma_desktop.aplicacao import Janela
from reforma_desktop.vendas import ServicoVendas
from reforma_desktop.financas import ServicoFinanceiro, ConsultaFinanceira
from reforma_desktop.campos_financeiros import SeletorFinanceiro
from reforma_desktop.formularios_financeiros import FormularioLancamento, FormularioTaxas, FormularioAnual


class FinancasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = preparar()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.pasta = Path(temp.name)
        p = patch.object(banco, 'CAMINHO_BANCO', self.pasta / 'vendas.db')
        p.start()
        self.addCleanup(p.stop)
        self.vendas = ServicoVendas(lambda: date(2026, 10, 27))
        self.servico = ServicoFinanceiro()
        self.addCleanup(fechamento.definir, {'versao': 0, 'historico': []})
        self.callback = []

    def mudou(self):
        self.callback.append(True)

    def salvar(self, data='2026-10-23', valor='100', descricao='Despesa de teste', meio='Dinheiro', parcelas=1, compra=None):
        self.servico.salvar_compra('despesa', data, descricao, valor, meio, 'Outros', parcelas, data_compra=compra)
        return next(r for r in self.todos() if r['descricao'] == descricao)

    def todos(self):
        return f.listar_lancamentos('1900-01-01', '9998-12-31')

    def janela(self):
        j = Janela(self.vendas, self.pasta)
        self.addCleanup(j.deleteLater)
        self.addCleanup(j.close)
        j.show()
        j.mostrar('Finanças')
        self.app.processEvents()
        return j, j.financas

    def form(self, registro=None):
        form = FormularioLancamento(self.servico, self.mudou, date(2026, 10, 27), registro)
        self.addCleanup(form.deleteLater)
        return form

    def taxas(self):
        form = FormularioTaxas(self.servico, self.mudou, date(2026, 10, 25))
        self.addCleanup(form.deleteLater)
        return form

    def anual(self, registro=None):
        form = FormularioAnual(self.servico, self.mudou, date(2026, 10, 27), registro)
        self.addCleanup(form.deleteLater)
        return form

    def test_resumo_equivale_ao_nucleo_com_faturas_futuras(self):
        self.vendas.salvar('2026-10-23', '500', '0', '0')
        self.salvar(valor='180', meio='Cartão de crédito', parcelas=3, compra='2026-10-09')
        self.salvar(valor='75,50', descricao='À vista')
        f.salvar_lancamento('taxa', '2026-10-23', 'Taxa', '2,30')
        c = ConsultaFinanceira('Fechamento', date(2026, 10, 1))
        r = self.servico.consultar(c)
        self.assertEqual(r['resumo'], f.resumo_periodo(*c.limites()))
        self.assertEqual(r['resumo']['despesas'], Decimal('135.50'))
        self.assertEqual(r['resumo']['saldo'], Decimal('362.20'))
        self.assertEqual(sum(v for _, v in r['semanas']), 13550)

    def test_seletor_semana_mes_ano_fechamento_e_vigencia(self):
        seletor = SeletorFinanceiro(date(2026, 1, 2), 'Semana')
        self.addCleanup(seletor.deleteLater)
        self.assertEqual(seletor.consulta().limites(), ('2025-12-29', '2026-01-04'))
        seletor.tipo.setCurrentText('Ano')
        self.assertEqual(seletor.consulta().limites(), ('2026-01-01', '2026-12-31'))
        self.assertTrue(seletor.mes.isHidden())
        seletor.tipo.setCurrentText('Mês')
        seletor.ano.setValue(2024)
        seletor.mes.setCurrentIndex(1)
        self.assertEqual(seletor.consulta().limites(), ('2024-02-01', '2024-02-29'))
        fechamento.definir({'versao': 1, 'historico': [{'vigencia': '2026-11-01', 'dia': 14}]})
        self.assertEqual(ConsultaFinanceira('Fechamento', date(2026, 11, 1)).limites(), ('2026-11-15', '2026-12-14'))
        self.assertEqual(ConsultaFinanceira('Fechamento', date(2026, 9, 1)).limites(), ('2026-09-10', '2026-10-09'))

    def test_compra_no_dia_09_primeira_fatura_seguinte_e_soma_exata(self):
        form = self.form()
        form.data.setDate(Q.QDate(2026, 10, 9))
        form.descricao.setText('Compra no fechamento')
        form.meio.setCurrentText('Cartão de crédito')
        form.parcelas.setValue(3)
        form.valor.setText('100,01')
        self.assertIn('09/11/2026', form.previa.text())
        with patch.object(form, 'confirmar', return_value=True):
            form.gravar()
        rows = sorted(self.todos(), key=lambda r: r['parcela'])
        self.assertEqual([r['data'] for r in rows], ['2026-11-09', '2026-12-09', '2027-01-09'])
        self.assertEqual([r['valor_centavos'] for r in rows], [3333, 3334, 3334])
        self.assertTrue(all(r['data_compra'] == '2026-10-09' for r in rows))
        self.assertEqual(self.callback, [True])

    def test_data_da_compra_nao_muda_ao_preencher_outros_campos(self):
        form = self.form()
        form.data.setDate(Q.QDate(2026, 5, 9))
        form.descricao.setText('Compra em maio')
        form.meio.setCurrentText('Cartão de crédito')
        form.valor.setText('150')
        form.parcelas.setValue(5)
        form.categoria.setCurrentText('Feira')
        self.assertEqual(form.data.date().toPython(), date(2026, 5, 9))
        with patch.object(form, 'confirmar', return_value=True):
            form.gravar()
        self.assertEqual(sorted(r['data'] for r in self.todos()), ['2026-06-09', '2026-07-09', '2026-08-09', '2026-09-09', '2026-10-09'])
        self.assertTrue(all(r['valor_centavos'] == 3000 for r in self.todos()))

    def test_editar_quarta_parcela_altera_compra_inteira(self):
        r = self.salvar('2026-05-09', '100', meio='Cartão de crédito', parcelas=5)
        quarta = next(v for v in self.todos() if v['parcela'] == 4)
        form = self.form(quarta)
        self.assertEqual(form.valor.text(), '100,00')
        self.assertEqual(form.data.date().toPython(), date(2026, 5, 9))
        form.valor.setText('150,01')
        with patch.object(form, 'confirmar', return_value=True):
            form.gravar()
        compra = self.servico.compra(r['id'])
        self.assertEqual([v['valor_centavos'] for v in compra['registros']], [3000, 3000, 3000, 3000, 3001])
        self.assertEqual(compra['data'], '2026-05-09')
        self.assertIsNone(compra['data_compra'])

    def test_legado_exige_data_original_antes_de_reclassificar(self):
        r = self.salvar('2026-10-09', '90', meio='Cartão de crédito', parcelas=3)
        form = self.form(r)
        form.origem.setCurrentIndex(1)
        form.gravar()
        self.assertIn('data original', form.erro.text())
        self.assertEqual(self.callback, [])
        form.data.setDate(Q.QDate(2026, 9, 9))
        with patch.object(form, 'confirmar', return_value=True):
            form.gravar()
        compra = self.servico.compra(r['id'])
        self.assertEqual(compra['data_compra'], '2026-09-09')
        self.assertEqual([v['data'] for v in compra['registros']], ['2026-10-09', '2026-11-09', '2026-12-09'])

    def test_cancelar_ou_recusar_confirmacao_nao_grava(self):
        form = self.form()
        form.valor.setText('100')
        form.descricao.setText('Não salvar')
        form.meio.setCurrentText('Cartão de crédito')
        form.parcelas.setValue(3)
        with patch.object(form, 'confirmar', return_value=False):
            form.gravar()
        self.assertEqual(self.todos(), [])
        self.assertTrue(form.salvar.isEnabled())
        form.reject()
        self.assertEqual(self.callback, [])

    def test_compra_alterada_ou_incompleta_nao_e_sobrescrita(self):
        r = self.salvar(valor='90', meio='Cartão de crédito', parcelas=3)
        form = self.form(r)
        f.salvar_lancamento('despesa', '2026-10-23', 'Outro total', '120', 'Cartão de crédito', parcelas=3, identificador=r['id'])
        with patch.object(form, 'confirmar', return_value=True):
            form.gravar()
        self.assertIn('mudou', form.erro.text())
        self.assertEqual(self.servico.compra(r['id'])['valor_centavos'], 12000)
        rows = self.todos()
        self.servico.excluir([rows[0]])
        with self.assertRaisesRegex(ValueError, 'incompleto'):
            self.servico.compra(rows[1]['id'])

    def test_lote_financeiro_atomico_com_conflito(self):
        self.salvar(descricao='A')
        self.salvar(descricao='B')
        esperado = self.todos()
        f.salvar_lancamento('despesa', '2026-10-23', 'B alterada', '110', identificador=esperado[1]['id'])
        with self.assertRaisesRegex(ValueError, 'mudou'):
            self.servico.excluir(esperado)
        self.assertEqual(len(self.todos()), 2)
        self.servico.excluir(self.todos())
        self.assertEqual(self.todos(), [])

    def test_falha_backup_impede_compra_taxa_historico_e_exclusoes(self):
        r = self.salvar()
        semana = self.servico.semana_taxas('2026-10-19')
        self.servico.salvar_anual(2025, '2025-01-01', '2025-12-31', '200', 'Estimada', '')
        anual = f.listar_taxas_anuais()[0]
        with patch.object(banco, 'criar_backup', side_effect=OSError('Backup indisponível')):
            for acao in [lambda: self.salvar(descricao='Não gravar'), lambda: self.servico.excluir([r]), lambda: self.servico.salvar_taxas('2026-10-19', {'2026-10-23': '3'}, semana), lambda: self.servico.salvar_anual(2026, '2026-01-01', '2026-10-20', '10', 'Confirmada', ''), lambda: self.servico.excluir_anual(anual)]:
                with self.assertRaises(OSError):
                    acao()
        self.assertEqual(len(self.todos()), 1)
        self.assertEqual(f.listar_taxas_anuais(), [anual])

    def test_taxas_sexta_domingo_vazio_mantem_zero_nao_exclui(self):
        semana = self.servico.semana_taxas('2026-10-19')
        self.servico.salvar_taxas('2026-10-19', {'2026-10-23': '2,30', '2026-10-25': '3,70'}, semana)
        self.assertEqual(sum(v['valor_centavos'] for v in self.todos()), 600)
        semana = self.servico.semana_taxas('2026-10-19')
        self.servico.salvar_taxas('2026-10-19', {'2026-10-23': '', '2026-10-25': '4'}, semana)
        self.assertEqual(sum(v['valor_centavos'] for v in self.todos()), 630)
        with self.assertRaises(ValueError):
            self.servico.salvar_taxas('2026-10-19', {'2026-10-25': '0'}, self.servico.semana_taxas('2026-10-19'))
        self.assertEqual(sum(v['valor_centavos'] for v in self.todos()), 630)

    def test_taxas_semana_nao_movem_campos_para_outras_datas(self):
        form = self.taxas()
        self.assertEqual(form.intervalo, ('2026-10-19', '2026-10-25'))
        form.campos['2026-10-23'].setText('2,30')
        form.seletor.semana.setCurrentIndex(0)
        form.gravar()
        self.assertIn('Carregue', form.erro.text())
        self.assertEqual(self.todos(), [])
        with patch.object(form, 'confirmar', return_value=False):
            form.carregar()
        self.assertEqual(form.campos['2026-10-23'].text(), '2,30')
        with patch.object(form, 'confirmar', return_value=True):
            form.carregar()
        self.assertNotIn('2026-10-23', form.campos)
        self.assertEqual(self.todos(), [])

    def test_historico_e_taxas_por_data_nao_sobrepoem(self):
        self.servico.salvar_anual(2025, '2025-01-01', '2025-12-31', '200', 'Confirmada', 'Extrato')
        semana = self.servico.semana_taxas('2025-10-20')
        with self.assertRaises(ValueError):
            self.servico.salvar_taxas('2025-10-20', {'2025-10-24': '3'}, semana)
        self.assertEqual(self.todos(), [])
        f.salvar_taxas_semana('2026-10-19', {'2026-10-23': '2'})
        with self.assertRaises(ValueError):
            self.servico.salvar_anual(2026, '2026-01-01', '2026-12-31', '100', 'Confirmada', '')
        self.assertEqual(len(f.listar_taxas_anuais()), 1)

    def test_semana_coberta_por_historico_nao_tem_campos_editaveis(self):
        self.servico.salvar_anual(2026, '2026-01-01', '2026-12-31', '200', 'Confirmada', '')
        form = self.taxas()
        self.assertEqual(form.campos, {})
        self.assertFalse(form.salvar.isEnabled())

    def test_historico_novo_nao_sobrescreve_ano_sem_abrir_edicao(self):
        self.servico.salvar_anual(2025, '2025-01-01', '2025-12-31', '100', 'Estimada', 'Base')
        antes = f.listar_taxas_anuais()[0]
        with self.assertRaises(ValueError):
            self.servico.salvar_anual(2025, '2025-01-01', '2025-12-31', '200', 'Confirmada', '')
        form = self.anual(antes)
        self.assertTrue(form.ano.isReadOnly())
        form.valor.setText('150')
        form.gravar()
        self.assertEqual(f.listar_taxas_anuais()[0]['valor_centavos'], 15000)
        with self.assertRaises(ValueError):
            self.servico.excluir_anual(antes)
        self.servico.excluir_anual(f.listar_taxas_anuais()[0])
        self.assertEqual(f.listar_taxas_anuais(), [])

    def test_historico_parcial_sem_rateio_e_estimativa_visivel(self):
        self.vendas.salvar('2026-10-23', '500', '0', '0')
        self.servico.salvar_anual(2026, '2026-01-01', '2026-12-31', '200', 'Estimada', '')
        j, p = self.janela()
        self.assertEqual(p.resultado['resumo']['taxas'], 0)
        self.assertIn('saldo provisório', p.aviso.text())
        self.assertIn('estimadas', p.aviso.text())
        p.seletor.tipo.setCurrentText('Ano')
        p.consultar()
        self.assertEqual(p.resultado['resumo']['taxas'], 200)
        self.assertEqual(p.resultado['resumo']['saldo'], 300)

    def test_financas_independe_de_vendas_pendente_e_recorte_de_lista(self):
        self.salvar()
        f.salvar_taxas_semana('2026-10-19', {'2026-10-23': '2'})
        j, p = self.janela()
        saldo = p.resultado['resumo']['saldo']
        j.mes.setCurrentIndex(9)
        j.aplicar()
        self.assertEqual(p.resultado['resumo']['saldo'], saldo)
        p.seletor.mes.setCurrentIndex(8)
        self.assertTrue(p.pendente.text())
        p.aplicar_recorte(2)
        self.assertEqual(len(p.tabela.linhas), 1)
        self.assertEqual(p.resultado['resumo']['saldo'], saldo)
        self.salvar(descricao='Outra despesa')
        p.ao_alterar()
        self.assertEqual(p.consulta.referencia.month, 10)
        self.assertEqual(p.seletor.mes.currentIndex(), 8)
        self.assertEqual(p.resultado['resumo']['despesas'], 200)

    def test_paginacao_lote_confirmado_e_totais_completos(self):
        for n in range(16):
            self.salvar(valor='10', descricao=f'Despesa {n}')
        j, p = self.janela()
        self.assertEqual(p.resultado['resumo']['despesas'], 160)
        p.tabela.todos.setChecked(True)
        ids = p.tabela.selecionados()
        self.assertEqual(len(ids), 10)
        with patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.No):
            p.excluir(ids)
        self.assertEqual(len(self.todos()), 16)
        with patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.Yes):
            p.excluir(ids)
        self.assertEqual(len(self.todos()), 6)
        self.assertEqual(p.resultado['resumo']['despesas'], 60)
        self.assertEqual(p.tabela.selecionados(), [])

    def test_despesas_por_semana_usa_todas_as_linhas_sem_taxas(self):
        self.salvar(valor='100')
        f.salvar_taxas_semana('2026-10-19', {'2026-10-23': '10'})
        j, p = self.janela()
        p.aplicar_recorte(2)
        d = p.despesas_semanas()
        self.assertEqual(sum(r[3] for r in d.modelo.linhas), 10000)
        self.assertEqual(sum(r[2] for r in d.modelo.linhas), 1)
        d.close()

    def test_historico_modal_crud_e_regra_somente_leitura(self):
        self.servico.salvar_anual(2025, '2025-01-01', '2025-12-31', '200', 'Estimada', 'Exemplo')
        j, p = self.janela()
        h = p.historico_taxas()
        self.assertEqual(h.tabela.rowCount(), 1)
        h.tabela.selectRow(0)
        form = h.editar_atual()
        self.assertEqual(form.valor.text(), '200,00')
        form.reject()
        h.close()
        antes = fechamento.estado()
        d = p.regra_fechamento()
        self.assertIsNone(d.modelo)
        d.close()
        self.assertEqual(fechamento.estado(), antes)
        self.assertNotIn('ProgramFeira.interface.painel_financeiro', sys.modules)

    def test_retorno_sem_mudanca_nao_consulta_e_ha_um_timer(self):
        j, p = self.janela()
        with patch.object(p.servico, 'consultar', side_effect=AssertionError('Consultou ao navegar')):
            for _ in range(5):
                j.mostrar('Vendas')
                j.mostrar('Análises')
                j.mostrar('Finanças')
        self.assertEqual(len(j.findChildren(Q.QTimer)), 1)
        self.assertIs(j.financas, p)
        self.assertEqual(j.nova.text(), 'Nova despesa')

    def test_janela_estreita_e_formularios_acessiveis(self):
        j, p = self.janela()
        for largura, altura in [(1000, 700), (1536, 1024)]:
            j.resize(largura, altura)
            for _ in range(8):
                self.app.processEvents()
            self.assertEqual(p.horizontalScrollBar().maximum(), 0)
            self.assertLessEqual(p.corpo.width(), p.viewport().width())
        form = p.abrir_taxas()
        self.app.processEvents()
        self.assertFalse(form.seletor.ano.isHidden())
        self.assertEqual(len(form.campos), 7)
        form.reject()

    def test_ano_incompleto_nao_aplica_consulta_anterior_silenciosamente(self):
        j, p = self.janela()
        antes = p.resultado
        p.seletor.ano.lineEdit().setText('20')
        p.consultar()
        self.assertIs(p.resultado, antes)
        self.assertIn('ano', p.pendente.text())
