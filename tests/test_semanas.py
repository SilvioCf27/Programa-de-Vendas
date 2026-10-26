from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from ProgramFeira import fechamento
from ProgramFeira.semanas import semana_atual, agrupar_semanas, selecao_inicial, PERIODOS_INICIAIS
from ProgramFeira.preferencias import carregar_periodo_inicial, salvar_periodo_inicial, salvar_tema


class SemanasTests(unittest.TestCase):
    def test_domingo_inclui_dias_zerados_exclui_futuro_e_segunda_reinicia(self):
        vendas = [(1, '2026-10-18', 100, 0, 0), (2, '2026-10-19', 0, 0, 0),
                  (3, '23/10/2026', 10.10, 20.20, 30.30), (4, '2026-10-25', 5, 0, 0),
                  (5, '2026-10-26', 7, 0, 0), (6, '2026-10-30', 9, 0, 0), (7, 'inválida', 999, 0, 0)]
        domingo = semana_atual(vendas, date(2026, 10, 25))
        self.assertEqual((domingo['inicio'], domingo['fim']), (date(2026, 10, 19), date(2026, 10, 25)))
        self.assertEqual(domingo['total'], Decimal('65.60'))
        self.assertEqual(domingo['quantidade'], 3)
        self.assertEqual(domingo['totais'], (Decimal('15.1'), Decimal('20.2'), Decimal('30.3')))
        segunda = semana_atual(vendas, date(2026, 10, 26))
        self.assertEqual(segunda['total'], 7)
        self.assertEqual(segunda['quantidade'], 1)
        self.assertEqual(segunda['fim'], date(2026, 11, 1))

    def test_historico_cruza_ano_preserva_zeros_e_nao_inventa_feiras(self):
        grupos = agrupar_semanas([(1, '2026-12-31', 1, 0, 0), (2, '2027-01-03', 2, 0, 0), (3, '2027-01-11', 0, 0, 0)])
        self.assertEqual(len(grupos), 2)
        self.assertEqual(grupos[0]['quantidade'], 1)
        self.assertEqual(grupos[0]['total'], 0)
        self.assertEqual(grupos[1]['inicio'], date(2026, 12, 28))
        self.assertEqual(grupos[1]['fim'], date(2027, 1, 3))
        self.assertEqual(grupos[1]['media'], Decimal('1.5'))
        self.assertEqual(agrupar_semanas([]), [])
        self.assertEqual(semana_atual([], date(2026, 10, 26))['quantidade'], 0)

    def test_abertura_respeita_fechamento_no_dia_9_virada_e_historico(self):
        anterior = fechamento.estado()
        self.addCleanup(fechamento.definir, anterior)
        fechamento.definir({'versao': 1, 'historico': [{'vigencia': '2027-01-01', 'dia': 15}]})
        self.assertEqual(selecao_inicial('Fechamento atual', date(2026, 1, 9)), (2025, 12, True))
        self.assertEqual(selecao_inicial('Fechamento atual', date(2026, 10, 10)), (2026, 10, True))
        self.assertEqual(selecao_inicial('Fechamento atual', date(2027, 1, 15)), (2026, 12, True))
        self.assertEqual(selecao_inicial('Fechamento atual', date(2027, 1, 16)), (2027, 1, True))
        self.assertEqual(selecao_inicial('Mês atual', date(2026, 10, 26)), (2026, 10, False))
        self.assertEqual(selecao_inicial('Ano atual', date(2026, 10, 26)), (2026, None, False))
        self.assertEqual(selecao_inicial('Todas as vendas'), (None, None, False))

    def test_preferencia_independente_do_tema_e_sem_escrita_ao_carregar(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            self.assertEqual(carregar_periodo_inicial(pasta), 'Fechamento atual')
            self.assertEqual(list(pasta.iterdir()), [])
            for periodo in PERIODOS_INICIAIS:
                salvar_periodo_inicial(pasta, periodo)
                salvar_tema(pasta, 'aurora')
                self.assertEqual(carregar_periodo_inicial(pasta), periodo)
            antes = (pasta / 'inicio.json').read_bytes()
            with self.assertRaises(ValueError): salvar_periodo_inicial(pasta, 'Última semana')
            self.assertEqual((pasta / 'inicio.json').read_bytes(), antes)
            for texto in ('invalido', '[]', '{"periodo":"desconhecido"}'):
                (pasta / 'inicio.json').write_text(texto)
                self.assertEqual(carregar_periodo_inicial(pasta), 'Fechamento atual')
