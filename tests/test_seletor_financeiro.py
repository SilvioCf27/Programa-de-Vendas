import unittest
from datetime import date
from ProgramFeira.interface.seletor_financeiro import semanas_do_mes


class SemanasDoMesTests(unittest.TestCase):
    def test_semanas_completas_na_virada_do_mes_e_do_ano(self):
        semanas = semanas_do_mes(2026, 1)
        self.assertEqual(semanas[0], (date(2025, 12, 29), date(2026, 1, 4)))
        self.assertEqual(semanas[-1], (date(2026, 1, 26), date(2026, 2, 1)))
        self.assertEqual(len(semanas), 5)

    def test_mes_comeca_na_segunda(self):
        self.assertEqual(semanas_do_mes(2026, 6)[0], (date(2026, 6, 1), date(2026, 6, 7)))


class PrimeiraFaturaTests(unittest.TestCase):
    def test_compras_no_fechamento_entram_no_proximo_mes(self):
        from ProgramFeira.financeiro import primeira_fatura, datas_parcelas
        self.assertEqual(primeira_fatura('2026-09-08'), '2026-09-09')
        self.assertEqual(primeira_fatura('2026-09-09'), '2026-10-09')
        self.assertEqual(primeira_fatura('2026-12-09'), '2027-01-09')
        self.assertEqual(primeira_fatura('2026-02-28', 31), '2026-03-31')
        self.assertEqual(datas_parcelas(primeira_fatura('2026-09-09'), 3),
                         ['2026-10-09', '2026-11-09', '2026-12-09'])
