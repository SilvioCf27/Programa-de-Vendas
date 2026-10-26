"""Acesso visível às funções de dados, sem duplicar suas regras ou comandos."""
import tkinter as tk
from tkinter import ttk
from ProgramFeira.interface.ajuda import Dica
from ProgramFeira.interface.visual import CORES
from ProgramFeira.preferencias import carregar_periodo_inicial, salvar_periodo_inicial
from ProgramFeira.semanas import PERIODOS_INICIAIS

EXPLICACOES = {
    'Criar backup agora': 'Salva uma cópia verificada dos dados atuais neste computador.',
    'Restaurar backup…': 'Substitui todos os dados atuais pelos da cópia escolhida. Antes, preserva uma cópia do estado atual.',
    'Verificar integridade do backup…': 'Confere se a cópia pode ser recuperada. Não altera os dados do programa.',
    'Backup no Google Drive…': 'Escolhe a pasta do Drive para as cópias de segurança. O Google Drive envia os arquivos para a nuvem.',
    'Conexão com a nuvem…': 'Conecta à conta e sincroniza vendas e finanças com o celular. Também permite revisar conflitos.',
    'Local dos dados': 'Mostra onde ficam o banco e os arquivos locais deste computador.',
    'Sobre esta versão…': 'Mostra a versão instalada e o local dos diagnósticos para relatar um problema.',
    'Atualizações…': 'Consulta versões estáveis no GitHub, verifica o download e atualiza o executável preservando os dados.',
}


class Configuracoes(tk.Toplevel):
    def __init__(self, parent, menu, pasta=None):
        super().__init__(parent)
        self.title('Configurações')
        self.configure(background=CORES['fundo'])
        self.transient(parent)
        self.resizable(False, False)
        self.acoes, self.ajudas = {}, {}
        corpo = ttk.Frame(self, padding=20)
        corpo.pack(fill='both', expand=True)
        corpo.columnconfigure(0, weight=1)
        ttk.Label(corpo, text='Configurações', style='Section.TLabel').grid(row=0, column=0, columnspan=2, sticky='w')
        ttk.Label(corpo, text='Backups, sincronização e informações do programa.\nPasse o mouse sobre ? para ver uma explicação.', style='Muted.TLabel').grid(row=1, column=0, columnspan=2, sticky='w', pady=(8, 16))
        linha = 2
        if pasta is not None:
            ttk.Label(corpo, text='Período ao abrir o programa').grid(row=linha, column=0, sticky='w')
            ajuda_inicio = ttk.Button(corpo, text='?', width=2, style='Ajuda.TButton')
            ajuda_inicio.grid(row=linha, column=1, padx=(12, 0))
            self.dica_inicio = Dica(ajuda_inicio, 'Define os cartões e a lista na próxima abertura. A semana atual sempre aparece separada, sem depender dos filtros.')
            ajuda_inicio.configure(command=self.dica_inicio.mostrar)
            self.periodo_inicial = tk.StringVar(value=carregar_periodo_inicial(pasta))
            seletor = ttk.Combobox(corpo, textvariable=self.periodo_inicial, values=PERIODOS_INICIAIS, state='readonly')
            seletor.grid(row=linha + 1, column=0, sticky='ew', pady=(4, 0))
            aviso = ttk.Label(corpo, text='Será usado na próxima abertura.', style='Muted.TLabel')
            aviso.grid(row=linha + 2, column=0, sticky='w', pady=(4, 12))
            def salvar_inicio(event=None):
                try:
                    salvar_periodo_inicial(pasta, self.periodo_inicial.get())
                    aviso.configure(text='Salvo para a próxima abertura.')
                except OSError:
                    aviso.configure(text='Não foi possível salvar. Verifique a pasta de dados.')
            seletor.bind('<<ComboboxSelected>>', salvar_inicio)
            self.seletor_inicio = seletor
            linha += 3
        for indice in range((menu.index('end') or 0) + 1):
            if menu.type(indice) != 'command':
                continue
            titulo = menu.entrycget(indice, 'label')
            def executar(i=indice):
                self.destroy()  # Libera a janela antes de abrir formulários ou sincronizar.
                menu.invoke(i)
            botao = ttk.Button(corpo, text=titulo.rstrip('…'), command=executar, state=menu.entrycget(indice, 'state'), padding=(10, 4))
            botao.grid(row=linha, column=0, sticky='ew', pady=3)
            ajuda = ttk.Button(corpo, text='?', width=2, style='Ajuda.TButton')
            ajuda.grid(row=linha, column=1, padx=(12, 0))
            dica = Dica(ajuda, EXPLICACOES[titulo])
            ajuda.configure(command=dica.mostrar)
            self.acoes[titulo] = botao
            self.ajudas[titulo] = dica
            linha += 1
        ttk.Button(corpo, text='Fechar', command=self.destroy).grid(row=linha, column=0, columnspan=2, sticky='e', pady=(16, 0))
        self.bind('<Escape>', lambda e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 2
        self.geometry(f'+{max(0,x)}+{max(0,y)}')
        self.grab_set()
