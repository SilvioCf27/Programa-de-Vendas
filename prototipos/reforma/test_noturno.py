"""Verifica a demo Noturno em memória, sem importar o aplicativo estável."""

import ast
import sys
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from datetime import date
from PySide6 import QtCore as Q, QtWidgets as W
from estado_demo import Estado, limites, agrupar
from noturno_demo import Aplicativo, preparar


class EstadoTests(unittest.TestCase):
    def test_totais_e_centavos(self):
        e = Estado()
        r = e.resumo(limites("Fechamento"))
        self.assertEqual(
            r,
            dict(
                bruto=200650,
                taxas=1680,
                liquido=198970,
                despesas=132000,
                saldo=66970,
                falta=0,
            ),
        )
        self.assertEqual(
            sum(
                sum(v.total for v in rs)
                for _, rs in agrupar(e.consultar_vendas(limites("Mês")))
            ),
            200650,
        )

    def test_zero_conta_e_semana_nao_inclui_futuro(self):
        e = Estado()
        self.assertEqual(len(e.consultar_vendas(limites("Mês"))), 6)
        self.assertEqual(
            len(e.consultar_vendas((date(2026, 10, 26), date(2026, 10, 26)))), 0
        )

    def test_limites_virada_ano_e_semana(self):
        self.assertEqual(
            limites("Fechamento", 2026, 12), (date(2026, 12, 10), date(2027, 1, 9))
        )
        self.assertEqual(
            limites("Semana", 2026, 10, 0), (date(2026, 9, 28), date(2026, 10, 4))
        )

    def test_exclusao_invalida_nao_remove_parcialmente(self):
        e = Estado()
        antes = list(e.vendas)
        with self.assertRaises(ValueError):
            e.excluir("Vendas", [1, 999])
        self.assertEqual(e.vendas, antes)

    def test_isolamento_das_instancias(self):
        a, b = Estado(), Estado()
        a.excluir("Finanças", [1, 2])
        self.assertEqual(len(a.lancamentos), 10)
        self.assertEqual(len(b.lancamentos), 12)

    def test_sem_importacao_de_banco_rede_ou_producao(self):
        for nome in ["estado_demo.py", "noturno_demo.py"]:
            tree = ast.parse(Path(__file__).with_name(nome).read_text())
            for node in ast.walk(tree):
                names = (
                    [x.name for x in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                )
                self.assertFalse(
                    any(
                        s.startswith(
                            (
                                "ProgramFeira",
                                "sqlite3",
                                "urllib",
                                "requests",
                                "socket",
                                "http",
                            )
                        )
                        for s in names
                    )
                )


class TelaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = preparar()

    def setUp(self):
        self.errors = []
        self.hook = sys.excepthook
        sys.excepthook = lambda *args: self.errors.append(args)
        self.w = Aplicativo()
        self.w.show()
        self.app.processEvents()

    def tearDown(self):
        self.w.close()
        self.w.deleteLater()
        self.app.processEvents()
        sys.excepthook = self.hook
        self.assertFalse(self.errors, self.errors)

    def test_pagina_nao_limita_totais_e_limpa_selecao(self):
        t = self.w.tabela_vendas
        t.tamanho.setCurrentText("5")
        self.assertEqual(t.table.rowCount(), 5)
        self.assertEqual(len(t.linhas), 6)
        self.assertEqual(self.w.cards[0].text(), "R$ 2.006,50")
        t.todos.setChecked(True)
        self.assertEqual(len(t.selecionados()), 5)
        t.mover(1)
        self.assertEqual(len(t.selecionados()), 0)
        self.assertEqual(t.table.rowCount(), 1)
        self.assertEqual(self.w.cards[0].text(), "R$ 2.006,50")

    def test_troca_area_preserva_selecao_e_filtro_pendente(self):
        t = self.w.tabela_vendas
        next(iter(t.checks.values())).setChecked(True)
        self.w.seletor_vendas.mes.setCurrentIndex(8)
        selecionados = t.selecionados()
        self.w.mostrar("Finanças")
        self.w.mostrar("Análises")
        self.w.mostrar("Vendas")
        self.assertEqual(t.selecionados(), selecionados)
        self.assertTrue(self.w.pendente.text())
        self.assertEqual(self.w.intervalo_vendas, limites("Fechamento"))

    def test_aplicar_consulta_recalcula_e_limpa_selecao(self):
        t = self.w.tabela_vendas
        t.todos.setChecked(True)
        self.w.seletor_vendas.tipo.setCurrentText("Mês")
        self.w.seletor_vendas.mes.setCurrentIndex(8)
        self.w.aplicar_vendas()
        self.assertEqual(self.w.cards[0].text(), "R$ 1.500,00")
        self.assertFalse(t.selecionados())
        self.assertFalse(self.w.pendente.text())
        self.w.mostrar("Análises")
        self.assertEqual(self.w.ana_tabela.rowCount(), 3)

    def test_financas_lista_nao_muda_totais_e_consulta_independente(self):
        self.w.mostrar("Finanças")
        self.w.fin_recorte.setCurrentText("Taxas")
        self.assertEqual(len(self.w.tabela_financas.linhas), 1)
        self.assertEqual(self.w.fin_cards["despesas"].text(), "R$ 1.320,00")
        self.w.seletor_financas.tipo.setCurrentText("Semana")
        self.w.seletor_financas.semana.setCurrentIndex(3)
        self.w.aplicar_financas()
        self.assertEqual(self.w.intervalo_vendas, limites("Fechamento"))
        self.assertEqual(self.w.intervalo_financas, limites("Semana", 2026, 10, 3))

    def test_cancelar_exclusao_e_confirmar_lote(self):
        ids = [r[0] for r in self.w.tabela_vendas.linhas[:2]]
        antes = len(self.w.estado.vendas)

        def cancelar():
            box = W.QApplication.activeModalWidget()
            for b in box.buttons():
                if box.buttonRole(b) == W.QMessageBox.ButtonRole.RejectRole:
                    b.click()
                    break

        Q.QTimer.singleShot(0, cancelar)
        self.w.confirmar_exclusao("Vendas", ids)
        self.assertEqual(len(self.w.estado.vendas), antes)

        def confirmar():
            box = W.QApplication.activeModalWidget()
            for b in box.buttons():
                if box.buttonRole(b) == W.QMessageBox.ButtonRole.DestructiveRole:
                    b.click()
                    break

        Q.QTimer.singleShot(0, confirmar)
        self.w.confirmar_exclusao("Vendas", ids)
        self.assertEqual(len(self.w.estado.vendas), antes - 2)
        self.assertFalse(set(ids) & {r.id for r in self.w.estado.vendas})
        self.assertIn("4 registros", self.w.total_vendas.text())

    def test_excluir_ultima_pagina_e_consulta_vazia(self):
        t = self.w.tabela_vendas
        t.tamanho.setCurrentText("5")
        t.mover(1)
        self.w.excluir_confirmado("Vendas", [r[0] for r in t.visiveis])
        self.assertEqual(t.pagina, 0)
        self.assertEqual(t.paginas(), 1)
        self.w.excluir_confirmado("Vendas", [r[0] for r in t.linhas])
        self.assertEqual(self.w.cards[0].text(), "R$ 0,00")
        self.assertEqual(self.w.cards[1].text(), "0")
        self.assertFalse(t.apagar.isEnabled())
        self.assertFalse(t.todos.isEnabled())
        self.assertEqual(t.table.rowCount(), 0)

    def test_excluir_taxa_atualiza_resumos(self):
        self.w.mostrar("Finanças")
        taxa = next(r for r in self.w.estado.lancamentos if r.taxa)
        self.w.excluir_confirmado("Finanças", [taxa.id])
        self.assertEqual(self.w.fin_secundarios["taxas"].text(), "R$ 0,00")
        self.assertEqual(self.w.fin_cards["saldo"].text(), "R$ 686,50")

    def test_comparador_dia_intervalo_e_independencia(self):
        self.w.mostrar("Análises")
        self.w.a.tipo.setCurrentText("Dia")
        self.w.a.inicio_data.setDate(Q.QDate(2026, 10, 25))
        self.w.b.tipo.setCurrentText("Intervalo")
        self.w.b.inicio_data.setDate(Q.QDate(2026, 10, 16))
        self.w.b.fim_data.setDate(Q.QDate(2026, 10, 18))
        self.w.comparar()
        self.assertIn("A: R$ 509,00", self.w.ana_comparacao.text())
        self.assertIn("B: R$ 749,50", self.w.ana_comparacao.text())
        self.assertEqual(self.w.intervalo_vendas, limites("Fechamento"))
        self.w.b.fim_data.setDate(Q.QDate(2026, 9, 1))
        with self.assertRaises(ValueError):
            self.w.b.intervalo()

    def test_janela_menor_sem_corte_horizontal_e_cartoes_reorganizados(self):
        self.w.resize(1280, 800)
        for area in ("Vendas", "Análises", "Finanças"):
            self.w.mostrar(area)
            for _ in range(3):
                self.app.processEvents()
            self.assertLessEqual(
                self.w.scroll.widget().width(), self.w.scroll.viewport().width(), area
            )
        self.w.mostrar("Vendas")
        self.app.processEvents()
        cards = self.w.cards[0].parentWidget().parentWidget()
        self.assertEqual(cards.colunas, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
