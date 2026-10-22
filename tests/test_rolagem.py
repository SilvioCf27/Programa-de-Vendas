"""Confere a área útil e o acesso ao conteúdo em janelas grandes e pequenas."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RolagemTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'), 'Sem sessão gráfica')
    def test_barras_so_aparecem_quando_necessarias(self):
        script = r'''
import tkinter as tk
from unittest.mock import patch
with patch.object(tk.Tk, 'mainloop'):
    import ProgramFeira.main as a
a.janela.geometry('1280x900'); a.janela.update()
assert a.container_tabela.winfo_width() >= a.area_tabela.winfo_width() - 32
assert not a.scroll_horizontal.winfo_manager()
assert not a.scroll_vertical.winfo_manager()
for i in range(80):
    a.tabela.insert('', 'end', values=(i, '01/01/2026', 'Quinta-feira', 'R$ 10,00', 'R$ 0,00', 'R$ 0,00', 'R$ 10,00'))
a.janela.update()
assert a.scroll_vertical.winfo_manager()
a.janela.geometry('940x660'); a.janela.update()
assert a.scroll_filtros.winfo_manager()
a.canvas_filtros.yview_moveto(1); a.janela.update()
assert a.canvas_filtros.yview()[1] >= .999
a.janela.geometry('1280x900'); a.janela.update()
# Após voltar à janela grande, o filtro retorna ao topo sem espaço vazio.
if a.frame_filtros.winfo_height() <= a.canvas_filtros.winfo_height():
    assert not a.scroll_filtros.winfo_manager()
    assert a.canvas_filtros.yview()[0] == 0
for item in a.tabela.get_children():
    a.tabela.delete(item)
a.janela.update()
assert not a.scroll_vertical.winfo_manager()
a.janela.destroy()
'''
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-c', script],
                                    cwd=Path(__file__).resolve().parents[1],
                                    env={**os.environ, 'PROGRAMFEIRA_DATA_DIR': folder},
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
