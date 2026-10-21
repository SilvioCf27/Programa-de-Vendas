"""Acesso e migração inicial, sempre fora do loop gráfico."""
from decimal import Decimal
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from ProgramFeira import nuvem, migracao_nuvem
from ProgramFeira.interface.visual import CORES
from ProgramFeira.resumos import moeda


class ConexaoNuvem:
    def __init__(self, janela, pasta):
        self.janela, self.pasta = janela, pasta
        self.popup = None
        self.sessao = self.cliente = self.preparacao = None
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
        ttk.Label(corpo, text='Verifique o acesso, confira o backup e depois transfira os registros iniciais.\nAinda não há sincronização: continue fazendo lançamentos reais no desktop até concluirmos a integração.', wraplength=570, justify='left').grid(row=1, column=0, columnspan=2, sticky='w', pady=12)
        try:
            config = nuvem.carregar_config(self.pasta)
        except nuvem.ErroNuvem as erro:
            config = {}
            messagebox.showwarning('Reconfigurar nuvem', str(erro), parent=popup)
        self.campos = {}
        for linha, (nome, rotulo, inicial) in enumerate((
            ('url', 'Project URL', config.get('url', '')),
            ('chave', 'Chave pública', config.get('chave_publica', '')),
            ('email', 'E-mail do aplicativo', self.sessao.email if self.sessao else ''),
            ('senha', 'Senha do aplicativo', ''),
        ), 2):
            ttk.Label(corpo, text=rotulo).grid(row=linha, column=0, sticky='w', padx=(0, 12), pady=5)
            campo = ttk.Entry(corpo, width=55, show='*' if nome == 'senha' else '')
            campo.insert(0, inicial)
            campo.grid(row=linha, column=1, sticky='ew', pady=5)
            self.campos[nome] = campo
        self.status = tk.StringVar(value='Somente a URL e a chave pública são salvas. Senha e sessão não são gravadas em arquivo.')
        ttk.Label(corpo, textvariable=self.status, wraplength=570, justify='left', style='Muted.TLabel').grid(row=6, column=0, columnspan=2, sticky='w', pady=12)
        acoes = ttk.Frame(corpo)
        acoes.grid(row=7, column=0, columnspan=2, sticky='ew')
        self.botao_entrar = ttk.Button(acoes, text='Verificar acesso', command=self.entrar, style='Primary.TButton')
        self.botao_entrar.pack(side='left')
        self.botao_sair = ttk.Button(acoes, text='Desconectar', command=self.sair)
        self.botao_sair.pack(side='left', padx=8)
        ttk.Button(acoes, text='Fechar', command=self.fechar).pack(side='right')
        migrar = ttk.Frame(corpo)
        migrar.grid(row=8, column=0, columnspan=2, sticky='ew', pady=(12, 0))
        self.botao_conferir = ttk.Button(migrar, text='Conferir migração', command=self.conferir)
        self.botao_conferir.pack(side='left')
        self.botao_transferir = ttk.Button(migrar, text='Transferir dados conferidos', command=self.transferir)
        self.botao_transferir.pack(side='left', padx=8)
        popup.protocol('WM_DELETE_WINDOW', self.fechar)
        popup.bind('<Escape>', lambda e: self.fechar())
        self._controles()
        if self.sessao:
            self.status.set(f'Acesso verificado para {self.sessao.email}. Ainda não há sincronização de dados.')
        return popup

    def _controles(self):
        for controle in [*self.campos.values(), self.botao_entrar, self.botao_sair]:
            controle.configure(state='disabled' if self.ocupado else 'normal')
        self.botao_conferir.configure(state='normal' if self.sessao and not self.ocupado else 'disabled')
        self.botao_transferir.configure(state='normal' if self.preparacao and not self.ocupado else 'disabled')

    def sair(self):
        self.sessao = self.cliente = self.preparacao = None
        self.campos['senha'].delete(0, 'end')
        self.status.set('Sessão removida deste programa. Configuração pública e backups preservados.')
        self._controles()

    def fechar(self):
        if self.ocupado:
            return
        self.campos['senha'].delete(0, 'end')
        self.preparacao = None
        self.popup.destroy()

    def _rodar(self, operacao, concluir, mensagem):
        self.ocupado = True
        self._controles()
        self.popup.grab_set()
        self.status.set(mensagem)
        resultados = queue.Queue()

        def trabalhar():
            try:
                resultados.put((True, operacao()))
            except nuvem.ErroNuvem as erro:
                resultados.put((False, str(erro)))
            except Exception:
                resultados.put((False, 'Operação não confirmada. Confira a conexão e o espaço em disco. Faça uma nova conferência antes de tentar transferir novamente.'))

        def acompanhar():
            try:
                sucesso, resultado = resultados.get_nowait()
            except queue.Empty:
                self.janela.after(100, acompanhar)
                return
            self.ocupado = False
            if not self.popup.winfo_exists():
                return
            self.popup.grab_release()
            if sucesso:
                concluir(resultado)
            else:
                self.preparacao = None
                self.status.set(resultado)
            self._controles()

        threading.Thread(target=trabalhar, daemon=True).start()
        self.janela.after(100, acompanhar)

    def entrar(self):
        if self.ocupado:
            return
        self.sessao = self.cliente = self.preparacao = None
        dados = {nome: campo.get() for nome, campo in self.campos.items()}
        self.campos['senha'].delete(0, 'end')
        try:
            config = nuvem.validar_config(dados['url'], dados['chave'])
            if not dados['email'].strip() or not dados['senha']:
                raise nuvem.ErroNuvem('Informe seu e-mail e sua senha de acesso ao aplicativo.')
            cliente = nuvem.ClienteNuvem(config['url'], config['chave_publica'])
        except nuvem.ErroNuvem as erro:
            self.status.set(str(erro))
            self._controles()
            return

        def operacao():
            try:
                sessao = cliente.entrar(dados['email'], dados['senha'])
                nuvem.salvar_config(self.pasta, config['url'], config['chave_publica'])
                return sessao
            finally:
                dados.clear()

        def concluir(sessao):
            self.sessao, self.cliente = sessao, cliente
            self.status.set(f'Acesso verificado para {sessao.email}. Configuração salva. Nenhum registro foi transferido.')

        self._rodar(operacao, concluir, 'Verificando acesso e autorização da conta…')

    def _validar_conta(self):
        if not self.sessao or not self.cliente:
            raise nuvem.ErroNuvem('Verifique o acesso antes de conferir a migração.')
        config = nuvem.validar_config(self.campos['url'].get(), self.campos['chave'].get())
        if config != {'url': self.cliente.url, 'chave_publica': self.cliente.chave} or self.campos['email'].get().strip().lower() != self.sessao.email.lower():
            raise nuvem.ErroNuvem('A configuração da conta mudou. Verifique o acesso novamente.')

    def conferir(self):
        if self.ocupado:
            return
        self.preparacao = None
        try:
            self._validar_conta()
        except nuvem.ErroNuvem as erro:
            self.status.set(str(erro))
            self._controles()
            return
        cliente, sessao = self.cliente, self.sessao

        def concluir(preparacao):
            self.preparacao = preparacao
            r = preparacao['relatorio']
            s = r['resumo']
            contagem = s['registros']
            self.status.set(
                f"Conferência concluída: {contagem['vendas']} vendas, {contagem['financeiro_lancamentos']} lançamentos e {contagem['financeiro_taxas_anuais']} ajustes anuais.\n"
                f"Vendas brutas: {moeda(Decimal(s['total_centavos']) / 100)}. Dias zerados: {s['dias_zerados']}.\n"
                f"Registros novos a enviar: {sum(r['novos'].values())}. Nenhuma divergência encontrada.\n"
                f"Backup verificado: {r['backup']}\nRelatório: {preparacao['caminho']}\n"
                'Nenhum registro foi transferido. Confira os totais antes de continuar.'
            )

        self._rodar(lambda: migracao_nuvem.preparar(self.pasta / 'vendas.db', cliente, sessao), concluir, 'Criando backup verificado e comparando os registros com a nuvem…')

    def transferir(self):
        if self.ocupado or not self.preparacao:
            return
        try:
            self._validar_conta()
        except nuvem.ErroNuvem as erro:
            self.status.set(str(erro))
            return
        p = self.preparacao
        r = p['relatorio']
        if not messagebox.askyesno('Transferência inicial',
            f"Enviar {sum(r['novos'].values())} registros novos para a conta {self.sessao.email}?\n"
            f"Vendas brutas conferidas: {moeda(Decimal(r['resumo']['total_centavos']) / 100)}.\n\n"
            f"Backup verificado: {r['backup']}\n\n"
            'O banco local será preservado. Isso ainda não ativa sincronização automática. Não edite os dados em outro dispositivo durante o envio.', parent=self.popup):
            return
        self.preparacao = None

        def concluir(relatorio):
            self.status.set(f"Transferência concluída e validada registro por registro.\nRegistros inseridos: {sum(relatorio['inseridos'].values())}.\nRelatório: {p['caminho']}\n\nAbra o aplicativo web e clique em Atualizar para conferir as vendas. Continue usando apenas o desktop para lançamentos reais: a sincronização ainda será implementada.")

        self._rodar(lambda: migracao_nuvem.transferir(p), concluir, 'Transferindo e validando os dados. Aguarde sem fechar o programa…')
