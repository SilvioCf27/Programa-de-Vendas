"""Campos de mês, ano e semana para a consulta financeira."""
import calendar
from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk
from ProgramFeira.comparacao import interpretar_data

MESES = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
         'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')


def semanas_do_mes(ano, mes):
    primeira = date(ano, mes, 1)
    inicio = primeira - timedelta(days=primeira.weekday())
    ultima = primeira.replace(day=calendar.monthrange(ano, mes)[1])
    resultado = []
    while inicio <= ultima:
        resultado.append((inicio, inicio + timedelta(days=6)))
        inicio += timedelta(days=7)
    return resultado


class SeletorFinanceiro(ttk.Frame):
    def __init__(self, parent, tipo, referencia):
        super().__init__(parent, style='Surface.TFrame')
        self.tipo, self.referencia = tipo, referencia
        self.atualizando = False
        self.ano, self.mes, self.semana = (tk.StringVar() for _ in range(3))
        self.campos = {}
        for coluna, (chave, titulo, variavel, opcoes, largura) in enumerate((
                ('ano', 'Ano', self.ano, tuple(range(date.today().year - 5, date.today().year + 3)), 7),
                ('mes', 'Mês', self.mes, MESES, 12),
                ('semana', 'Semana (segunda a domingo)', self.semana, (), 25))):
            bloco = ttk.Frame(self, style='Surface.TFrame')
            bloco.grid(row=0, column=coluna, sticky='w', padx=(0, 8))
            ttk.Label(bloco, text=titulo, style='Surface.TLabel').pack(anchor='w')
            campo = ttk.Combobox(bloco, textvariable=variavel, values=opcoes,
                                 width=largura, state='normal' if chave == 'ano' else 'readonly')
            campo.pack(anchor='w', pady=(3, 0))
            campo.bind('<<ComboboxSelected>>', self.atualizar)
            if chave == 'ano':
                campo.bind('<Return>', self.atualizar)
                campo.bind('<FocusOut>', self.atualizar)
            self.campos[chave] = (bloco, campo)
        self.traces = [(tipo, tipo.trace_add('write', self.atualizar)),
                       (referencia, referencia.trace_add('write', self.ler_referencia))]
        self.bind('<Destroy>', self.limpar_traces, add='+')
        self.ler_referencia()

    def limpar_traces(self, evento):
        if evento.widget is self:
            for var, ident in self.traces:
                try: var.trace_remove('write', ident)
                except tk.TclError: pass

    def ler_referencia(self, *args):
        if self.atualizando:
            return
        try:
            dia = interpretar_data(self.referencia.get())
        except ValueError:
            return
        self.ano.set(str(dia.year))
        self.mes.set(MESES[dia.month - 1])
        self.atualizar(dia=dia)

    def atualizar(self, *args, dia=None):
        if self.atualizando:
            return
        self.atualizando = True
        try:
            ano, mes = int(self.ano.get()), MESES.index(self.mes.get()) + 1
            if not 1900 <= ano <= 9998:
                self.referencia.set('')
                return
            for chave, mostrar in (('mes', self.tipo.get() != 'Ano'), ('semana', self.tipo.get() == 'Semana')):
                bloco, _ = self.campos[chave]
                bloco.grid() if mostrar else bloco.grid_remove()
            if self.tipo.get() == 'Semana':
                semanas = semanas_do_mes(ano, mes)
                self.opcoes = {f'{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}': inicio for inicio, fim in semanas}
                anterior = self.semana.get()
                if dia:
                    inicio = dia - timedelta(days=dia.weekday())
                else:
                    inicio = self.opcoes.get(anterior, semanas[0][0])
                escolhido = next((nome for nome, data in self.opcoes.items() if data == inicio), next(iter(self.opcoes)))
                self.campos['semana'][1].configure(values=tuple(self.opcoes))
                self.semana.set(escolhido)
                referencia = self.opcoes[escolhido]
            else:
                referencia = date(ano, mes, 1)
            self.referencia.set(referencia.strftime('%d/%m/%Y'))
        except (ValueError, OverflowError):
            self.referencia.set('')  # Ano incompleto não reutiliza uma consulta antiga.
        finally:
            self.atualizando = False


class CampoData(ttk.Frame):
    """Data explícita, sem depender da confirmação de um calendário nativo."""
    def __init__(self, parent, variavel):
        super().__init__(parent)
        self.variavel, self.atualizando = variavel, False
        self.dia, self.mes, self.ano = (tk.StringVar() for _ in range(3))
        self.campos = []
        for coluna, (titulo, var, opcoes, largura) in enumerate((
                ('Dia', self.dia, tuple(range(1, 32)), 4),
                ('Mês', self.mes, MESES, 11),
                ('Ano', self.ano, tuple(range(date.today().year - 5, date.today().year + 3)), 6))):
            bloco = ttk.Frame(self)
            bloco.grid(row=0, column=coluna, sticky='w', padx=(0, 6))
            ttk.Label(bloco, text=titulo).pack(anchor='w')
            campo = ttk.Combobox(bloco, textvariable=var, values=opcoes,
                                 width=largura, state='normal' if titulo == 'Ano' else 'readonly')
            campo.pack(anchor='w')
            campo.bind('<<ComboboxSelected>>', self.atualizar)
            if titulo == 'Ano':
                campo.bind('<FocusOut>', self.atualizar)
                campo.bind('<Return>', self.atualizar)
            self.campos.append(campo)
        self.resumo = ttk.Label(self, style='Muted.TLabel')
        self.resumo.grid(row=1, column=0, columnspan=3, sticky='w', pady=(4, 0))
        self.trace = variavel.trace_add('write', self.ler)
        self.bind('<Destroy>', self.limpar_trace, add='+')
        self.ler()

    def limpar_trace(self, evento):
        if evento.widget is self:
            try: self.variavel.trace_remove('write', self.trace)
            except tk.TclError: pass

    def set(self, texto):
        self.variavel.set(texto)

    def ler(self, *args):
        if self.atualizando:
            return
        try:
            dia = interpretar_data(self.variavel.get())
        except ValueError:
            return
        self.dia.set(str(dia.day)); self.mes.set(MESES[dia.month - 1]); self.ano.set(str(dia.year))
        self.atualizar()

    def atualizar(self, *args):
        self.atualizando = True
        try:
            ano, mes = int(self.ano.get()), MESES.index(self.mes.get()) + 1
            if not 1900 <= ano <= 9998:
                raise ValueError()
            ultimo = calendar.monthrange(ano, mes)[1]
            dia = min(int(self.dia.get()), ultimo)
            self.campos[0].configure(values=tuple(range(1, ultimo + 1)))
            self.dia.set(str(dia))
            texto = date(ano, mes, dia).strftime('%d/%m/%Y')
            self.variavel.set(texto)
            self.resumo.configure(text='Data selecionada: ' + texto)
        except ValueError:
            self.variavel.set('')
            self.resumo.configure(text='Confira o ano informado.')
        finally:
            self.atualizando = False
