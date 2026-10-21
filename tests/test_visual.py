import unittest
from ProgramFeira.interface.visual import ordenar_vendas


class OrdenacaoTests(unittest.TestCase):
    def setUp(self):
        self.rows = [(2, '2026-01-09', 9.5, 0, 100),
                     (10, '2025-12-31', 1000, 2, 0),
                     (3, '2026-02-01', 100, 20, 0)]

    def test_ordena_valores_e_ids_numericamente(self):
        self.assertEqual([v[0] for v in ordenar_vendas(self.rows, 'dinheiro')], [2, 3, 10])
        self.assertEqual([v[0] for v in ordenar_vendas(self.rows, 'id')], [2, 3, 10])
        self.assertEqual([v[0] for v in ordenar_vendas(self.rows, 'total', True)], [10, 3, 2])

    def test_ordena_data_cronologica_e_dia_semana(self):
        self.assertEqual([v[0] for v in ordenar_vendas(self.rows, 'data')], [10, 2, 3])
        self.assertEqual([v[0] for v in ordenar_vendas(self.rows, 'dia_semana')], [10, 2, 3])
        self.assertEqual(self.rows[0][0], 2)  # Não altera lista de origem.

    def test_vazio_e_data_legada(self):
        self.assertEqual(ordenar_vendas([], 'total'), [])
        rows = [(1, '10/01/2026', 0, 0, 0), (2, '2025-12-31', 0, 0, 0)]
        self.assertEqual(ordenar_vendas(rows, 'data')[0][0], 2)
