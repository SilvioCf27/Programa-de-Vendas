from dados_ficticios import criar_banco
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from ProgramFeira import financeiro as f
from ProgramFeira.database import banco

ROOT = Path(__file__).resolve().parents[1]


class FinanceiroTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.caminho = Path(self.tmp.name) / 'vendas.db'
        criar_banco(self.caminho)
        self.patch = patch.object(banco, 'CAMINHO_BANCO', self.caminho)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.vendas = banco.listar_vendas()
        f.inicializar()

    def linhas(self):
        return f.listar_lancamentos('2000-01-01', '2099-12-31')

    def despesa(self, valor='100,00', **kwargs):
        args = dict(tipo='despesa', data='2026-10-15', descricao='Compras', valor=valor)
        args.update(kwargs)
        f.salvar_lancamento(**args)

    def test_migracao_backup_anterior_e_idempotencia_preserva_vendas(self):
        backups = list((self.caminho.parent / 'backups').glob('*.db'))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0])) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM vendas').fetchone()[0], 9)
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='financeiro_lancamentos'").fetchone())
        f.inicializar()
        self.assertEqual(len(list((self.caminho.parent / 'backups').glob('*.db'))), 1)
        self.assertEqual(banco.listar_vendas(), self.vendas)

    def test_valores_exatos_e_formatos_invalidos(self):
        for texto, esperado in [('0,01', 1), ('R$ 1.234,56', 123456), ('1234.56', 123456), ('300', 30000)]:
            self.assertEqual(f.centavos(texto), esperado)
        for texto in ('NaN', 'Infinity', '-1', '0', '', '1,234', '1.234', '1e3', '1.2,00'):
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                f.centavos(texto)

    def test_taxa_anual_sem_rateio_e_cobertura_parcial(self):
        f.salvar_taxa_anual(2025, '2025-01-01', '2025-12-31', '210,25')
        ano = f.resumo_periodo('2025-01-01', '2025-12-31')
        mes = f.resumo_periodo('2025-10-01', '2025-10-31')
        self.assertEqual(ano['taxas'], Decimal('210.25'))
        self.assertEqual(ano['liquido'], ano['bruto'] - Decimal('210.25'))
        self.assertEqual(mes['taxas'], 0)
        self.assertEqual(mes['parciais'], [2025])
        self.assertEqual(ano['parciais'], [])

    def test_ano_atual_acumulado_substitui_em_vez_de_somar(self):
        f.salvar_taxa_anual(2026, '2026-01-01', '2026-09-30', '100')
        f.salvar_taxa_anual(2026, '2026-01-01', '2026-10-20', '120')
        self.assertEqual(len(f.listar_taxas_anuais()), 1)
        self.assertEqual(f.resumo_periodo('2026-01-01', '2026-12-31')['taxas'], 120)
        self.assertEqual(f.resumo_periodo('2026-10-01', '2026-10-31')['parciais'], [2026])
        f.salvar_lancamento('taxa', '2026-10-21', 'Taxa diária posterior', '2,30')
        self.assertEqual(f.resumo_periodo('2026-01-01', '2026-12-31')['taxas'], Decimal('122.30'))

    def test_sobreposicao_diaria_anual_bloqueada_nas_duas_direcoes(self):
        f.salvar_lancamento('taxa', '2025-02-10', 'Taxa', '1')
        with self.assertRaises(ValueError):
            f.salvar_taxa_anual(2025, '2025-01-01', '2025-12-31', '200')
        f.salvar_taxa_anual(2026, '2026-01-01', '2026-10-20', '200')
        with self.assertRaises(ValueError):
            f.salvar_lancamento('taxa', '2026-10-20', 'Taxa duplicada', '1')
        self.assertEqual(len(self.linhas()), 1)
        self.assertEqual(len(f.listar_taxas_anuais()), 1)

    def test_taxa_diaria_unica_falha_nao_bloqueia_proxima_operacao(self):
        f.salvar_lancamento('taxa', '2026-10-15', 'Taxa', '1,15')
        with self.assertRaises(ValueError):
            f.salvar_lancamento('taxa', '2026-10-15', 'Duplicada', '2')
        self.despesa()
        taxa = next(r for r in self.linhas() if r['tipo'] == 'taxa')
        f.salvar_lancamento('taxa', taxa['data'], 'Corrigida', '2,10', identificador=taxa['id'])
        self.assertEqual(f.resumo_periodo('2026-10-01', '2026-10-31')['taxas'], Decimal('2.10'))

    def test_parcelas_virada_ano_meses_curtos_valor_por_parcela(self):
        self.despesa('33,33', data='2027-01-31', meio='Cartão de crédito', parcelas=3)
        linhas = sorted(self.linhas(), key=lambda r: r['parcela'])
        self.assertEqual([r['data'] for r in linhas], ['2027-01-31', '2027-02-28', '2027-03-31'])
        self.assertEqual(sum(r['valor_centavos'] for r in linhas), 9999)
        self.assertEqual(len({r['grupo'] for r in linhas}), 1)
        self.assertEqual([r['parcela'] for r in linhas], [1, 2, 3])
        self.despesa('1', data='2027-12-09', meio='Cartão de crédito', parcelas=2)
        self.assertTrue(any(r['data'] == '2028-01-09' for r in self.linhas()))

    def test_editar_excluir_somente_parcela_selecionada(self):
        self.despesa(meio='Cartão de crédito', parcelas=3)
        linhas = sorted(self.linhas(), key=lambda r: r['parcela'])
        alvo = linhas[1]
        self.despesa('90', identificador=alvo['id'], data='2026-11-15', meio='Cartão de crédito')
        novas = sorted(self.linhas(), key=lambda r: r['parcela'])
        self.assertEqual([r['valor_centavos'] for r in novas], [10000, 9000, 10000])
        self.assertEqual(novas[1]['parcela'], 2)
        f.excluir_lancamento(alvo['id'])
        self.assertEqual(len(self.linhas()), 2)

    def test_falha_backup_impede_migracao_gravacao_edicao_e_exclusao(self):
        self.despesa()
        antes = self.linhas()
        with patch.object(banco, 'criar_backup', side_effect=OSError('disco cheio')):
            for acao in (lambda: self.despesa(meio='Cartão de crédito', parcelas=3),
                         lambda: self.despesa('50', identificador=antes[0]['id']),
                         lambda: f.excluir_lancamento(antes[0]['id']),
                         lambda: f.salvar_taxa_anual(2025, '2025-01-01', '2025-12-31', '200')):
                with self.assertRaises(OSError):
                    acao()
        self.assertEqual(self.linhas(), antes)
        self.assertEqual(f.listar_taxas_anuais(), [])
        self.assertEqual(banco.listar_vendas(), self.vendas)

    def test_backup_restauracao_inclui_financas_e_legado_pode_ser_reaberto(self):
        self.despesa()
        f.salvar_taxa_anual(2025, '2025-01-01', '2025-12-31', '210')
        copia = banco.criar_backup()
        f.excluir_lancamento(self.linhas()[0]['id'])
        banco.restaurar_backup(copia)
        self.assertEqual(len(self.linhas()), 1)
        self.assertEqual(len(f.listar_taxas_anuais()), 1)
        legado = criar_banco(Path(self.tmp.name) / 'legado.db')
        banco.restaurar_backup(legado)
        f.inicializar()
        self.assertEqual(self.linhas(), [])
        self.assertEqual(banco.listar_vendas(), self.vendas)

    def test_meta_cobre_despesas_taxas_uma_vez_sem_chamar_lucro(self):
        vendas = [(1, '2026-10-15', 100, 200, 200)]
        lancamentos = [{'tipo': 'despesa', 'valor_centavos': 60000}, {'tipo': 'taxa', 'valor_centavos': 1000}]
        r = f.resumir(vendas, lancamentos, [], '2026-10-10', '2026-11-09')
        self.assertEqual((r['bruto'], r['liquido'], r['despesas'], r['saldo'], r['falta']), (500, 490, 600, -110, 110))
        lancamentos[0]['valor_centavos'] = 30000
        r = f.resumir(vendas, lancamentos, [], '2026-10-10', '2026-11-09')
        self.assertEqual((r['saldo'], r['falta']), (190, 0))

    def test_fechamento_datas_limites_e_semana_parcial(self):
        self.assertEqual(f.limites('Fechamento', '2026-12-01'), ('2026-12-10', '2027-01-09'))
        self.assertEqual(f.limites('Semana', '2026-10-18'), ('2026-10-12', '2026-10-18'))
        self.assertEqual(f.limites('Mês', '2028-02-01'), ('2028-02-01', '2028-02-29'))
        self.despesa('10', data='2026-10-09')
        self.despesa('20', data='2026-10-10')
        self.despesa('30', data='2026-11-09')
        self.despesa('40', data='2026-11-10')
        linhas = f.listar_lancamentos('2026-10-10', '2026-11-09')
        self.assertEqual(sum(v for _, v in f.semanas(linhas)), 5000)
        self.assertEqual(f.resumo_periodo('2026-10-10', '2026-11-09')['despesas'], 50)

    def test_entrada_invalida_nao_cria_parcelas_parciais(self):
        for kwargs in ({'data': '2026-02-30'}, {'parcelas': 0}, {'parcelas': 121}, {'parcelas': 2}, {'descricao': ''}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.despesa(**kwargs)
        with self.assertRaises(ValueError):
            f.salvar_taxa_anual(2025, '2025-01-01', '2026-01-01', '1')
        self.assertEqual(self.linhas(), [])

    def test_falha_backup_impede_alteracao_de_estrutura(self):
        with closing(sqlite3.connect(self.caminho)) as c, c:
            c.execute('DROP TABLE financeiro_lancamentos')
            c.execute('DROP TABLE financeiro_taxas_anuais')
        with patch.object(banco, 'criar_backup', side_effect=OSError('sem espaço')):
            with self.assertRaises(OSError):
                f.inicializar()
        with closing(sqlite3.connect(self.caminho)) as c:
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='financeiro_lancamentos'").fetchone())
        self.assertEqual(banco.listar_vendas(), self.vendas)

    def test_operacao_de_parcelas_e_atomica(self):
        with closing(sqlite3.connect(self.caminho)) as c, c:
            c.execute("""CREATE TRIGGER simular_falha BEFORE INSERT ON financeiro_lancamentos
                WHEN NEW.parcela=2 BEGIN SELECT RAISE(ABORT, 'falha simulada'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.despesa(meio='Cartão de crédito', parcelas=3)
        self.assertEqual(self.linhas(), [])

    def test_migracao_taxas_antigas_preserva_valores_e_backup(self):
        with closing(sqlite3.connect(self.caminho)) as c, c:
            c.execute('DROP TABLE financeiro_taxas_anuais')
            c.execute('CREATE TABLE financeiro_taxas_anuais (ano INTEGER PRIMARY KEY,inicio TEXT,fim TEXT,valor_centavos INTEGER)')
            c.execute("INSERT INTO financeiro_taxas_anuais VALUES (2025,'2025-01-01','2025-12-31',20000)")
        f.inicializar()
        registro = f.listar_taxas_anuais()[0]
        self.assertEqual(registro['valor_centavos'], 20000)
        self.assertEqual(registro['natureza'], 'Confirmada')
        self.assertEqual(registro['observacao'], '')
        registro['natureza'] = 'Estimada'
        f.salvar_taxa_anual(2025, registro['inicio'], registro['fim'], '200', 'Estimada', 'Estimativa manual')
        self.assertEqual(f.listar_taxas_anuais()[0]['natureza'], 'Estimada')

    def test_taxas_semanais_preservam_data_e_atualizam_sem_duplicar(self):
        self.assertEqual(f.salvar_taxas_semana('2026-10-05', {'2026-10-09': '2,00', '2026-10-11': '3,00'}), 2)
        linhas = self.linhas()
        ids = {r['data']: r['id'] for r in linhas}
        self.assertEqual(f.salvar_taxas_semana('2026-10-05', {'2026-10-09': '2,50', '2026-10-11': '3,00'}), 1)
        self.assertEqual({r['data']: r['id'] for r in self.linhas()}, ids)
        self.assertEqual(f.resumo_periodo('2026-09-10', '2026-10-09')['taxas'], Decimal('2.50'))
        self.assertEqual(f.resumo_periodo('2026-10-10', '2026-11-09')['taxas'], Decimal('3'))

    def test_taxas_semanais_sao_atomicas_quando_um_dia_esta_no_historico(self):
        f.salvar_taxa_anual(2026, '2026-10-11', '2026-10-12', '10,00')
        with self.assertRaises(ValueError):
            f.salvar_taxas_semana('2026-10-05', {'2026-10-09': '2,00', '2026-10-11': '3,00'})
        self.assertEqual(self.linhas(), [])
