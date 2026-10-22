"""Barras que ocupam espaço apenas quando há conteúdo fora da área visível."""
from tkinter import ttk


class BarraDiscreta(ttk.Scrollbar):
    def set(self, primeiro, ultimo):
        necessario = float(primeiro) > .0001 or float(ultimo) < .9999
        visivel = bool(self.winfo_manager())
        if necessario and not visivel:
            self.grid()
        elif not necessario and visivel:
            self.grid_remove()
        super().set(primeiro, ultimo)
