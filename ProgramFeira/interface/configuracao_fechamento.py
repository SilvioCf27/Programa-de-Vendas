"""Prévia de uma regra futura; o salvamento é delegado à conexão autenticada."""
from datetime import date
import tkinter as tk
from tkinter import ttk
from ProgramFeira import fechamento
from ProgramFeira.interface.seletor_financeiro import MESES
from ProgramFeira.interface.visual import CORES


class ConfiguracaoFechamento(tk.Toplevel):
    def __init__(self, parent, config, salvar):
        super().__init__(parent)
        self.title('Configurar fechamento')
        self.configure(background=CORES['fundo'])
        self.transient(parent)
        self.resizable(False, False)
        hoje = date.today()
        ano, mes = divmod(hoje.year * 12 + hoje.month, 12)
        mes += 1
        self.config = config
        self.dia = tk.StringVar(value=str(fechamento.dia_no_mes(ano, mes)))
        self.ano = tk.StringVar(value=str(ano))
        self.mes = tk.StringVar(value=MESES[mes - 1])
        corpo = ttk.Frame(self, padding=20)
        corpo.pack(fill='both', expand=True)
        ttk.Label(corpo, text='Regra dos próximos fechamentos', style='Title.TLabel').grid(row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(corpo, text='Fechamento é diferente do prazo para pagar a fatura.\nA regra só pode começar em um mês futuro. Os períodos já encerrados serão preservados.\nUse a mesma versão atualizada no PC e no PWA.', wraplength=570).grid(row=1, column=0, columnspan=3, sticky='w', pady=12)
        self.campos = []
        for coluna, (rotulo, var, opcoes, largura) in enumerate((('Dia', self.dia, tuple(range(1, 32)), 5), ('Primeira fatura com a nova regra', self.mes, MESES, 14), ('Ano', self.ano, tuple(range(ano, ano + 8)), 7))):
            ttk.Label(corpo, text=rotulo).grid(row=2, column=coluna, sticky='w', padx=(0, 12))
            campo = ttk.Combobox(corpo, textvariable=var, values=opcoes, width=largura, state='readonly')
            campo.grid(row=3, column=coluna, sticky='w', padx=(0, 12))
            self.campos.append(campo)
        self.previa = tk.StringVar()
        ttk.Label(corpo, textvariable=self.previa, wraplength=570, justify='left').grid(row=4, column=0, columnspan=3, sticky='w', pady=12)
        historico = 'Regra inicial: dia 09.' + ''.join(f'\nA partir de {r["vigencia"][:7]}: dia {r["dia"]:02d}.' for r in config['historico'])
        ttk.Label(corpo, text=historico, wraplength=570, style='Muted.TLabel').grid(row=5, column=0, columnspan=3, sticky='w')
        ttk.Label(corpo, text='Um dia que não existe no mês usa o último dia (por exemplo, em fevereiro).\nA mudança pode encurtar ou alongar o período ainda aberto. Não altera valores nem move parcelas já cadastradas; confira os vencimentos futuros.', wraplength=570, style='Muted.TLabel').grid(row=6, column=0, columnspan=3, sticky='w', pady=12)
        self.erro = tk.StringVar()
        ttk.Label(corpo, textvariable=self.erro, wraplength=570).grid(row=7, column=0, columnspan=3, sticky='w')
        self.cancelar = ttk.Button(corpo, text='Cancelar', command=self.destroy)
        self.cancelar.grid(row=8, column=0, sticky='w', pady=(10, 0))
        self.salvar = ttk.Button(corpo, text='Salvar nova regra', style='Primary.TButton', command=lambda: self.enviar(salvar))
        self.salvar.grid(row=8, column=2, sticky='e', pady=(10, 0))
        self.em_envio = False
        self.protocol('WM_DELETE_WINDOW', lambda: None if self.em_envio else self.destroy())
        self.traces = [(var, var.trace_add('write', self.atualizar)) for var in (self.dia, self.ano, self.mes)]
        self.bind('<Destroy>', self.limpar, add='+')
        self.atualizar()
        self.grab_set()

    def parametros(self):
        return f'{int(self.ano.get()):04d}-{MESES.index(self.mes.get()) + 1:02d}-01', int(self.dia.get())

    def atualizar(self, *args):
        try:
            vigencia, dia = self.parametros()
            proposta = fechamento.propor(self.config, vigencia, dia)
            ano, mes = int(self.ano.get()), MESES.index(self.mes.get()) + 1
            anterior = date(ano, mes, 1).replace(day=1)
            from datetime import timedelta
            anterior -= timedelta(days=1)
            periodos = [fechamento.periodo(anterior.year, anterior.month, proposta['historico']), fechamento.periodo(ano, mes, proposta['historico'])]
            self.previa.set('Prévia dos períodos:\n' + '\n'.join(f'{date.fromisoformat(i):%d/%m/%Y} a {date.fromisoformat(f):%d/%m/%Y}' for i, f in periodos))
            self.erro.set('')
        except ValueError as erro:
            self.erro.set(str(erro)); self.previa.set('')

    def enviar(self, salvar):
        try:
            vigencia, dia = self.parametros()
            fechamento.propor(self.config, vigencia, dia)
        except ValueError as erro:
            self.erro.set(str(erro)); return
        self.ocupar(True)
        salvar(self, self.config['versao'], vigencia, dia)

    def ocupar(self, valor, mensagem=''):
        self.em_envio = valor
        for campo in self.campos: campo.configure(state='disabled' if valor else 'readonly')
        for botao in (self.salvar, self.cancelar): botao.configure(state='disabled' if valor else 'normal')
        self.erro.set(mensagem)

    def limpar(self, evento):
        if evento.widget is self:
            for var, ident in self.traces:
                try: var.trace_remove('write', ident)
                except tk.TclError: pass
