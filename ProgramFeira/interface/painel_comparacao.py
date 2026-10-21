"""Seleção de dois períodos com resultados lado a lado, apenas para consulta."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import tkinter as tk
from tkinter import ttk
from ProgramFeira.database import banco
from ProgramFeira.comparacao import limites_comparacao, comparar_registros
from ProgramFeira.resumos import moeda
from ProgramFeira.interface.ajuda import rotulo_com_ajuda
from ProgramFeira.interface.visual import CORES

MESES = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')


class SeletorPeriodo(ttk.Frame):
    def __init__(self, parent, titulo, referencia, mudou):
        super().__init__(parent, style='Panel.TFrame', padding=14)
        self.columnconfigure(1, weight=1)
        rotulo_com_ajuda(self, titulo, 'comparacao_livre', 'Section.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))
        self.tipo = tk.StringVar(value='Mês')
        self.ano = tk.StringVar(value=str(referencia.year))
        self.mes = tk.StringVar(value=MESES[referencia.month - 1])
        self.inicio = tk.StringVar(value=referencia.strftime('%d/%m/%Y'))
        self.fim = tk.StringVar(value=referencia.strftime('%d/%m/%Y'))
        ttk.Label(self, text='Comparar por', style='Surface.TLabel').grid(row=1, column=0, sticky='w', padx=(0, 8))
        ttk.Combobox(self, textvariable=self.tipo, values=('Data', 'Mês', 'Fechamento', 'Intervalo'), state='readonly', width=18).grid(row=1, column=1, sticky='ew', pady=(0, 8))
        anos = sorted(set(banco.listar_anos_vendas()) | {date.today().year - 1, date.today().year, date.today().year + 1})
        self.linha_mes = ttk.Frame(self, style='Surface.TFrame')
        self.linha_mes.grid(row=2, column=0, columnspan=2, sticky='ew')
        self.linha_mes.columnconfigure(0, weight=1)
        ttk.Combobox(self.linha_mes, textvariable=self.mes, values=MESES, state='readonly', width=13).grid(row=0, column=0, sticky='ew', padx=(0, 8))
        ttk.Combobox(self.linha_mes, textvariable=self.ano, values=anos, state='readonly', width=7).grid(row=0, column=1)
        self.linha_datas = ttk.Frame(self, style='Surface.TFrame')
        self.linha_datas.grid(row=3, column=0, columnspan=2, sticky='ew')
        self.label_inicio = ttk.Label(self.linha_datas, text='Data (DD/MM/AAAA)', style='Surface.TLabel')
        self.label_inicio.grid(row=0, column=0, sticky='w')
        ttk.Entry(self.linha_datas, textvariable=self.inicio, width=15).grid(row=1, column=0, sticky='w', padx=(0, 10))
        self.label_fim = ttk.Label(self.linha_datas, text='Até (inclusive)', style='Surface.TLabel')
        self.label_fim.grid(row=0, column=1, sticky='w')
        self.entrada_fim = ttk.Entry(self.linha_datas, textvariable=self.fim, width=15)
        self.entrada_fim.grid(row=1, column=1, sticky='w')
        self.tipo.trace_add('write', lambda *args: (self.ajustar(), mudou()))
        for variavel in (self.ano, self.mes, self.inicio, self.fim):
            variavel.trace_add('write', lambda *args: mudou())
        self.ajustar()

    def ajustar(self):
        datas = self.tipo.get() in ('Data', 'Intervalo')
        if datas:
            self.linha_mes.grid_remove()
            self.linha_datas.grid()
            self.label_inicio.configure(text='De (DD/MM/AAAA)' if self.tipo.get() == 'Intervalo' else 'Data (DD/MM/AAAA)')
            for widget in (self.label_fim, self.entrada_fim):
                widget.grid() if self.tipo.get() == 'Intervalo' else widget.grid_remove()
        else:
            self.linha_datas.grid_remove()
            self.linha_mes.grid()

    def limites(self):
        return limites_comparacao(self.tipo.get(), self.ano.get(), MESES.index(self.mes.get()) + 1, self.inicio.get(), self.fim.get())


class PainelComparacao(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=(14, 14))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, background=CORES['fundo'], highlightthickness=0, height=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        barra = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        barra.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=barra.set)
        corpo = ttk.Frame(self.canvas)
        janela = self.canvas.create_window((0, 0), anchor='nw', window=corpo)
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(janela, width=e.width))
        corpo.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        corpo.columnconfigure(0, weight=1)
        corpo.columnconfigure(1, weight=1)
        def rolar(event):
            if str(event.widget).startswith(str(self)):
                numero = getattr(event, 'num', None)
                unidades = (-1 if numero == 4 else 1) if numero in (4, 5) else (-1 if event.delta > 0 else 1)
                self.canvas.yview_scroll(unidades, 'units')
                return 'break'
        for evento in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self.winfo_toplevel().bind(evento, rolar, add='+')
        rotulo_com_ajuda(corpo, 'Comparar dois períodos', 'comparacao_livre', 'Section.TLabel').grid(row=0, column=0, columnspan=2, sticky='w')
        ttk.Label(corpo, text='Consulta independente: todos os dias da semana. Os cartões do topo continuam mostrando os filtros de Vendas.', style='Muted.TLabel', wraplength=850).grid(row=1, column=0, columnspan=2, sticky='w', pady=(8, 12))
        hoje = date.today()
        anterior = hoje.replace(day=1) - timedelta(days=1)
        self.seletor_a = SeletorPeriodo(corpo, 'Período A · referência', anterior, self.marcar_pendente)
        self.seletor_b = SeletorPeriodo(corpo, 'Período B · comparar', hoje, self.marcar_pendente)
        self.seletor_a.grid(row=2, column=0, sticky='nsew', padx=(0, 8))
        self.seletor_b.grid(row=2, column=1, sticky='nsew')
        linha = ttk.Frame(corpo)
        linha.grid(row=3, column=0, columnspan=2, sticky='ew', pady=10)
        ttk.Button(linha, text='Comparar A e B', style='Primary.TButton', command=self.comparar).pack(side='left')
        self.aviso = tk.StringVar(value='Escolha A e B e clique em Comparar.')
        ttk.Label(linha, textvariable=self.aviso, style='Muted.TLabel', wraplength=650).pack(side='left', padx=(12, 0))
        self.periodos = tk.StringVar()
        ttk.Label(corpo, textvariable=self.periodos, style='Muted.TLabel', wraplength=850, justify='left').grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 8))
        self.tabela = ttk.Treeview(corpo, columns=('indicador', 'a', 'b'), show='headings', height=7, selectmode='none')
        self.tabela.grid(row=5, column=0, columnspan=2, sticky='nsew')
        for coluna, titulo in zip(('indicador', 'a', 'b'), ('Indicador', 'Período A', 'Período B')):
            self.tabela.heading(coluna, text=titulo, anchor='center')
            self.tabela.column(coluna, width=180, minwidth=140, anchor='center')
        self.resultado = tk.StringVar()
        ttk.Label(corpo, textvariable=self.resultado, style='Muted.TLabel', wraplength=850, justify='left').grid(row=6, column=0, columnspan=2, sticky='w', pady=(10, 0))
        self.ultima_comparacao = None
        self.ultima_selecao = None

    def marcar_pendente(self):
        if hasattr(self, 'aviso'):
            self.aviso.set('Seleção alterada. Clique em Comparar para atualizar os resultados.')

    def comparar(self):
        try:
            a, b = self.seletor_a.limites(), self.seletor_b.limites()
            # Valida as duas seleções antes de consultar ou substituir resultados.
            dados_a, dados_b = banco.listar_vendas(*a), banco.listar_vendas(*b)
            resumo = comparar_registros(dados_a, dados_b)
        except (ValueError, TypeError) as erro:
            self.aviso.set(f'Não atualizado: {erro}')
            return
        linhas = [('Total registrado', moeda(resumo['a']['total']), moeda(resumo['b']['total'])),
                  ('Dias de feira (inclui zerados)', resumo['a']['quantidade'], resumo['b']['quantidade']),
                  ('Média por dia de feira', moeda(resumo['a']['media']), moeda(resumo['b']['media']))]
        for i, nome in enumerate(('Dinheiro', 'Pix', 'Cartão')):
            linhas.append((nome, moeda(resumo['pagamentos_a'][i]), moeda(resumo['pagamentos_b'][i])))
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for linha in linhas:
            self.tabela.insert('', 'end', values=linha)
        formatar = lambda d: date.fromisoformat(d).strftime('%d/%m/%Y')
        self.periodos.set(f'A: {formatar(a[0])} a {formatar(a[1])}  |  B: {formatar(b[0])} a {formatar(b[1])}')
        variacao = resumo['motivo'] if resumo['variacao'] is None else ('Variação de B em relação a A: ' + f"{resumo['variacao'].quantize(Decimal('.1'), rounding=ROUND_HALF_UP):+.1f}%".replace('.', ','))
        self.resultado.set(f"Diferença de total (B menos A): {moeda(resumo['diferenca'])}. {variacao}")
        self.aviso.set('Comparação atualizada. Dias sem registro não são contados; registros zerados são contados.')
        self.ultima_selecao = (a, b)
        self.ultima_comparacao = resumo
