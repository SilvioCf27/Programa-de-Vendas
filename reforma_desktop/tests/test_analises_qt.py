"""Equivalência de Análises com o núcleo; somente SQLite temporário e Qt offscreen."""
import os
import sys
import tempfile
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'prototipos/reforma'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6 import QtCore as Q
from noturno_demo import preparar
from reforma_desktop.aplicacao import Janela
from reforma_desktop.vendas import ServicoVendas, Consulta
from reforma_desktop.analises import analisar, Periodo, comparar, analisar_evolucao, centavos
from ProgramFeira.database import banco
from ProgramFeira import fechamento
from ProgramFeira.resumos import calcular_indicadores
from ProgramFeira.semanas import agrupar_semanas
from ProgramFeira.tendencias import evolucao


class AnalisesTests(unittest.TestCase):
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
        self.servico = ServicoVendas(lambda: date(2026, 10, 27))
        self.addCleanup(fechamento.definir, {'versao': 0, 'historico': []})

    def venda(self, data, valor='60'):
        self.servico.salvar(data, valor, '0', '0')

    def janela(self):
        j = Janela(self.servico, self.pasta)
        self.addCleanup(j.deleteLater)
        self.addCleanup(j.close)
        j.show()
        self.app.processEvents()
        return j

    def abrir(self, j):
        j.mostrar('Análises')
        self.app.processEvents()
        return j.analises

    def periodo(self, tipo='Mês', ano=2026, mes=10, inicio=date(2026, 10, 1), fim=date(2026, 10, 31)):
        return Periodo(tipo, ano, mes, inicio, fim)

    def test_semanas_indicadores_e_pagamentos_equivalem_ao_nucleo(self):
        self.venda('2026-10-23', '100,01')
        self.venda('2026-10-25', '0')
        self.servico.salvar('2026-10-26', '10', '20,20', '30,30')
        linhas = banco.listar_vendas()
        s = analisar(linhas, Consulta())
        self.assertEqual(s['indicadores'], calcular_indicadores(linhas))
        for g, base in zip(s['semanas'], agrupar_semanas(linhas)):
            self.assertEqual({k: g[k] for k in base}, base)
            self.assertEqual(sum(g['pagamentos']), g['total'])
        self.assertEqual(s['pagamentos'], (Decimal('110.01'), Decimal('20.2'), Decimal('30.3')))
        self.assertEqual(s['dias'][6][1]['quantidade'], 1)
        self.assertEqual(s['dias'][6][1]['total'], 0)
        self.assertEqual(s['dias'][5][1]['quantidade'], 0)

    def test_recortes_por_borda_e_dias_da_semana(self):
        self.venda('2026-10-31', '0')
        linhas = banco.listar_vendas()
        self.assertTrue(analisar(linhas, Consulta(2026, 10))['semanas'][0]['parcial'])
        self.assertFalse(analisar(linhas, Consulta())['semanas'][0]['parcial'])
        self.assertTrue(analisar(linhas, Consulta(dias=(5,)))['semanas'][0]['parcial'])
        self.assertFalse(analisar(linhas, Consulta(dias=tuple(range(7))))['semanas'][0]['parcial'])

    def test_periodos_comparacao_datas_intervalo_mes_e_vigencia(self):
        self.assertEqual(self.periodo('Data', inicio=date(2024, 2, 29)).limites(), ('2024-02-29', '2024-02-29'))
        self.assertEqual(self.periodo('Mês', 2024, 2).limites(), ('2024-02-01', '2024-02-29'))
        self.assertEqual(self.periodo('Fechamento', 2026, 12).limites(), ('2026-12-10', '2027-01-09'))
        fechamento.definir({'versao': 1, 'historico': [{'vigencia': '2026-11-01', 'dia': 14}]})
        self.assertEqual(self.periodo('Fechamento', 2026, 9).limites(), ('2026-09-10', '2026-10-09'))
        self.assertEqual(self.periodo('Fechamento', 2026, 11).limites(), ('2026-11-15', '2026-12-14'))
        a = self.periodo()
        b = self.periodo('Intervalo', inicio=date(2026, 10, 20), fim=date(2026, 10, 1))
        with patch.object(banco, 'listar_vendas', side_effect=AssertionError('Consultou antes de validar os dois')):
            with self.assertRaises(ValueError):
                comparar(a, b)

    def test_comparacao_b_menos_a_zero_e_sem_registros(self):
        self.venda('2026-09-25', '100')
        self.venda('2026-10-23', '150')
        r = comparar(self.periodo(mes=9), self.periodo())
        self.assertEqual((r['diferenca'], r['variacao']), (Decimal(50), Decimal(50)))
        self.assertEqual(comparar(self.periodo(), self.periodo())['diferenca'], 0)
        self.venda('2026-08-23', '0')
        zero = comparar(self.periodo(mes=8), self.periodo())
        self.assertIsNone(zero['variacao'])
        self.assertIn('zero', zero['motivo'])
        vazio = comparar(self.periodo(mes=7), self.periodo())
        self.assertIn('Sem registros', vazio['motivo'])

    def test_evolucao_consecutiva_distinge_ausencia_e_zero_e_limita_12(self):
        for dia, valor in [('2025-01-01', '999'), ('2026-01-23', '0'), ('2026-03-20', '100')]:
            self.venda(dia, valor)
        s = analisar(banco.listar_vendas(), Consulta())
        grupos = analisar_evolucao(s, 'Mês')
        self.assertEqual(grupos, evolucao(banco.listar_vendas()))
        self.assertEqual(len(grupos), 12)
        jan = next(g for g in grupos if g['rotulo'] == '01/2026')
        fev = next(g for g in grupos if g['rotulo'] == '02/2026')
        self.assertEqual((jan['quantidade'], jan['total']), (1, 0))
        self.assertEqual((fev['quantidade'], fev['total']), (0, 0))
        self.assertEqual(centavos(Decimal('1.005')), 101)
        self.assertEqual(centavos(Decimal('0.004')), 0)
        fechamento.definir({'versao': 1, 'historico': [{'vigencia': '2026-02-01', 'dia': 14}]})
        self.assertEqual(analisar_evolucao(s, 'Fechamento'), evolucao(s['linhas'], 'Fechamento'))

    def test_tela_so_e_criada_na_primeira_visita_e_retorno_nao_consulta(self):
        j = self.janela()
        self.assertIsNone(j.analises)
        p = self.abrir(j)
        with patch('reforma_desktop.painel_analises.analisar', side_effect=AssertionError('Reconstruiu snapshot sem mudança')), patch.object(banco, 'listar_vendas', side_effect=AssertionError('Consultou ao navegar')):
            for _ in range(5):
                j.mostrar('Vendas')
                j.mostrar('Análises')
        self.assertIs(j.analises, p)
        self.assertEqual(len(j.findChildren(Q.QTimer)), 1)

    def test_analises_usa_consulta_aplicada_e_avisa_filtro_pendente(self):
        self.venda('2026-09-25', '100')
        self.venda('2026-10-23', '150')
        j = self.janela()
        p = self.abrir(j)
        snapshot = p.snapshot
        j.mes.setCurrentIndex(9)
        self.assertTrue(p.aviso_vendas.text())
        self.assertIs(p.snapshot, snapshot)
        self.assertEqual(p.snapshot['indicadores']['total'], 150)
        j.aplicar()
        self.assertEqual(p.snapshot['indicadores']['total'], 100)
        self.assertEqual(p.aviso_vendas.text(), '')

    def test_busca_e_paginacao_nao_recortam_semanas_ou_detalhes(self):
        for dia in range(10, 26):
            self.venda(f'2026-10-{dia:02}')
        j = self.janela()
        j.tabela.mover(1)
        j.busca.setText('23/10/2026')
        p = self.abrir(j)
        self.assertEqual(p.snapshot['indicadores']['quantidade'], 16)
        d = p.criar_detalhe('vendas')
        self.addCleanup(d.deleteLater)
        self.assertEqual(d.modelo.rowCount(), 16)
        self.assertEqual(sum(g['quantidade'] for g in p.snapshot['semanas']), 16)

    def test_ab_independe_de_vendas_e_preserva_ultimo_resultado_se_invalido(self):
        self.venda('2026-09-25', '100')
        self.venda('2026-10-23', '150')
        j = self.janela()
        j.dias[0].setChecked(True)
        j.aplicar()
        p = self.abrir(j)
        p.comparar()
        self.assertEqual(p.ultima_comparacao['diferenca'], 50)
        self.assertEqual(p.snapshot['indicadores']['quantidade'], 0)
        antes = p.ultima_comparacao
        p.b.tipo.setCurrentText('Intervalo')
        p.b.inicio.setDate(Q.QDate(2026, 10, 31))
        p.b.fim.setDate(Q.QDate(2026, 10, 1))
        p.comparar()
        self.assertIs(p.ultima_comparacao, antes)
        self.assertIn('Não atualizado', p.aviso.text())
        self.assertEqual(j.consulta.dias, (0,))

    def test_alteracao_de_venda_invalida_oculta_e_atualiza_ab_aplicado(self):
        self.venda('2026-09-25', '100')
        self.venda('2026-10-23', '150')
        j = self.janela()
        p = self.abrir(j)
        p.comparar()
        p.b.mes.setCurrentIndex(7)  # Agosto pendente; não deve substituir Outubro aplicado.
        j.mostrar('Vendas')
        venda = banco.buscar_venda_por_data('2026-10-23')
        self.servico.salvar(venda[1], '200', '0', '0', venda)
        j.atualizar()
        self.assertTrue(p.sujo)
        self.assertEqual(p.ultima_comparacao['b']['total'], 150)
        j.mostrar('Análises')
        self.assertFalse(p.sujo)
        self.assertEqual(p.snapshot['indicadores']['total'], 200)
        self.assertEqual(p.ultima_comparacao['b']['total'], 200)
        self.assertEqual(p.b.mes.currentIndex(), 7)
        self.assertIn('Seleção alterada', p.aviso.text())
        d = p.detalhes_comparacao()
        self.assertEqual(d.modelo.linhas[0], ('Total registrado', 'R$ 100,00', 'R$ 200,00'))
        d.close()

    def test_seletores_adaptam_datas_e_mes_sem_reiniciar_valores(self):
        p = self.abrir(self.janela())
        p.a.tipo.setCurrentText('Intervalo')
        p.a.inicio.setDate(Q.QDate(2026, 5, 3))
        p.a.fim.setDate(Q.QDate(2026, 5, 10))
        self.assertFalse(p.a.datas.isHidden())
        self.assertTrue(p.a.meses.isHidden())
        p.a.tipo.setCurrentText('Mês')
        self.assertFalse(p.a.meses.isHidden())
        p.a.tipo.setCurrentText('Intervalo')
        self.assertEqual(p.a.periodo().limites(), ('2026-05-03', '2026-05-10'))
        p.a.tipo.setCurrentText('Data')
        self.assertTrue(p.a.fim.isHidden())
        self.assertEqual(p.a.periodo().limites(), ('2026-05-03', '2026-05-03'))

    def test_janelas_dias_pagamentos_evolucao_e_vazio(self):
        p = self.abrir(self.janela())
        for modo, quantidade in [('dias', 7), ('pagamentos', 3), ('vendas', 0)]:
            d = p.criar_detalhe(modo)
            self.addCleanup(d.deleteLater)
            self.assertEqual(len(d.dias_dados) if modo == 'dias' else d.modelo.rowCount() if d.modelo else 0, quantidade)
        e = p.criar_evolucao('Fechamento')
        self.addCleanup(e.deleteLater)
        self.assertIsNone(e.modelo)
        p.controlador.mostrar('Vendas')
        self.venda('2026-10-23', '0')
        p.controlador.atualizar()
        p.controlador.mostrar('Análises')
        d = p.criar_detalhe('dias')
        self.addCleanup(d.deleteLater)
        self.assertEqual(d.dias_dados[4][1:], (0, 1))
        self.assertIn('Média por dia registrado', d.barras[4].toolTip())
        e = p.criar_evolucao('Mês')
        self.addCleanup(e.deleteLater)
        self.assertEqual(e.modelo.linhas[0][1:], (1, 0, 'Com registros'))
        self.assertIsInstance(e.modelo.linhas[0][0], date)

    def test_novo_ano_disponivel_sem_aplicar_selecao_pendente(self):
        j = self.janela()
        p = self.abrir(j)
        self.venda('2040-01-06')
        j.atualizar()
        self.assertGreaterEqual(p.a.ano.findText('2040'), 0)
        self.assertEqual(p.a.ano.currentText(), '2026')

    def test_janela_estreita_detalhes_e_volta_preservam_dados(self):
        self.venda('2026-10-23')
        j = self.janela()
        p = self.abrir(j)
        s = p.snapshot
        for largura, altura in [(1000, 700), (1536, 1024)]:
            j.resize(largura, altura)
            for _ in range(8):
                self.app.processEvents()
            self.assertEqual(p.horizontalScrollBar().maximum(), 0)
            self.assertLessEqual(p.corpo.width(), p.viewport().width())
            self.assertIs(p.snapshot, s)
        self.assertNotIn('ProgramFeira.main', sys.modules)
        self.assertNotIn('ProgramFeira.interface.analises', sys.modules)
