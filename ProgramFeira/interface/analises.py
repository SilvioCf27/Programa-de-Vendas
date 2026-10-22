"""Painel de leitura dos dados da seleção aplicada na aba Vendas."""
from decimal import Decimal
import tkinter as tk
from tkinter import ttk
from ProgramFeira.database.banco import converter_data_salva
from ProgramFeira.resumos import calcular_indicadores, moeda
from ProgramFeira.interface.visual import CORES
from ProgramFeira.interface.ajuda import rotulo_com_ajuda
from ProgramFeira.interface.painel_comparacao import PainelComparacao
from ProgramFeira.interface.grafico import GraficoEvolucao

DIAS = ('Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo')


def agrupar_dias(vendas):
    grupos = [[] for _ in range(7)]
    for venda in vendas:
        data = converter_data_salva(venda[1])
        if data:
            grupos[data.weekday()].append(venda)
    return [(nome, calcular_indicadores(grupo)) for nome, grupo in zip(DIAS, grupos)]


class PainelAnalises(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.abas = ttk.Notebook(self)
        self.abas.grid(row=0, column=0, sticky='nsew')
        pagina_resumo = ttk.Frame(self.abas)
        pagina_resumo.columnconfigure(0, weight=1)
        pagina_resumo.rowconfigure(0, weight=1)
        self.abas.add(pagina_resumo, text='Resumo do período')
        self.comparador = PainelComparacao(self.abas)
        self.abas.add(self.comparador, text='Comparar A e B')
        self.canvas = tk.Canvas(pagina_resumo, highlightthickness=0, background=CORES['fundo'], height=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(pagina_resumo, orient='vertical', command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scroll.set)
        self.corpo = ttk.Frame(self.canvas, padding=(0, 14, 0, 0))
        janela = self.canvas.create_window((0, 0), window=self.corpo, anchor='nw')
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(janela, width=e.width))
        self.corpo.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.corpo.columnconfigure(0, weight=1)
        cabecalho = ttk.Frame(self.corpo, style='Panel.TFrame', padding=16)
        cabecalho.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        cabecalho.columnconfigure(0, weight=1)
        rotulo_com_ajuda(cabecalho, 'Análises do período', 'analises', 'Section.TLabel').grid(row=0, column=0, sticky='w')
        self.filtro = tk.StringVar()
        ttk.Label(cabecalho, textvariable=self.filtro, style='Filtro.TLabel', wraplength=800).grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.aviso = tk.StringVar()
        ttk.Label(cabecalho, textvariable=self.aviso, style='Aviso.TLabel', wraplength=800).grid(row=2, column=0, columnspan=2, sticky='w', pady=(5, 0))
        ttk.Button(cabecalho, text='Alterar filtros na aba Vendas', command=lambda: parent.master.select(0)).grid(row=0, column=1, rowspan=2, sticky='e', padx=(12, 0))
        comparacao = ttk.Frame(self.corpo, style='Panel.TFrame', padding=16)
        comparacao.grid(row=1, column=0, sticky='ew', pady=(0, 12))
        rotulo_com_ajuda(comparacao, 'Comparação com o período anterior', 'comparacao', 'Section.TLabel').pack(anchor='w')
        self.comparacao = tk.StringVar()
        detalhe = ttk.Label(comparacao, textvariable=self.comparacao, style='Surface.TLabel', wraplength=800, justify='left')
        detalhe.pack(anchor='w', pady=(10, 0))
        comparacao.bind('<Configure>', lambda e: detalhe.configure(wraplength=max(100, e.width - 32)))
        self.quadros = ttk.Frame(self.corpo)
        self.quadros.grid(row=2, column=0, sticky='ew')
        self.quadros.columnconfigure(0, weight=1)
        self.quadros.columnconfigure(1, weight=1)
        pagamentos = ttk.Frame(self.quadros, style='Panel.TFrame', padding=16)
        pagamentos.grid(row=0, column=0, sticky='new', padx=(0, 12), pady=(0, 12))
        rotulo_com_ajuda(pagamentos, 'Formas de pagamento', 'participacao', 'Section.TLabel').pack(anchor='w', pady=(0, 10))
        self.pagamentos = self._tabela(pagamentos, ('forma', 'valor', 'participacao'), ('Forma de pagamento', 'Total registrado', 'Participação'), 3)
        semana = ttk.Frame(self.quadros, style='Panel.TFrame', padding=16)
        semana.grid(row=0, column=1, sticky='new')
        rotulo_com_ajuda(semana, 'Resultados por dia da semana', 'por_dia', 'Section.TLabel').pack(anchor='w', pady=(0, 10))
        self.semana = self._tabela(semana, ('dia', 'quantidade', 'total', 'media'), ('Dia da semana', 'Dias de feira', 'Total', 'Média por dia'), 7)
        self.grafico = GraficoEvolucao(self.corpo)
        self.grafico.grid(row=3, column=0, sticky='ew', pady=12)
        self._colunas = None
        def organizar(event):
            colunas = 2 if event.width >= 1100 else 1
            if colunas == self._colunas:
                return
            self._colunas = colunas
            self.quadros.columnconfigure(1, weight=1 if colunas == 2 else 0)
            pagamentos.grid_configure(row=0, column=0, padx=(0, 12 if colunas == 2 else 0))
            semana.grid_configure(row=0 if colunas == 2 else 1, column=1 if colunas == 2 else 0)
        self.quadros.bind('<Configure>', organizar)
        def rolar(event):
            if str(event.widget).startswith(str(pagina_resumo)):
                numero = getattr(event, 'num', None)
                unidades = (-1 if numero == 4 else 1) if numero in (4, 5) else (-1 if event.delta > 0 else 1)
                self.canvas.yview_scroll(unidades, 'units')
                return 'break'
        for evento in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self.winfo_toplevel().bind(evento, rolar, add='+')


    def _tabela(self, parent, colunas, titulos, altura):
        tabela = ttk.Treeview(parent, columns=colunas, show='headings', height=altura, selectmode='none')
        tabela.pack(fill='x')
        for coluna, titulo in zip(colunas, titulos):
            tabela.heading(coluna, text=titulo, anchor='center')
            tabela.column(coluna, width=130, minwidth=95, anchor='center')
        return tabela

    def atualizar(self, vendas, filtro, comparacao):
        self.grafico.atualizar(vendas)
        self.filtro.set(filtro)
        self.comparacao.set(comparacao)
        indicadores = calcular_indicadores(vendas)
        for tabela in (self.pagamentos, self.semana):
            for item in tabela.get_children():
                tabela.delete(item)
        for i, nome in enumerate(('Dinheiro', 'Pix', 'Cartão')):
            total = sum((Decimal(str(v[i + 2])) for v in vendas), Decimal(0))
            percentual = f"{indicadores['participacoes'][i]:.1f}%".replace('.', ',') if indicadores['total'] else 'Indisponível (total zero)'
            self.pagamentos.insert('', 'end', values=(nome, moeda(total), percentual))
        for nome, grupo in agrupar_dias(vendas):
            self.semana.insert('', 'end', values=(nome, grupo['quantidade'], moeda(grupo['total']), moeda(grupo['media'])))
