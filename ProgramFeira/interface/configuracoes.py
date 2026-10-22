"""Acesso visível às funções de dados, sem duplicar suas regras ou comandos."""
import tkinter as tk
from tkinter import ttk
from ProgramFeira.interface.ajuda import Dica
from ProgramFeira.interface.visual import CORES

EXPLICACOES = {
    'Criar backup agora': 'Salva uma cópia verificada dos dados atuais neste computador.',
    'Restaurar backup…': 'Substitui todos os dados atuais pelos da cópia escolhida. Antes, preserva uma cópia do estado atual.',
    'Verificar integridade do backup…': 'Confere se a cópia pode ser recuperada. Não altera os dados do programa.',
    'Backup no Google Drive…': 'Escolhe a pasta do Drive para as cópias de segurança. O Google Drive envia os arquivos para a nuvem.',
    'Conexão com a nuvem…': 'Conecta à conta e sincroniza vendas e finanças com o celular. Também permite revisar conflitos.',
    'Local dos dados': 'Mostra onde ficam o banco e os arquivos locais deste computador.',
    'Sobre esta versão…': 'Mostra a versão instalada e o local dos diagnósticos para relatar um problema.',
}


class Configuracoes(tk.Toplevel):
    def __init__(self, parent, menu):
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
        for indice in range((menu.index('end') or 0) + 1):
            if menu.type(indice) != 'command':
                continue
            titulo = menu.entrycget(indice, 'label')
            def executar(i=indice):
                self.destroy()  # Libera a janela antes de abrir formulários ou sincronizar.
                menu.invoke(i)
            botao = ttk.Button(corpo, text=titulo.rstrip('…'), command=executar, state=menu.entrycget(indice, 'state'))
            botao.grid(row=linha, column=0, sticky='ew', pady=4)
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
