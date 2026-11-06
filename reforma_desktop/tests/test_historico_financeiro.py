import unittest
from reforma_desktop.historico_financeiro import data_da_compra, historico_financeiro


def compra(identificador, compra, fatura, meio='Cartão de crédito'):
    return dict(id=identificador, tipo='despesa', data_compra=compra, data=fatura,
                descricao='Mercado terça', meio=meio, categoria='Casa', parcela=1, parcelas=3, valor_centavos=12345)


class HistoricoFinanceiroTests(unittest.TestCase):
    def test_ordena_pela_compra_sem_inventar_data_legada(self):
        antiga = compra('a', '2026-09-01', '2026-12-09')
        antiga['created_at'] = '2099-12-31'
        nova = compra('n', '2026-10-20', '2026-11-09')
        legado = compra('l', None, '2027-01-09')
        dinheiro = compra('d', None, '2026-10-21', 'Dinheiro')
        self.assertEqual([r['id'] for r in historico_financeiro([antiga, nova, legado, dinheiro])], ['d', 'n', 'a', 'l'])
        self.assertIsNone(data_da_compra(legado))
        self.assertEqual(data_da_compra(dinheiro), '2026-10-21')
        self.assertEqual(antiga['data'], '2026-12-09')

    def test_busca_por_datas_dia_valor_descricao_e_meio(self):
        r = compra('x', '2026-10-20', '2026-11-09')
        for termo in ['20/10/2026', '09/11/2026', '2026-10-20', 'TERCA', 'mercado', 'credito', '123,45', '123.45', '1/3']:
            self.assertEqual(len(historico_financeiro([r], termo)), 1, termo)
        self.assertEqual(historico_financeiro([r], 'ausente'), [])
