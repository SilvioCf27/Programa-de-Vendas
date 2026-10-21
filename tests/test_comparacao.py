import unittest
from decimal import Decimal
from datetime import date, timedelta
from ProgramFeira.comparacao import fechamento_do_mes, limites_comparacao, comparar_registros


class ComparacaoTests(unittest.TestCase):
    def test_mes_calendario_e_bissexto(self):
        self.assertEqual(limites_comparacao('Mês', 2024, 2), ('2024-02-01', '2024-02-29'))
        self.assertEqual(limites_comparacao('Mês', 2026, 3), ('2026-03-01', '2026-03-31'))

    def test_fechamento_com_mes_inicial_e_sem_sobreposicao(self):
        self.assertEqual(fechamento_do_mes(2026, 10), ('2026-10-10', '2026-11-09'))
        self.assertEqual(fechamento_do_mes(2026, 12), ('2026-12-10', '2027-01-09'))
        for mes in range(1, 12):
            fim = date.fromisoformat(fechamento_do_mes(2026, mes)[1])
            inicio = date.fromisoformat(fechamento_do_mes(2026, mes + 1)[0])
            self.assertEqual(fim + timedelta(days=1), inicio)

    def test_classificacao_diaria_corresponde_a_formula_da_planilha(self):
        # SE(DIA(data)<=9; mês anterior; mês atual), usando o dia 10 como referência.
        for offset in range(365):
            data = date(2026, 1, 1) + timedelta(days=offset)
            referencia = (data.replace(day=1) - timedelta(days=1)) if data.day <= 9 else data
            inicio, fim = fechamento_do_mes(referencia.year, referencia.month)
            self.assertLessEqual(date.fromisoformat(inicio), data)
            self.assertLessEqual(data, date.fromisoformat(fim))

    def test_data_e_intervalos_validos_e_invalidos(self):
        self.assertEqual(limites_comparacao('Data', 0, 0, '09/10/2026'), ('2026-10-09', '2026-10-09'))
        self.assertEqual(limites_comparacao('Intervalo', 0, 0, '10/10/2026', '09/11/2026'), ('2026-10-10', '2026-11-09'))
        for inicio, fim in [('31/02/2026', '10/03/2026'), ('10/10/2026', '09/10/2026')]:
            with self.assertRaises(ValueError):
                limites_comparacao('Intervalo', 0, 0, inicio, fim)

    def test_diferenca_variacao_e_media_com_zerados(self):
        a = [(1, '', 100, 0, 0), (2, '', 0, 0, 0)]
        b = [(3, '', 0, 150, 0)]
        resultado = comparar_registros(a, b)
        self.assertEqual(resultado['diferenca'], Decimal(50))
        self.assertEqual(resultado['variacao'], Decimal(50))
        self.assertEqual(resultado['a']['quantidade'], 2)
        self.assertEqual(resultado['a']['media'], Decimal(50))
        self.assertEqual(resultado['b']['media'], Decimal(150))
        self.assertEqual(comparar_registros(b, a)['variacao'].quantize(Decimal('.1')), Decimal('-33.3'))

    def test_zero_e_ausencia_de_registros_sao_distintos(self):
        zero = [(1, '', 0, 0, 0)]
        r = comparar_registros(zero, zero)
        self.assertEqual(r['a']['quantidade'], 1)
        self.assertIsNone(r['variacao'])
        self.assertIn('total de A é zero', r['motivo'])
        r = comparar_registros([], zero)
        self.assertEqual(r['a']['quantidade'], 0)
        self.assertIn('Sem registros', r['motivo'])
