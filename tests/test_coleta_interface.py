"""Finalizadores Tk não podem rodar no worker de rede/backup."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class ColetaInterfaceTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32','darwin'), 'Sem sessão gráfica')
    def test_finaliza_variaveis_na_interface_e_restaura_gc_apos_trabalhos_sobrepostos(self):
        script = r'''
import gc, threading
import tkinter as tk
from ProgramFeira.interface.coleta import suspender_coleta
root=tk.Tk()
principal=threading.get_ident()
finalizadores=[]
class Variavel(tk.StringVar):
    def __del__(self):
        finalizadores.append(threading.get_ident())
        super().__del__()
estado_inicial=gc.isenabled()
var=Variavel(root,value='teste')
var.ciclo=[var]
del var
primeiro=suspender_coleta()
segundo=suspender_coleta()
assert finalizadores and all(t==principal for t in finalizadores)
assert not gc.isenabled()
var=Variavel(root,value='descartada durante a tarefa')
var.ciclo=[var]
del var
assert len(finalizadores)==1
resultado=[]
def trabalho():
    for i in range(10000):
        ciclo=[]; ciclo.append(ciclo)
    resultado.append(gc.isenabled())
t=threading.Thread(target=trabalho)
t.start()
while t.is_alive(): root.update(); t.join(.001)
t.join()
primeiro()
assert len(finalizadores)==1
assert not gc.isenabled()
segundo(); segundo()
assert len(finalizadores)==2
assert resultado==[False]
assert gc.isenabled()==estado_inicial
assert all(t==principal for t in finalizadores)
root.destroy()
'''
        r=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],env=os.environ.copy(),capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
