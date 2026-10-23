"""Gráfico horizontal com valores e quantidade explícitos, sem biblioteca externa."""
import tkinter as tk
from tkinter import ttk
from ProgramFeira.tendencias import evolucao
from ProgramFeira.resumos import moeda


class GraficoEvolucao(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style='Panel.TFrame', padding=16)
        self.vendas = []
        ttk.Label(self, text='Evolução das vendas', style='Section.TLabel').pack(anchor='w')
        self.tipo = tk.StringVar(value='Mês')
        seletor = ttk.Frame(self, style='Surface.TFrame')
        seletor.pack(fill='x', pady=10)
        ttk.Label(seletor, text='Agrupar por', style='Surface.TLabel').pack(side='left', padx=(0, 10))
        ttk.Combobox(seletor, textvariable=self.tipo, values=('Mês', 'Fechamento'), state='readonly', width=16).pack(side='left')
        ttk.Label(self, text='Usa os filtros aplicados em Vendas. Selecione Ano ou Todas as vendas para ver a evolução.\nAté 12 períodos consecutivos; sem registros é diferente de feira com valor zero. Fechamento segue a regra vigente de cada mês (inicialmente, 10 a 09).', style='Muted.TLabel', wraplength=780).pack(anchor='w', pady=(0, 10))
        self.linhas = ttk.Frame(self, style='Surface.TFrame')
        self.linhas.pack(fill='x')
        self.linhas.columnconfigure(1, weight=1)
        self.tipo.trace_add('write', lambda *args: self.atualizar(self.vendas))

    def atualizar(self, vendas):
        self.vendas = list(vendas)
        grupos = evolucao(self.vendas, self.tipo.get())
        for widget in self.linhas.winfo_children():
            widget.destroy()
        maximo = max((g['total'] for g in grupos), default=1) or 1
        for i, grupo in enumerate(grupos):
            ttk.Label(self.linhas, text=grupo['rotulo'], style='Surface.TLabel', width=10).grid(row=i, column=0, sticky='w', pady=5)
            ttk.Progressbar(self.linhas, maximum=float(maximo), value=float(grupo['total'])).grid(row=i, column=1, sticky='ew', padx=12)
            texto = f"{moeda(grupo['total'])} · {grupo['quantidade']} dias" if grupo['quantidade'] else 'Sem registros'
            ttk.Label(self.linhas, text=texto, style='Surface.TLabel', width=26).grid(row=i, column=2, sticky='e')
        if not grupos:
            ttk.Label(self.linhas, text='Sem registros para este gráfico.', style='Surface.TLabel').grid(row=0, column=0, columnspan=3)
