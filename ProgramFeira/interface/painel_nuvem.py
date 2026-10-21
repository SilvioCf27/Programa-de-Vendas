"""Verificação de acesso online sem bloquear a janela ou transferir registros."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from ProgramFeira import nuvem
from ProgramFeira.interface.visual import CORES


class ConexaoNuvem:
    def __init__(self, janela, pasta):
        self.janela, self.pasta = janela, pasta
        self.popup = None
        self.sessao = None
        self.ocupado = False

    def configurar(self):
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.lift()
            return self.popup
        popup = self.popup = tk.Toplevel(self.janela)
        popup.title('Conexão com a nuvem')
        popup.configure(background=CORES['fundo'])
        popup.transient(self.janela)
        corpo = ttk.Frame(popup, padding=20)
        corpo.pack(fill='both', expand=True)
        corpo.columnconfigure(1, weight=1)
        ttk.Label(corpo, text='Sua conta no Gestão da Feira', style='Title.TLabel').grid(row=0, column=0, columnspan=2, sticky='w')
        ttk.Label(corpo, text='Confira o acesso ao mesmo projeto usado no celular. Esta etapa não envia nem baixa vendas, taxas ou despesas.\nO banco local e o backup no Drive continuam funcionando como antes.', wraplength=550, justify='left').grid(row=1, column=0, columnspan=2, sticky='w', pady=12)
        try:
            config = nuvem.carregar_config(self.pasta)
        except nuvem.ErroNuvem as erro:
            config = {}
            messagebox.showwarning('Reconfigurar nuvem', str(erro), parent=popup)
        self.campos = {}
        for linha, (nome, rotulo, inicial) in enumerate((
            ('url', 'Project URL', config.get('url', '')),
            ('chave', 'Chave pública', config.get('chave_publica', '')),
            ('email', 'E-mail do aplicativo', ''),
            ('senha', 'Senha do aplicativo', ''),
        ), 2):
            ttk.Label(corpo, text=rotulo).grid(row=linha, column=0, sticky='w', padx=(0, 12), pady=5)
            campo = ttk.Entry(corpo, width=55, show='*' if nome == 'senha' else '')
            campo.insert(0, inicial)
            campo.grid(row=linha, column=1, sticky='ew', pady=5)
            self.campos[nome] = campo
        self.status = tk.StringVar(value='Somente a URL e a chave pública são salvas neste computador. Senha e sessão não são gravadas em arquivo.')
        ttk.Label(corpo, textvariable=self.status, wraplength=550, justify='left', style='Muted.TLabel').grid(row=6, column=0, columnspan=2, sticky='w', pady=12)
        acoes = ttk.Frame(corpo)
        acoes.grid(row=7, column=0, columnspan=2, sticky='ew')
        self.botao_entrar = ttk.Button(acoes, text='Verificar acesso', command=self.entrar, style='Primary.TButton')
        self.botao_entrar.pack(side='left')
        self.botao_sair = ttk.Button(acoes, text='Desconectar', command=self.sair)
        self.botao_sair.pack(side='left', padx=8)
        ttk.Button(acoes, text='Fechar', command=self.fechar).pack(side='right')
        popup.protocol('WM_DELETE_WINDOW', self.fechar)
        popup.bind('<Escape>', lambda e: self.fechar())
        if self.sessao:
            self.status.set(f'Acesso verificado para {self.sessao.email}. Ainda não há sincronização de dados.')
        return popup

    def sair(self):
        self.sessao = None
        self.campos['senha'].delete(0, 'end')
        self.status.set('Sessão removida deste programa. A configuração pública foi preservada.')

    def fechar(self):
        if self.ocupado:
            return
        self.campos['senha'].delete(0, 'end')
        self.popup.destroy()

    def entrar(self):
        if self.ocupado:
            return
        self.sessao = None
        dados = {nome: campo.get() for nome, campo in self.campos.items()}
        self.campos['senha'].delete(0, 'end')
        try:
            config = nuvem.validar_config(dados['url'], dados['chave'])
            if not dados['email'].strip() or not dados['senha']:
                raise nuvem.ErroNuvem('Informe seu e-mail e sua senha de acesso ao aplicativo.')
            cliente = nuvem.ClienteNuvem(config['url'], config['chave_publica'])
        except nuvem.ErroNuvem as erro:
            self.status.set(str(erro))
            return
        self.ocupado = True
        controles = [*self.campos.values(), self.botao_entrar, self.botao_sair]
        for controle in controles:
            controle.configure(state='disabled')
        self.status.set('Verificando acesso e autorização da conta…')
        resultados = queue.Queue()

        def trabalhar():
            try:
                sessao = cliente.entrar(dados['email'], dados['senha'])
                nuvem.salvar_config(self.pasta, config['url'], config['chave_publica'])
                resultados.put((sessao, None))
            except nuvem.ErroNuvem as erro:
                resultados.put((None, str(erro)))
            except Exception:
                resultados.put((None, 'Não foi possível concluir a verificação e salvar a configuração. Tente novamente.'))
            finally:
                dados.clear()

        def acompanhar():
            try:
                sessao, erro = resultados.get_nowait()
            except queue.Empty:
                self.janela.after(100, acompanhar)
                return
            self.ocupado = False
            self.sessao = sessao
            if not self.popup.winfo_exists():
                return
            for controle in controles:
                controle.configure(state='normal')
            self.status.set(erro or f'Acesso verificado para {sessao.email}. Configuração salva. Nenhum registro foi transferido.')

        threading.Thread(target=trabalhar, daemon=True).start()
        self.janela.after(100, acompanhar)
