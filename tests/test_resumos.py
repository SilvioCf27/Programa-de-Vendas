import unittest
from decimal import Decimal
from ProgramFeira.resumos import calcular_indicadores, periodo_anterior, descrever_comparacao, moeda


class ResumosTests(unittest.TestCase):
    def test_media_inclui_dia_zerado_e_percentuais(self):
        dados = [(1, '2026-01-02', 10, 20, 30), (2, '2026-01-04', 0, 0, 0)]
        r = calcular_indicadores(dados)
        self.assertEqual(r['quantidade'], 2)
        self.assertEqual(r['total'], Decimal(60))
        self.assertEqual(r['media'], Decimal(30))
        self.assertEqual(r['participacoes'][2], Decimal(50))

    def test_centavos_e_arredondamento(self):
        r = calcular_indicadores([(1, '', .1, .2, 0)])
        self.assertEqual(r['total'], Decimal('.3'))
        self.assertEqual(moeda(Decimal('1234.565')), 'R$ 1.234,57')

    def test_vazio_e_todos_zerados(self):
        for dados, quantidade in [([], 0), ([(1, '', 0, 0, 0)], 1)]:
            r = calcular_indicadores(dados)
            self.assertEqual(r['media'], 0)
            self.assertEqual(r['participacoes'], (0, 0, 0))
            self.assertEqual(r['quantidade'], quantidade)

    def test_periodos_anteriores(self):
        cases = [
            ('Ano', '2026-01-01', '2026-12-31', ('2025-01-01', '2025-12-31')),
            ('Mês', '2024-03-01', '2024-03-31', ('2024-02-01', '2024-02-29')),
            ('Mês', '2026-01-01', '2026-01-31', ('2025-12-01', '2025-12-31')),
            ('Período de fechamento', '2025-12-10', '2026-01-09', ('2025-11-10', '2025-12-09')),
        ]
        for tipo, inicio, fim, esperado in cases:
            self.assertEqual(periodo_anterior(tipo, inicio, fim), esperado)
        self.assertIsNone(periodo_anterior('Todas as vendas', None, None))

    def test_comparacao_crescimento_queda_zero_e_ausencia(self):
        def indicadores(valor):
            return calcular_indicadores([(1, '', valor, 0, 0)])
        periodo = ('2025-01-01', '2025-12-31')
        self.assertIn('+50,0%', descrever_comparacao(indicadores(150), indicadores(100), periodo))
        self.assertIn('-50,0%', descrever_comparacao(indicadores(50), indicadores(100), periodo))
        self.assertIn('total anterior zero', descrever_comparacao(indicadores(50), indicadores(0), periodo))
        self.assertIn('sem registros para comparação', descrever_comparacao(indicadores(50), calcular_indicadores([]), periodo))
        self.assertIn('atual sem registros', descrever_comparacao(calcular_indicadores([]), indicadores(50), periodo))
        self.assertIn('selecione', descrever_comparacao(indicadores(50), None, None))
