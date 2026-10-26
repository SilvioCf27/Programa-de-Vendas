import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SemanasInterfaceTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'), 'Sem sessão gráfica')
    def test_faixa_independente_historico_preferencia_e_virada_sem_perder_filtros(self):
        codigo = r'''
from datetime import date
import os, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'tests')
from dados_ficticios import criar_banco
criar_banco(Path(os.environ['PROGRAMFEIRA_DATA_DIR'])/'vendas.db')
import tkinter as tk
with patch.object(tk.Tk,'mainloop'):
    import ProgramFeira.main as a
from ProgramFeira.preferencias import carregar_periodo_inicial
class Dia(date):
    atual = date(2026,10,25)
    @classmethod
    def today(cls): return cls.atual
with patch.object(a,'date',Dia):
    a.cadastrar_venda('2026-10-23',10,20,30)
    a.cadastrar_venda('2026-10-25',0,0,0)
    a.cadastrar_venda('2026-10-26',70,0,0)
    a.aplicar_periodo_inicial(); a.atualizar_tabela(); a.janela.update()
    assert a.obter_filtros()[:2] == ('2026-10-10','2026-11-09')
    assert 'R$ 60,00' in a.resumo_semana.get() and '2 dias de feira' in a.resumo_semana.get()
    assert a.indicadores_visuais['total'].get() == 'R$ 280,00'  # Período completo, inclusive futuro.
    a.limpar_filtros()
    a.filtro_ano.set('2025'); a.atualizar_tabela()
    assert a.indicadores_visuais['total'].get() == 'R$ 185,50'
    assert 'R$ 60,00' in a.resumo_semana.get()
    grupos = a.painel_analises.historico_semanal
    assert sum(int(grupos.item(i,'values')[1]) for i in grupos.get_children()) == 3
    assert '2025' in a.painel_analises.filtro_semanal.get()
    a.filtro_ano.set('2026')  # Deixa filtro pendente, sem aplicar.
    pendente = a.assinatura_filtros()
    relatorio = a.relatorio_atual
    a.dia_semana_exibida = Dia.atual
    Dia.atual = date(2026,10,26)
    import sqlite3
    with patch.object(a, 'listar_vendas', side_effect=sqlite3.OperationalError('database is locked')):
        a.conferir_virada_do_dia()
    assert 'temporariamente indisponível' in a.resumo_semana.get()
    assert a.dia_semana_exibida == date(2026,10,25)
    a.conferir_virada_do_dia()
    assert 'R$ 70,00' in a.resumo_semana.get() and '1 dia de feira' in a.resumo_semana.get()
    assert a.assinatura_filtros() == pendente
    assert a.relatorio_atual is relatorio
    assert a.aviso_filtros.get()
    a.atualizar_apos_sincronizacao()
    assert 'R$ 70,00' in a.resumo_semana.get()
    cfg = a.abrir_configuracoes(); a.janela.update()
    cfg.periodo_inicial.set('Ano atual')
    cfg.seletor_inicio.event_generate('<<ComboboxSelected>>'); a.janela.update()
    assert carregar_periodo_inicial(a.CAMINHO_BANCO.parent) == 'Ano atual'
    cfg.destroy()
    a.aplicar_periodo_inicial(); a.atualizar_tabela()
    assert a.obter_filtros()[:2] == ('2026-01-01','2026-12-31')
    assert 'R$ 70,00' in a.resumo_semana.get()
a.janela.destroy()
'''
        with tempfile.TemporaryDirectory() as pasta:
            result = subprocess.run([sys.executable, '-c', codigo], cwd=ROOT,
                                    env={**os.environ, 'PROGRAMFEIRA_DATA_DIR': pasta}, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
