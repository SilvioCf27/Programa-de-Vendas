"""Finanças pessoais e da feira, com consulta independente da aba Vendas."""
from datetime import date, timedelta
from decimal import Decimal
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from ProgramFeira import financeiro as f
from ProgramFeira.comparacao import interpretar_data
from ProgramFeira.resumos import moeda
from ProgramFeira.interface.visual import CORES
from ProgramFeira.interface.ajuda import rotulo_com_ajuda


def data_br(texto):
    return date.fromisoformat(texto).strftime('%d/%m/%Y')


def valor_br(centavos):
    return f'{Decimal(centavos) / 100:.2f}'.replace('.', ',')


class PainelFinanceiro(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=(0, 10, 0, 0))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self.tipo = tk.StringVar(value='Fechamento')
        hoje = date.today()
        # Abre no fechamento em andamento; o seletor continua nomeando o mês inicial.
        referencia = hoje if hoje.day >= 10 else hoje.replace(day=1) - timedelta(days=1)
        self.referencia = tk.StringVar(value=referencia.strftime('%d/%m/%Y'))
        consulta = ttk.Frame(self, style='Panel.TFrame', padding=10)
        consulta.grid(row=0, column=0, sticky='ew')
        rotulo_com_ajuda(consulta, 'Finanças', 'financas', 'Section.TLabel').pack(side='left', padx=(0, 18))
        ttk.Combobox(consulta, textvariable=self.tipo, values=('Semana', 'Mês', 'Fechamento', 'Ano'), state='readonly', width=13).pack(side='left')
        ttk.Label(consulta, text='Data de referência', style='Surface.TLabel').pack(side='left', padx=(12, 5))
        ttk.Entry(consulta, textvariable=self.referencia, width=12).pack(side='left')
        ttk.Button(consulta, text='Consultar', command=self.consultar, style='Primary.TButton').pack(side='left', padx=10)
        self.periodo = tk.StringVar()
        ttk.Label(consulta, textvariable=self.periodo, style='Surface.TLabel').pack(side='right')
        quadros = ttk.Frame(self)
        quadros.grid(row=1, column=0, sticky='ew', pady=8)
        self.valores = {}
        for i, (chave, titulo) in enumerate((('bruto', 'Vendas brutas'), ('taxas', 'Taxas informadas'), ('liquido', 'Vendas menos taxas'), ('despesas', 'Meta: despesas do período'), ('falta', 'Falta cobrir'), ('saldo', 'Saldo após despesas'))):
            coluna, linha = i % 3, i // 3
            quadros.columnconfigure(coluna, weight=1)
            card = ttk.Frame(quadros, style='Card.TFrame', padding=8)
            card.grid(row=linha, column=coluna, sticky='ew', padx=(0, 8 if coluna < 2 else 0), pady=3)
            rotulo_com_ajuda(card, titulo, 'saldo' if chave in ('saldo', 'falta', 'despesas') else 'taxas', 'CardTitle.TLabel').pack(anchor='w')
            self.valores[chave] = tk.StringVar()
            ttk.Label(card, textvariable=self.valores[chave], style='Section.TLabel').pack(anchor='w', pady=(3, 0))
        self.aviso = tk.StringVar()
        ttk.Label(self, textvariable=self.aviso, style='Aviso.TLabel', wraplength=1100).grid(row=2, column=0, sticky='w', pady=(0, 7))
        self.bind('<Configure>', lambda e: self._ajustar_aviso(e))
        self.abas = ttk.Notebook(self)
        self.abas.grid(row=3, column=0, sticky='nsew')
        pagina = ttk.Frame(self.abas, padding=10, style='Panel.TFrame')
        pagina.columnconfigure(0, weight=3)
        pagina.columnconfigure(1, weight=1)
        pagina.rowconfigure(1, weight=1)
        self.abas.add(pagina, text='Despesas e taxas por dia')
        rotulo_com_ajuda(pagina, 'Lançamentos do período', 'despesas', 'Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.tabela = self._tabela(pagina, ('data', 'tipo', 'descricao', 'valor', 'meio'), ('Data de pagamento', 'Tipo', 'Descrição / parcela', 'Valor', 'Pagamento'), 0)
        self.tabela.column('descricao', width=240, stretch=True)
        semanas = ttk.Frame(pagina, padding=(12, 0, 0, 0), style='Surface.TFrame')
        semanas.grid(row=0, column=1, rowspan=2, sticky='nsew')
        semanas.rowconfigure(1, weight=1)
        semanas.columnconfigure(0, weight=1)
        rotulo_com_ajuda(semanas, 'Despesas por semana', 'despesas', 'Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.tabela_semanas = self._tabela(semanas, ('semana', 'valor'), ('Segunda-feira', 'Despesas'), 0)
        acoes = ttk.Frame(pagina, style='Surface.TFrame')
        acoes.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(8, 0))
        for texto, comando in (('Nova despesa', lambda: self.formulario('despesa')), ('Nova taxa por dia', lambda: self.formulario('taxa')), ('Editar lançamento', self.editar), ('Excluir lançamento', self.excluir)):
            ttk.Button(acoes, text=texto, command=comando).pack(side='left', padx=(0, 8))
        self.tabela.bind('<Double-1>', lambda e: self.editar())
        anual = ttk.Frame(self.abas, style='Panel.TFrame', padding=10)
        anual.columnconfigure(0, weight=1)
        anual.rowconfigure(1, weight=1)
        self.abas.add(anual, text='Taxas históricas anuais')
        rotulo_com_ajuda(anual, 'Taxas anuais — sem rateio por mês', 'taxas', 'Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.tabela_anuais = self._tabela(anual, ('ano', 'inicio', 'fim', 'valor', 'natureza'), ('Ano', 'Cobertura inicial', 'Cobertura final', 'Taxa total', 'Natureza'), 0)
        botoes = ttk.Frame(anual, style='Surface.TFrame')
        botoes.grid(row=2, column=0, sticky='w', pady=(8, 0))
        for texto, comando in (('Adicionar taxa anual', lambda: self.formulario_anual()), ('Editar taxa anual', self.editar_anual), ('Excluir taxa anual', lambda: self.excluir(True))):
            ttk.Button(botoes, text=texto, command=comando).pack(side='left', padx=(0, 8))
        self.inicio = self.fim = None
        # Consulta apenas quando a aba for aberta; não penaliza a inicialização.

    def _ajustar_aviso(self, evento):
        if evento.widget is self:
            for widget in self.grid_slaves(row=2):
                widget.configure(wraplength=max(200, evento.width - 20))

    def _tabela(self, parent, colunas, titulos, coluna):
        quadro = ttk.Frame(parent, style='Surface.TFrame')
        quadro.grid(row=1, column=coluna, sticky='nsew')
        quadro.columnconfigure(0, weight=1)
        quadro.rowconfigure(0, weight=1)
        tabela = ttk.Treeview(quadro, columns=colunas, show='headings', height=3, selectmode='browse')
        tabela.grid(row=0, column=0, sticky='nsew')
        for nome, titulo in zip(colunas, titulos):
            tabela.heading(nome, text=titulo, anchor='center')
            tabela.column(nome, width=115, minwidth=80, anchor='center', stretch=True)
        scroll = ttk.Scrollbar(quadro, orient='vertical', command=tabela.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(quadro, orient='horizontal', command=tabela.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        tabela.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        return tabela

    def consultar(self):
        try:
            referencia = interpretar_data(self.referencia.get()).isoformat()
            inicio, fim = f.limites(self.tipo.get(), referencia)
            resumo = f.resumo_periodo(inicio, fim)
            linhas = f.listar_lancamentos(inicio, fim)
            anuais = f.listar_taxas_anuais()
        except (ValueError, OSError, sqlite3.Error) as erro:
            messagebox.showerror('Consulta não realizada', str(erro), parent=self)
            return
        self.inicio, self.fim = inicio, fim
        self.periodo.set(f'{data_br(inicio)} a {data_br(fim)}')
        for chave, variavel in self.valores.items():
            variavel.set(moeda(resumo[chave]))
        aviso = 'Saldo considera somente taxas e despesas cadastradas, inclusive futuras. Exportar vendas continua exportando apenas Vendas.'
        if resumo['parciais']:
            aviso += ' ATENÇÃO: taxa anual de ' + ', '.join(map(str, resumo['parciais'])) + ' não descontada neste recorte; saldo provisório, sem rateio.'
        else:
            aviso += ' Taxa não cadastrada não significa isenção.'
        if resumo['estimados']:
            aviso += ' Taxas estimadas em ' + ', '.join(map(str, resumo['estimados'])) + ': o resultado não é um valor líquido confirmado.'
        self.aviso.set(aviso)
        self.registros = {str(r['id']): r for r in linhas}
        self.anuais = {str(r['ano']): r for r in anuais}
        for tabela in (self.tabela, self.tabela_semanas, self.tabela_anuais):
            tabela.delete(*tabela.get_children())
        for r in linhas:
            descricao = r['descricao'] + (f" · {r['parcela']}/{r['parcelas']}" if r['parcelas'] > 1 else '')
            self.tabela.insert('', 'end', iid=str(r['id']), values=(data_br(r['data']), 'Despesa' if r['tipo'] == 'despesa' else 'Taxa', descricao, moeda(Decimal(r['valor_centavos']) / 100), r['meio']))
        for segunda, valor in f.semanas(linhas):
            self.tabela_semanas.insert('', 'end', values=(segunda.strftime('%d/%m/%Y'), moeda(Decimal(valor) / 100)))
        for r in anuais:
            self.tabela_anuais.insert('', 'end', iid=str(r['ano']), values=(r['ano'], data_br(r['inicio']), data_br(r['fim']), moeda(Decimal(r['valor_centavos']) / 100), r['natureza']))

    def editar(self):
        selecionado = self.tabela.selection()
        if selecionado:
            registro = self.registros[selecionado[0]]
            self.formulario(registro['tipo'], registro)
        else:
            messagebox.showinfo('Selecionar lançamento', 'Selecione uma linha para editar.', parent=self)

    def editar_anual(self):
        selecionado = self.tabela_anuais.selection()
        if selecionado:
            self.formulario_anual(self.anuais[selecionado[0]])
        else:
            messagebox.showinfo('Selecionar taxa', 'Selecione um ano para editar.', parent=self)

    def excluir(self, anual=False):
        tabela = self.tabela_anuais if anual else self.tabela
        selecionado = tabela.selection()
        if not selecionado:
            messagebox.showinfo('Selecionar lançamento', 'Selecione uma linha para excluir.', parent=self)
            return
        if messagebox.askyesno('Excluir lançamento', 'Excluir somente o lançamento selecionado? Será criado um backup. As outras parcelas serão preservadas.', parent=self):
            try:
                f.excluir_lancamento(int(selecionado[0]), anual)
                self.consultar()
            except (OSError, sqlite3.Error, ValueError) as erro:
                messagebox.showerror('Exclusão não realizada', str(erro), parent=self)

    def _janela(self, titulo):
        popup = tk.Toplevel(self)
        popup.title(titulo)
        popup.configure(background=CORES['fundo'])
        popup.transient(self.winfo_toplevel())
        popup.resizable(False, False)
        popup.bind('<Escape>', lambda e: popup.destroy())
        corpo = ttk.Frame(popup, padding=18)
        corpo.pack(fill='both', expand=True)
        corpo.columnconfigure(1, weight=1)
        return popup, corpo

    def _campo(self, corpo, linha, titulo, valor='', opcoes=None):
        variavel = tk.StringVar(value=valor)
        ttk.Label(corpo, text=titulo).grid(row=linha, column=0, sticky='w', padx=(0, 14), pady=6)
        widget = ttk.Combobox(corpo, textvariable=variavel, values=opcoes, state='readonly') if opcoes else ttk.Entry(corpo, textvariable=variavel, width=35)
        widget.grid(row=linha, column=1, sticky='ew', pady=6)
        return variavel

    def formulario(self, tipo, registro=None):
        r = registro or {}
        popup, corpo = self._janela(('Editar ' if r else 'Nova ') + ('despesa' if tipo == 'despesa' else 'taxa do cartão'))
        data = self._campo(corpo, 0, 'Pagamento / competência', data_br(r.get('data', date.today().isoformat())))
        descricao = self._campo(corpo, 1, 'Descrição', r.get('descricao', '' if tipo == 'despesa' else 'Taxa do cartão'))
        valor = self._campo(corpo, 2, 'Valor em R$ (por parcela)', valor_br(r['valor_centavos']) if r else '')
        meio = self._campo(corpo, 3, 'Pagamento', r.get('meio', 'Cartão de crédito' if tipo == 'taxa' else 'Dinheiro'), f.MEIOS)
        categoria = self._campo(corpo, 4, 'Categoria', r.get('categoria', 'Outros'), f.CATEGORIAS)
        parcelas = self._campo(corpo, 5, 'Quantidade de parcelas', '1') if not r and tipo == 'despesa' else None
        explicacao = ('Cartão: use a data em que a compra será paga na fatura. Para parcelas, informe o primeiro pagamento e o valor de CADA parcela.\nNão registre o pagamento da fatura outra vez. “Compromisso inicial” serve só para valores ainda não cadastrados.\nEditar ou excluir altera apenas a parcela selecionada.' if tipo == 'despesa' else 'Use a data da venda à qual a taxa corresponde. Informe a taxa exata em reais.\nUm ajuste anual e taxas diárias não podem cobrir a mesma data.')
        ttk.Label(corpo, text=explicacao, wraplength=490, style='Muted.TLabel', justify='left').grid(row=6, column=0, columnspan=2, sticky='w', pady=12)
        def salvar():
            try:
                quantidade = int(parcelas.get()) if parcelas else 1
                if quantidade > 1 and not messagebox.askyesno('Confirmar parcelas', f'Criar {quantidade} despesas mensais de R$ {valor.get()} cada? O campo é o valor da parcela, não o total da compra.', parent=popup):
                    return
                f.salvar_lancamento(tipo, interpretar_data(data.get()).isoformat(), descricao.get(), valor.get(), meio.get(), categoria.get(), quantidade, r.get('id'))
            except (ValueError, OSError, sqlite3.Error) as erro:
                messagebox.showerror('Lançamento não salvo', str(erro), parent=popup)
                return
            popup.destroy()
            self.consultar()
        ttk.Button(corpo, text='Salvar', command=salvar, style='Primary.TButton').grid(row=7, column=1, sticky='e')
        ttk.Button(corpo, text='Cancelar', command=popup.destroy).grid(row=7, column=0, sticky='w')
        return popup

    def formulario_anual(self, registro=None):
        r = registro or {}
        hoje = date.today()
        popup, corpo = self._janela('Taxa histórica anual')
        ano = self._campo(corpo, 0, 'Ano', str(r.get('ano', hoje.year)))
        if r:
            # Evita criar outro ano acidentalmente ao editar.
            corpo.grid_slaves(row=0, column=1)[0].configure(state='readonly')
        inicio = self._campo(corpo, 1, 'Cobertura inicial', data_br(r.get('inicio', f'{hoje.year}-01-01')))
        fim = self._campo(corpo, 2, 'Cobertura final', data_br(r.get('fim', hoje.isoformat())))
        valor = self._campo(corpo, 3, 'Taxa total em R$', valor_br(r['valor_centavos']) if r else '')
        natureza = self._campo(corpo, 4, 'Natureza', r.get('natureza', 'Confirmada'), ('Confirmada', 'Estimada'))
        observacao = self._campo(corpo, 5, 'Origem / observação', r.get('observacao', ''))
        ttk.Label(corpo, text='Informe as datas exatas cobertas pelo total. Ano completo: 01/01 a 31/12.\nAno em andamento: termine na data coberta pelo extrato. Ao atualizar, informe o TOTAL acumulado, não só a diferença.\nEste valor não será dividido entre meses ou dias.', wraplength=490, justify='left', style='Muted.TLabel').grid(row=6, column=0, columnspan=2, pady=12)
        def salvar():
            try:
                numero = int(ano.get())
                existente = any(a['ano'] == numero for a in f.listar_taxas_anuais())
                if existente and not messagebox.askyesno('Atualizar taxa anual', f'Substituir o total e a cobertura de {numero}? Um backup será criado.', parent=popup):
                    return
                f.salvar_taxa_anual(numero, interpretar_data(inicio.get()).isoformat(), interpretar_data(fim.get()).isoformat(), valor.get(), natureza.get(), observacao.get())
            except (ValueError, OSError, sqlite3.Error) as erro:
                messagebox.showerror('Taxa não salva', str(erro), parent=popup)
                return
            popup.destroy()
            self.consultar()
        ttk.Button(corpo, text='Salvar taxa anual', command=salvar, style='Primary.TButton').grid(row=7, column=1, sticky='e')
        ttk.Button(corpo, text='Cancelar', command=popup.destroy).grid(row=7, column=0, sticky='w')
        return popup
