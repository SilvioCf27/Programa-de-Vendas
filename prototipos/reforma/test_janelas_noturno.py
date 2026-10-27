"""Regressões das janelas de leitura da demo, sem contas ou banco de produção."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from PySide6 import QtCore as Q, QtWidgets as W, QtTest
from noturno_demo import preparar, Aplicativo
from estado_demo import Venda, limites
from janelas_noturno import janela_texto, ModeloDetalhe, Coluna


class JanelasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = preparar()

    def setUp(self):
        self.erros = []
        self.hook = sys.excepthook
        sys.excepthook = lambda *a: self.erros.append(a)
        self.w = Aplicativo()
        self.w.show()
        self.app.processEvents()
        self.janelas = []

    def tearDown(self):
        for d in self.janelas:
            d.close()
            d.deleteLater()
        self.w.close()
        self.w.deleteLater()
        self.app.processEvents()
        sys.excepthook = self.hook
        self.assertFalse(self.erros, self.erros)

    def detalhe(self, nome):
        d = self.w.criar_detalhe(nome)
        self.janelas.append(d)
        d.show()
        for _ in range(6):
            self.app.processEvents()
        self.assertLessEqual(d.corpo.width(), d.scroll.viewport().width(), nome)
        return d

    def test_consulta_completa_independe_da_pagina_e_do_filtro_pendente(self):
        self.w.tabela_vendas.tamanho.setCurrentText("5")
        self.w.seletor_vendas.mes.setCurrentIndex(8)
        source = self.w.estado.consultar_vendas(self.w.intervalo_vendas, self.w.dias)
        ids = [r.id for r in source]
        d = self.detalhe("vendas")
        self.assertEqual(d.modelo.rowCount(), 6)
        self.assertEqual([r[0] for r in d.modelo.linhas], ids)
        self.assertEqual(sum(row[-1] for row in d.modelo.linhas), 200650)
        d.modelo.sort(6, Q.Qt.SortOrder.AscendingOrder)
        self.assertEqual(
            [row[-1] for row in d.modelo.linhas], sorted(r.total for r in source)
        )
        self.assertEqual(
            [
                r.id
                for r in self.w.estado.consultar_vendas(
                    self.w.intervalo_vendas, self.w.dias
                )
            ],
            ids,
        )
        idx = d.modelo.index(0, 6)
        self.assertFalse(d.modelo.flags(idx) & Q.Qt.ItemFlag.ItemIsEditable)
        self.assertFalse(d.modelo.setData(idx, 999))
        self.assertTrue(self.w.pendente.text())

    def test_sete_dias_zero_sem_barra_e_registro_zerado_conta(self):
        d = self.detalhe("dias")
        self.assertEqual(len(d.barras), 7)
        self.assertEqual(d.dias_dados[4], ("Sexta-feira", 68650, 3))
        self.assertEqual(d.dias_dados[6], ("Domingo", 132000, 3))
        for i in (0, 1, 2, 3, 5):
            self.assertEqual(d.barras[i].value(), 0)
        self.w.estado.vendas = [Venda(1, date(2026, 10, 16), 0, 0, 0)]
        vazio = self.detalhe("dias")
        self.assertEqual(vazio.dias_dados[4][2], 1)
        self.assertTrue(all(b.value() == 0 for b in vazio.barras))

    def test_despesas_preservam_soma_recorte_e_exclusao_das_taxas(self):
        self.w.intervalo_financas = limites("Semana", 2026, 10, 3)
        d = self.detalhe("despesas")
        self.assertEqual(sum(row[3] for row in d.modelo.linhas), 23740)
        self.assertEqual(sum(row[2] for row in d.modelo.linhas), 3)
        self.assertEqual(self.w.intervalo_vendas, limites("Fechamento"))
        self.assertEqual(
            d.modelo.linhas[0][:2], (date(2026, 10, 19), date(2026, 10, 25))
        )

    def test_semana_vazia_compacta_e_semana_com_vendas_independente(self):
        d = self.detalhe("semana")
        self.assertIsNone(d.tabela)
        self.assertLessEqual(d.height(), 360)
        self.w.dias = set()  # Consulta de Vendas sem dias não limita a semana atual.
        with patch("noturno_demo.HOJE", date(2026, 10, 25)):
            cheio = self.detalhe("semana")
        self.assertEqual(cheio.modelo.rowCount(), 2)
        self.assertEqual(sum(row[-1] for row in cheio.modelo.linhas), 89200)
        self.assertTrue(
            all(
                date(2026, 10, 19) <= row[1] <= date(2026, 10, 25)
                for row in cheio.modelo.linhas
            )
        )

    def test_escape_retorna_sem_perder_selecao_ou_consulta_pendente(self):
        t = self.w.tabela_vendas
        next(iter(t.checks.values())).setChecked(True)
        ids = t.selecionados()
        self.w.seletor_vendas.mes.setCurrentIndex(8)
        d = self.detalhe("vendas")
        d.tabela.setFocus()
        QtTest.QTest.keyClick(d.tabela, Q.Qt.Key.Key_Tab)
        self.assertIsNotNone(self.app.focusWidget())
        QtTest.QTest.keyClick(d, Q.Qt.Key.Key_Escape)
        self.assertFalse(d.isVisible())
        self.assertEqual(t.selecionados(), ids)
        self.assertTrue(self.w.pendente.text())
        self.assertEqual(self.w.intervalo_vendas, limites("Fechamento"))

    def test_muitos_registros_valores_altos_e_ordenacao_numerica(self):
        self.w.estado.vendas = [
            Venda(i, date(2000, 1, 1) + timedelta(days=i), 100000000000 + i, 900, 100)
            for i in range(5000)
        ]
        self.w.intervalo_vendas = (date.min, date.max)
        d = self.detalhe("vendas")
        self.assertEqual(d.modelo.rowCount(), 5000)
        d.tabela.setCurrentIndex(d.modelo.index(0, 0))
        d.tabela.setFocus()
        QtTest.QTest.keyClick(
            d.tabela, Q.Qt.Key.Key_End, Q.Qt.KeyboardModifier.ControlModifier
        )
        self.assertEqual(d.tabela.currentIndex().row(), 4999)
        self.assertIn("1.000.000.", d.modelo.data(d.modelo.index(0, 3)))
        dias = self.detalhe("dias")
        self.assertTrue(all(0 <= b.value() <= 1000 for b in dias.barras))
        model = ModeloDetalhe([Coluna("Valor", "moeda")], [(900,), (10000,), (2000,)])
        model.sort(0)
        self.assertEqual(model.linhas, [(900,), (2000,), (10000,)])

    def test_estados_vazios_e_texto_longo_em_janela_menor(self):
        self.w.estado.vendas = []
        self.w.estado.lancamentos = []
        self.w.resize(1000, 700)
        for nome in ("vendas", "despesas", "dias", "semana"):
            d = self.detalhe(nome)
            d.resize(480, 320)
            for _ in range(6):
                self.app.processEvents()
            self.assertLessEqual(d.corpo.width(), d.scroll.viewport().width())
            self.assertTrue(d.fechar.isVisible())
        texto = "Explicação longa para avaliar redimensionamento e leitura. " * 80
        d = janela_texto(self.w, "Informações adicionais", [texto])
        self.janelas.append(d)
        d.resize(480, 320)
        d.show()
        self.app.processEvents()
        self.assertLessEqual(d.corpo.width(), d.scroll.viewport().width())

    def test_pagamentos_preservam_valores_e_mes_formatado(self):
        d = self.detalhe("pagamentos")
        self.assertEqual(sum(row[1] for row in d.modelo.linhas), 200650)
        self.assertEqual(d.modelo.rowCount(), 3)
        model = ModeloDetalhe([Coluna("Mês", "mes")], [(date(2026, 10, 1),)])
        self.assertEqual(model.data(model.index(0, 0)), "10/2026")


if __name__ == "__main__":
    unittest.main(verbosity=2)
