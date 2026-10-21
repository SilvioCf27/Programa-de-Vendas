from dados_ficticios import criar_banco
import ast
import calendar
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import tkinter as tk
import unittest
import shutil
import tempfile
from unittest.mock import patch, Mock
from ProgramFeira.comparacao import fechamento_do_mes
from ProgramFeira.interface.visual import ordenar_vendas
from ProgramFeira.exportacao import montar_relatorio
from ProgramFeira.database import banco
from ProgramFeira.resumos import calcular_indicadores, periodo_anterior, descrever_comparacao, moeda

ROOT = Path(__file__).resolve().parents[1]


class Tabela:
    def __init__(self):
        self.rows = {}

    def get_children(self):
        return list(self.rows)

    def delete(self, key):
        del self.rows[key]

    def insert(self, parent, position, values, tags=()):
        self.rows[len(self.rows)] = values


class FiltrosTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        banco_teste = Path(tmp.name) / 'vendas.db'
        criar_banco(banco_teste)
        patcher = patch.object(banco, 'CAMINHO_BANCO', banco_teste)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Usa as funções reais da interface sem iniciar janela ou criar tabela SQLite.
        tree = ast.parse((ROOT / 'ProgramFeira/main.py').read_text(encoding='utf-8'))
        names = {'obter_filtros', 'selecionar_ano_filtro', 'selecionar_mes_filtro',
                 'atualizar_tabela', 'atualizar_resumo', 'descrever_filtro_atual', 'limpar_filtros', 'sincronizar_filtros', 'assinatura_filtros', 'atualizar_aviso_filtros'}
        self.tcl = tk.Tcl()
        n = self.n = dict(fechamento_do_mes=fechamento_do_mes, painel_analises=Mock(), ordenar_vendas=ordenar_vendas, ordenacao_coluna="data", ordenacao_decrescente=True,
                         sincronizando_filtros=False, filtros_aplicados=None, ajustar_larguras_colunas=lambda: None, Decimal=Decimal, atualizar_botoes_selecao=lambda: None, atualizar_cabecalhos=lambda: None, montar_relatorio=montar_relatorio, calcular_indicadores=calcular_indicadores, periodo_anterior=periodo_anterior,
                         descrever_comparacao=descrever_comparacao, moeda=moeda, date=date, timedelta=timedelta, calendar=calendar, tk=tk,
                         DIA_FECHAMENTO=9, ANOS=[2025, 2026, 2027],
                         MESES={nome: i for i, nome in enumerate(('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'), 1)},
                         DIAS_SEMANA=('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'),
                         listar_vendas=banco.listar_vendas, obter_resumo_vendas=banco.obter_resumo_vendas,
                         converter_data_salva=banco.converter_data_salva, tabela=Tabela())
        for name, value in [('filtro_tipo', 'Todas as vendas'), ('filtro_mes', 'Todos os meses'), ('filtro_ano', 'Todos os anos'),
                            ('aviso_filtros', ''), ('texto_filtro_atual', ''), ('resumo_dinheiro', ''), ('resumo_pix', ''),
                            ('resumo_cartao', ''), ('resumo_total', ''), ('resumo_quantidade', ''), ('resumo_media', ''), ('resumo_participacao', ''), ('resumo_comparacao', '')]:
            n[name] = tk.StringVar(master=self.tcl, value=value)
        n['indicadores_visuais'] = {k: tk.StringVar(master=self.tcl) for k in ('total', 'quantidade', 'media', 'dinheiro', 'pix', 'cartao')}
        n['filtro_fechamento'] = tk.BooleanVar(master=self.tcl)
        n['filtros_dias_semana'] = {d: tk.BooleanVar(master=self.tcl) for d in range(7)}
        exec(compile(ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[]), 'main.py', 'exec'), n)
        n['filtro_ano'].trace_add('write', lambda *args: n['selecionar_ano_filtro']())
        n['filtro_mes'].trace_add('write', lambda *args: n['selecionar_mes_filtro']())
        n['filtro_fechamento'].trace_add('write', lambda *args: n['sincronizar_filtros']('fechamento'))
        for variavel in n['filtros_dias_semana'].values():
            variavel.trace_add('write', n['atualizar_aviso_filtros'])

    def verify(self, start=None, end=None, days=()):
        n = self.n
        n['atualizar_tabela']()
        expected = [v for v in banco.listar_vendas()
                    if (start is None or start <= v[1] <= end)
                    and (not days or date.fromisoformat(v[1]).weekday() in days)]
        self.assertEqual([v[0] for v in n['tabela'].rows.values()], [v[0] for v in expected])
        self.assertEqual(n['relatorio_atual']['vendas'], tuple(expected))
        totals = [sum(Decimal(str(v[i])) for v in expected) for i in (2, 3, 4)]
        self.assertEqual(n['resumo_total'].get(), f'Total geral: R$ {sum(totals):.2f}')
        for key, label, amount in zip(('resumo_dinheiro', 'resumo_pix', 'resumo_cartao'), ('Dinheiro', 'Pix', 'Cartão'), totals):
            self.assertEqual(n[key].get(), f'{label}: R$ {amount:.2f}')
        self.assertEqual(n['resumo_quantidade'].get(), f'Vendas encontradas: {len(expected)}')
        media = sum(totals) / len(expected) if expected else Decimal(0)
        self.assertIn(moeda(media), n['resumo_media'].get())

    def test_selecionar_ano_filtra_lista_e_resumo(self):
        self.verify()
        for year in (2025, 2026, 2027):
            self.n['filtro_ano'].set(str(year))
            self.n['selecionar_ano_filtro']()
            self.assertEqual(self.n['filtro_tipo'].get(), 'Ano')
            self.verify(f'{year}-01-01', f'{year}-12-31')
            self.assertEqual(self.n['texto_filtro_atual'].get(), f'Ano: {year}')

    def test_mes_ativa_filtro(self):
        for mode in ('Todas as vendas', 'Ano'):
            self.n['limpar_filtros']()
            if mode == 'Ano':
                self.n['filtro_ano'].set(str(date.today().year))
            self.n['filtro_mes'].set('Março')
            self.n['selecionar_mes_filtro']()
            self.assertEqual(self.n['filtro_tipo'].get(), 'Mês')
            self.verify(f'{date.today().year}-03-01', f'{date.today().year}-03-31')

    def test_fechamento_dias_e_troca_de_ano(self):
        n = self.n
        n['filtro_ano'].set('2026')
        n['filtro_mes'].set('Janeiro')
        n['filtro_fechamento'].set(True)
        n['filtros_dias_semana'][4].set(True)
        self.verify('2026-01-10', '2026-02-09', [4])
        n['filtro_ano'].set('2025')
        n['selecionar_ano_filtro']()
        self.assertEqual(n['filtro_tipo'].get(), 'Período de fechamento')
        self.verify('2025-01-10', '2025-02-09', [4])

    def test_comparacao_respeita_dias_da_semana(self):
        n = self.n
        n['filtro_ano'].set('2026')
        n['filtros_dias_semana'][4].set(True)
        self.verify('2026-01-01', '2026-12-31', [4])
        atual = calcular_indicadores(banco.listar_vendas('2026-01-01', '2026-12-31', [4]))
        anterior = calcular_indicadores(banco.listar_vendas('2025-01-01', '2025-12-31', [4]))
        self.assertEqual(n['resumo_comparacao'].get(), descrever_comparacao(atual, anterior, ('2025-01-01', '2025-12-31')))

    def test_exportacao_preserva_ultima_visualizacao_aplicada(self):
        n = self.n
        n['filtro_ano'].set('2026')
        self.verify('2026-01-01', '2026-12-31')
        snapshot = n['relatorio_atual']
        n['filtro_ano'].set('2025')  # Ainda não clicou Aplicar filtros.
        self.assertIs(n['relatorio_atual'], snapshot)
        self.assertIn(('Filtro aplicado', 'Ano: 2026'), snapshot['resumo'])
        self.assertTrue(all(v[1].startswith('2026-') for v in snapshot['vendas']))

    def test_limpar_restaura_todas_as_vendas(self):
        self.n['filtro_ano'].set('2026')
        self.n['filtros_dias_semana'][4].set(True)
        self.n['limpar_filtros']()
        self.assertEqual(self.n['filtro_ano'].get(), 'Todos os anos')
        self.verify()

    def test_todos_os_anos_limpa_mes_e_fechamento(self):
        n = self.n
        n['filtro_ano'].set('2026')
        n['filtro_mes'].set('Janeiro')
        n['filtro_fechamento'].set(True)
        n['filtro_ano'].set('Todos os anos')
        self.assertEqual(n['filtro_mes'].get(), 'Todos os meses')
        self.assertFalse(n['filtro_fechamento'].get())
        self.verify()

    def test_todos_os_meses_volta_para_ano(self):
        n = self.n
        n['filtro_ano'].set('2026')
        n['filtro_mes'].set('Janeiro')
        n['filtro_fechamento'].set(True)
        n['filtro_mes'].set('Todos os meses')
        self.assertFalse(n['filtro_fechamento'].get())
        self.verify('2026-01-01', '2026-12-31')

    def test_aviso_filtros_e_reversao_sem_aplicar(self):
        n = self.n
        self.verify()
        self.assertEqual(n['aviso_filtros'].get(), '')
        snapshot = n['relatorio_atual']
        n['filtro_ano'].set('2026')
        self.assertIn('Filtros alterados', n['aviso_filtros'].get())
        self.assertIs(n['relatorio_atual'], snapshot)
        n['filtro_ano'].set('Todos os anos')
        self.assertEqual(n['aviso_filtros'].get(), '')
        n['filtros_dias_semana'][4].set(True)
        self.assertTrue(n['aviso_filtros'].get())
        self.verify(days=[4])
        self.assertEqual(n['aviso_filtros'].get(), '')
        n['filtros_dias_semana'][6].set(True)
        self.assertTrue(n['aviso_filtros'].get())
        n['limpar_filtros']()
        self.assertEqual(n['aviso_filtros'].get(), '')

    def test_outubro_e_dezembro_fecham_no_mes_seguinte(self):
        n = self.n
        n['filtro_ano'].set('2026')
        n['filtro_mes'].set('Outubro')
        n['filtro_fechamento'].set(True)
        self.verify('2026-10-10', '2026-11-09')
        n['filtro_mes'].set('Dezembro')
        self.verify('2026-12-10', '2027-01-09')
        n['filtro_fechamento'].set(False)
        self.verify('2026-12-01', '2026-12-31')

    def test_eventos_ligados_aos_controles(self):
        tree = ast.parse((ROOT / 'ProgramFeira/main.py').read_text(encoding='utf-8'))
        bindings = {node.func.value.id: node.args[1].id for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'bind' and isinstance(node.func.value, ast.Name)
                    and len(node.args) == 2 and isinstance(node.args[1], ast.Name)}
        self.assertEqual(bindings['filtro_ano_combobox'], 'selecionar_ano_filtro')
        self.assertEqual(bindings['filtro_mes_combobox'], 'selecionar_mes_filtro')
