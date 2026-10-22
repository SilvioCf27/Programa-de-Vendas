"""Revisão explícita das duas versões; nenhuma gravação ocorre neste painel."""
from decimal import Decimal
import tkinter as tk
from tkinter import ttk, messagebox
from ProgramFeira.resumos import moeda
from ProgramFeira.interface.visual import CORES

NOMES = {'vendas': 'Venda', 'financeiro_lancamentos': 'Lançamento financeiro', 'financeiro_taxas_anuais': 'Taxa anual'}
ROTULOS = {'data': 'Data', 'ano': 'Ano', 'inicio': 'Início da cobertura', 'fim': 'Fim da cobertura', 'tipo': 'Tipo',
           'descricao': 'Descrição', 'meio': 'Pagamento', 'categoria': 'Categoria', 'parcela': 'Parcela', 'parcelas': 'Parcelas',
           'natureza': 'Natureza', 'observacao': 'Observação', 'dinheiro_centavos': 'Dinheiro', 'pix_centavos': 'Pix',
           'cartao_centavos': 'Cartão', 'valor_centavos': 'Valor'}


def descrever(registro):
    if registro is None:
        return 'Registro excluído neste lado. Escolher esta versão confirma a exclusão.'
    linhas = []
    for chave, valor in registro.items():
        if chave not in ROTULOS:
            continue
        if chave in ('data', 'inicio', 'fim') and isinstance(valor, str):
            valor = '/'.join(reversed(valor.split('-')))
        if chave.endswith('_centavos'):
            valor = moeda(Decimal(valor) / 100)
        linhas.append(f'{ROTULOS[chave]}: {valor if valor is not None else ""}')
    return '\n'.join(linhas)


class RevisaoConflitos(tk.Toplevel):
    def __init__(self, parent, revisao, aplicar):
        super().__init__(parent)
        self.title('Conferir conflitos de sincronização')
        self.configure(background=CORES['fundo'])
        self.transient(parent)
        self.escolhas = {}
        self.revisao = revisao
        self.aplicar = aplicar
        self.geometry('900x650')
        self.minsize(700, 500)
        corpo = ttk.Frame(self, padding=16)
        corpo.pack(fill='both', expand=True)
        corpo.columnconfigure(0, weight=1)
        corpo.rowconfigure(3, weight=1)
        ttk.Label(corpo, text='Qual versão deve ser mantida?', style='Section.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(corpo, text='Escolha uma versão para cada registro. Nada será alterado até Aplicar escolhas.\nUm backup será criado antes da aplicação. Se algum dado mudar, será necessária uma nova revisão.', wraplength=830).grid(row=1, column=0, sticky='w', pady=10)
        self.lista = ttk.Treeview(corpo, columns=('registro', 'escolha'), show='headings', height=5)
        self.lista.heading('registro', text='Registro em conflito')
        self.lista.heading('escolha', text='Versão escolhida')
        self.lista.column('registro', width=490)
        self.lista.column('escolha', width=140)
        self.lista.grid(row=2, column=0, sticky='ew')
        barra = ttk.Scrollbar(corpo, orient='vertical', command=self.lista.yview)
        barra.grid(row=2, column=1, sticky='ns')
        self.lista.configure(yscrollcommand=barra.set)
        versoes = ttk.Frame(corpo)
        versoes.grid(row=3, column=0, sticky='nsew', pady=12)
        versoes.rowconfigure(1, weight=1)
        self.textos = {}
        for coluna, (lado, titulo) in enumerate((('pc', 'Neste PC'), ('nuvem', 'Na nuvem / celular'))):
            versoes.columnconfigure(coluna, weight=1)
            ttk.Label(versoes, text=titulo, style='Section.TLabel').grid(row=0, column=coluna, sticky='w')
            texto = tk.Text(versoes, wrap='word', width=35, height=11, background=CORES['fundo'], foreground=CORES['texto'], relief='flat')
            texto.grid(row=1, column=coluna, sticky='nsew', padx=(0, 10))
            self.textos[lado] = texto
        acoes = ttk.Frame(corpo)
        acoes.grid(row=4, column=0, sticky='ew')
        self.usar_pc = ttk.Button(acoes, text='Usar versão do PC', command=lambda: self.escolher('pc'))
        self.usar_pc.pack(side='left')
        self.usar_nuvem = ttk.Button(acoes, text='Usar versão da nuvem', command=lambda: self.escolher('nuvem'))
        self.usar_nuvem.pack(side='left', padx=8)
        self.botao_aplicar = ttk.Button(acoes, text='Aplicar escolhas', command=self.confirmar, style='Primary.TButton', state='disabled')
        self.botao_aplicar.pack(side='right')
        ttk.Button(acoes, text='Cancelar', command=self.destroy).pack(side='right', padx=8)
        self.aviso = tk.StringVar(value='Selecione um registro para conferir as duas versões.')
        ttk.Label(corpo, textvariable=self.aviso, wraplength=820).grid(row=5, column=0, sticky='w', pady=8)
        for i, r in enumerate(revisao['conflitos']):
            dados = r['pc'] or r['nuvem'] or {}
            nome = f"{NOMES[r['tabela']]} · {dados.get('data', dados.get('ano', r['id']))}"
            self.lista.insert('', 'end', iid=str(i), values=(nome, 'Pendente'))
        self.lista.bind('<<TreeviewSelect>>', lambda e: self.mostrar())
        self.lista.selection_set('0')
        self.mostrar()
        self.bind('<Escape>', lambda e: self.destroy())
        self.grab_set()

    def mostrar(self):
        if not self.lista.selection():
            return
        registro = self.revisao['conflitos'][int(self.lista.selection()[0])]
        for lado, texto in self.textos.items():
            texto.configure(state='normal')
            texto.delete('1.0', 'end')
            texto.insert('1.0', descrever(registro[lado]))
            texto.configure(state='disabled')
        for botao in (self.usar_pc, self.usar_nuvem):
            botao.configure(state='normal' if registro['resolvivel'] else 'disabled')
        self.aviso.set('Confira os valores e escolha qual versão manter.' if registro['resolvivel'] else 'São cadastros independentes na mesma data/ano. Revise os cadastros antes de sincronizar; nenhuma versão será sobrescrita por esta tela.')

    def escolher(self, lado):
        if not self.lista.selection():
            return
        item = self.lista.selection()[0]
        registro = self.revisao['conflitos'][int(item)]
        if not registro['resolvivel']:
            return
        self.escolhas[registro['tabela'] + ':' + registro['id']] = lado
        self.lista.set(item, 'escolha', 'PC' if lado == 'pc' else 'Nuvem')
        if len(self.escolhas) == len(self.revisao['conflitos']):
            self.botao_aplicar.configure(state='normal')

    def confirmar(self):
        if len(self.escolhas) != len(self.revisao['conflitos']):
            return
        if not messagebox.askyesno('Aplicar versões escolhidas', 'Manter as versões escolhidas e sincronizar os dados?\nUma escolha de registro excluído confirma a exclusão.\nUm backup dos dados locais será preservado.', parent=self):
            return
        escolhas = dict(self.escolhas)
        self.grab_release()
        self.destroy()
        self.aplicar(escolhas)
