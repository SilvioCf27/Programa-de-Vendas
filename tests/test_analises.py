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


class EvolucaoTests(unittest.TestCase):
    def test_fechamentos_incluem_virada_do_ano_e_lacunas_nao_viram_dias_de_feira(self):
        from ProgramFeira.tendencias import evolucao
        from decimal import Decimal
        vendas = [(1,'2030-12-10',10,0,0),(2,'2031-01-09',20,0,0),(3,'2031-03-10',0,0,0)]
        grupos = evolucao(vendas,'Fechamento')
        self.assertEqual([g['rotulo'] for g in grupos],['12/2030','01/2031','02/2031','03/2031'])
        self.assertEqual(grupos[0]['total'],Decimal(30))
        self.assertEqual(grupos[1]['quantidade'],0)
        self.assertEqual(grupos[-1]['quantidade'],1)
        self.assertEqual(evolucao([]),[])
