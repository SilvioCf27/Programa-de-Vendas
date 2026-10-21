from dados_ficticios import criar_banco
import importlib.util
import shutil
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BancoTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("banco_teste", ROOT / "ProgramFeira/database/banco.py")
        self.banco = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.banco)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.banco.CAMINHO_BANCO = Path(self.tmp.name) / "vendas.db"
        criar_banco(self.banco.CAMINHO_BANCO)

    def test_historico_importado(self):
        self.assertEqual(len(self.banco.listar_vendas()), 9)
        totals = tuple(Decimal(str(v)).quantize(Decimal(".01")) for v in self.banco.obter_resumo_vendas())
        self.assertEqual(totals, tuple(map(Decimal, ["250.00", "100.50", "210.75"])))
        self.assertEqual(self.banco.listar_anos_vendas(), [2025, 2026, 2027])

    def test_duplicidade_nao_bloqueia_proxima_gravacao(self):
        erro = None
        try:
            self.banco.cadastrar_venda("2025-01-03", 1, 2, 3)
        except sqlite3.IntegrityError as exc:
            erro = exc  # Retém traceback para detectar conexão abandonada.
        self.assertIsNotNone(erro)
        self.banco.cadastrar_venda("2030-01-10", 10, 20, 30)
        venda = self.banco.buscar_venda_por_data("2030-01-10")
        self.assertEqual(venda[2:], (10, 20, 30))
        self.banco.atualizar_venda(venda[0], "2030-01-11", 40, 50, 60)
        self.assertEqual(self.banco.buscar_venda_por_id(venda[0])[1:], ("2030-01-11", 40, 50, 60))
        self.banco.excluir_venda(venda[0])
        self.assertEqual(len(self.banco.listar_vendas()), 9)

    def test_pagamento_invalido_nao_bloqueia(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.banco.cadastrar_venda("2030-01-10", None, 2, 3)
        self.banco.cadastrar_venda("2030-01-10", 1, 2, 3)
        self.assertIsNotNone(self.banco.buscar_venda_por_data("2030-01-10"))


if __name__ == "__main__":
    unittest.main()
