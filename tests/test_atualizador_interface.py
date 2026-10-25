import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AtualizadorInterfaceTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'), 'Sem sessão gráfica')
    def test_consulta_nao_bloqueia_interface_e_formularios_impedem_instalacao(self):
        codigo = r'''
import os, time, threading
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
with patch.object(tk.Tk, 'mainloop'):
    import ProgramFeira.main as app
app.janela.update()
p = app.atualizacoes
assert not p.disponivel  # Executando fonte, não o binário.
p.disponivel = True
popup = p.abrir()
app.janela.update()
app.verificar_disponibilidade_atualizacao(popup)
try:
    app.verificar_formulario_sincronizacao()
except ValueError:
    pass
else:
    raise AssertionError('A sincronização deve aguardar a janela modal')
liberar = threading.Event()
eventos = []
def consulta():
    assert liberar.wait(5)
    return {'versao':'v999.0.0'}
def aguardar():
    prazo = time.monotonic() + 5
    while p.ocupado and time.monotonic() < prazo:
        app.janela.update(); time.sleep(.01)
    assert not p.ocupado
with patch('ProgramFeira.atualizador.consultar', consulta):
    p.verificar_agora()
    app.janela.after(1, lambda: eventos.append('interface ativa'))
    prazo = time.monotonic() + 1
    while not eventos and time.monotonic() < prazo:
        app.janela.update(); time.sleep(.01)
    assert eventos and p.ocupado
    p.fechar()
    assert popup.winfo_exists(), 'Não pode fechar durante a preparação'
    liberar.set(); aguardar()
assert p.release['versao'] == 'v999.0.0'
assert '999.0.0' in p.status.get()
app.formulario.deiconify(); app.janela.update()
with patch('ProgramFeira.interface.painel_atualizacao.messagebox.askyesno', return_value=True), patch('ProgramFeira.atualizador.preparar') as preparar:
    p.baixar()
    preparar.assert_not_called()
app.formulario.withdraw(); app.janela.update()
with patch('ProgramFeira.interface.painel_atualizacao.messagebox.askyesno', return_value=True), patch('ProgramFeira.atualizador.preparar', side_effect=ValueError('Hash inválido')), patch('ProgramFeira.atualizador.instalar') as instalar:
    p.baixar(); aguardar()
    instalar.assert_not_called()
    assert 'Hash inválido' in p.status.get()
p.fechar()
app.janela.destroy()
'''
        with tempfile.TemporaryDirectory() as pasta:
            result = subprocess.run([sys.executable, '-c', codigo], cwd=ROOT,
                                    env={**os.environ, 'PROGRAMFEIRA_DATA_DIR': pasta}, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
