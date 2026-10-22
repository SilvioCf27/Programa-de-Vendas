"""Indicador visual de participação, sem eventos ou cálculos financeiros."""
import tkinter as tk
from ProgramFeira.interface.visual import CORES, cores_indicadores, misturar


class BarraParticipacao(tk.Canvas):
    def __init__(self, parent, chave):
        super().__init__(parent, height=8, width=1, highlightthickness=0)
        self.chave, self.valor = chave, 0
        self.bind('<Configure>', self.atualizar_aparencia)

    def __setitem__(self, chave, valor):
        if chave == 'value':
            self.valor = max(0, min(100, float(valor)))
            self.atualizar_aparencia()
        else:
            super().__setitem__(chave, valor)

    def atualizar_aparencia(self, event=None):
        cor, fundo, _ = cores_indicadores(CORES)[self.chave]
        self.configure(background=fundo)
        self.delete('all')
        largura = max(8, self.winfo_width())
        self.create_line(4, 4, largura - 4, 4, width=7, capstyle='round',
                         fill=misturar(fundo, cor, .18))
        if self.valor:
            self.create_line(4, 4, 4 + (largura - 8) * self.valor / 100, 4,
                             width=7, capstyle='round', fill=cor)
