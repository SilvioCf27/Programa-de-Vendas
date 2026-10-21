import unittest
from decimal import Decimal
from ProgramFeira.interface.analises import agrupar_dias
from ProgramFeira.interface.ajuda import AJUDAS


class AnalisesTests(unittest.TestCase):
    def test_grupos_preservam_dias_zerados_e_totais(self):
        vendas = [(1, '2026-01-02', 100, 0, 0), (2, '2026-01-09', 0, 0, 0), (3, '2026-01-04', 0, 25.5, 0)]
        grupos = dict(agrupar_dias(vendas))
        self.assertEqual(grupos['Sexta-feira']['quantidade'], 2)
        self.assertEqual(grupos['Sexta-feira']['media'], Decimal(50))
        self.assertEqual(sum(g['quantidade'] for g in grupos.values()), 3)
        self.assertEqual(sum(g['total'] for g in grupos.values()), Decimal('125.5'))

    def test_grupos_vazios_e_data_legada(self):
        self.assertEqual(len(agrupar_dias([])), 7)
        grupos = dict(agrupar_dias([(1, '02/01/2026', 1, 2, 3), (2, 'invalida', 0, 0, 0)]))
        self.assertEqual(grupos['Sexta-feira']['total'], 6)
        self.assertEqual(sum(g['quantidade'] for g in grupos.values()), 1)

    def test_ajudas_cobrem_indicadores_e_regras_financeiras(self):
        required = {'total', 'media', 'quantidade', 'dinheiro', 'pix', 'cartao', 'participacao', 'comparacao', 'fechamento', 'filtros', 'por_dia', 'analises'}
        self.assertTrue(required <= AJUDAS.keys())
        self.assertIn('não lucro', AJUDAS['total'][1])
        self.assertIn('R$ 150', AJUDAS['media'][1])
        self.assertIn('10/10/2026', AJUDAS['fechamento'][1])
