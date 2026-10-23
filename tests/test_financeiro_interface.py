"""Datas e taxas semanais pelos controles reais, com banco isolado."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class FinanceiroInterfaceTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'), 'Sem sessão gráfica')
    def test_datas_parcelas_taxas_e_previa_de_regra(self):
        script = r'''
import tkinter as tk
from unittest.mock import patch
with patch.object(tk.Tk, 'mainloop'):
    import ProgramFeira.main as a
from ProgramFeira import financeiro as f
a.janela.update()
a.abas.select(2); a.janela.update()
p = a.painel_financeiro
popup = p.formulario('despesa')
corpo = popup.winfo_children()[0]
def campo(linha, texto):
    widget = corpo.grid_slaves(row=linha, column=1)[0]
    if hasattr(widget, 'set'): widget.set(texto)
    else: widget.delete(0, 'end'); widget.insert(0, texto)
campo(0, '09/09/2026'); campo(1, 'Compra de exemplo'); campo(2, '30,00'); campo(3, 'Cartão de crédito'); campo(5, '3')
cd = corpo.grid_slaves(row=0, column=1)[0]
assert cd.variavel.get() == '09/09/2026'
assert not cd.grid_slaves(row=2, column=0)
assert cd.variavel.get() == '09/09/2026'
with patch.object(a.messagebox, 'askyesno', return_value=True):
    corpo.grid_slaves(row=7, column=1)[0].invoke()
assert sorted(r['data'] for r in f.listar_lancamentos('2000-01-01','2199-12-31')) == ['2026-10-09','2026-11-09','2026-12-09']
linhas = sorted(f.listar_lancamentos('2000-01-01','2199-12-31'), key=lambda r:r['parcela'])
assert [r['valor_centavos'] for r in linhas] == [1000,1000,1000]
popup = p.formulario('despesa', linhas[2])
corpo = popup.winfo_children()[0]
assert corpo.grid_slaves(row=0,column=1)[0].variavel.get() == '09/09/2026'
assert corpo.grid_slaves(row=2,column=1)[0].get() == '30,00'
assert corpo.grid_slaves(row=5,column=1)[0].get() == '3'
campo(2,'100,00')
with patch.object(a.messagebox, 'askyesno', return_value=True):
    corpo.grid_slaves(row=7, column=1)[0].invoke()
novas = sorted(f.listar_lancamentos('2000-01-01','2199-12-31'), key=lambda r:r['parcela'])
assert [r['id'] for r in novas] == [r['id'] for r in linhas]
assert [r['valor_centavos'] for r in novas] == [3333,3333,3334]
popup = p.formulario_taxas()
popup.seletor_semana.referencia.set('09/10/2026')
a.janela.update()
popup.campos_taxas['2026-10-09'].set('2,00')
popup.campos_taxas['2026-10-11'].set('3,00')
popup.winfo_children()[0].grid_slaves(row=5, column=1)[0].invoke()
assert [(r['data'],r['valor_centavos']) for r in sorted(f.listar_lancamentos('2000-01-01','2199-12-31'),key=lambda r:r['data']) if r['tipo']=='taxa'] == [('2026-10-09',200),('2026-10-11',300)]
from ProgramFeira.interface.configuracao_fechamento import ConfiguracaoFechamento
recebidos=[]
popup=ConfiguracaoFechamento(a.janela,{'versao':0,'historico':[]},lambda *args: recebidos.append(args))
popup.ano.set('2090'); popup.mes.set('Novembro'); popup.dia.set('14')
assert '14/11/2090' in popup.previa.get()
popup.salvar.invoke()
assert recebidos[0][1:] == (0,'2090-11-01',14)
popup.destroy(); a.janela.destroy()
'''
        with tempfile.TemporaryDirectory() as pasta:
            r = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1],
                               env={**os.environ, 'PROGRAMFEIRA_DATA_DIR': pasta}, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
