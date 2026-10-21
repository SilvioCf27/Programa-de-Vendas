"""Acesso e migração inicial, sempre fora do loop gráfico."""
from datetime import datetime
from decimal import Decimal
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from ProgramFeira import nuvem, migracao_nuvem, sincronizacao, automacao_nuvem, sessao_windows
from ProgramFeira.interface.visual import CORES
from ProgramFeira.resumos import moeda


class ConexaoNuvem:
    def __init__(self, janela, pasta, ao_sincronizar=None, antes_sincronizar=None, antes_automatico=None, bloquear_edicao=None):
        self.janela, self.pasta = janela, pasta
        self.ao_sincronizar = ao_sincronizar
        self.antes_sincronizar = antes_sincronizar
        self.antes_automatico = antes_automatico or antes_sincronizar
        self.bloquear_edicao = bloquear_edicao
        self.bloqueando_edicao = False
        self.em_segundo_plano = False
        self.status = tk.StringVar(master=janela, value='Entre para conectar à nuvem. No Windows, a sessão fica protegida na sua conta; sua senha não é salva.')
        self.resumo = tk.StringVar(master=janela, value='Nuvem: entre em Dados → Conexão com a nuvem.')
        self.automatico = tk.BooleanVar(master=janela, value=automacao_nuvem.carregar_preferencia(pasta))
        self.agendador = automacao_nuvem.Agendador(janela,
            lambda: bool(self.automatico.get() and self.sessao and self.vinculado),
            self._livre_automatico, self._automatico)
        janela.bind('<Destroy>', lambda e: self.agendador.parar() if e.widget is janela else None, add='+')
        self.vinculado = sincronizacao.vinculado(pasta / 'vendas.db')
        self.popup = None
        self.sessao = self.cliente = self.preparacao = None
        self.ocupado = False
        self.aviso_sessao = ''
        # Apenas leitura local; a rede será consultada pelo agendador após abrir a UI.
        self.janela.after_idle(self.restaurar_sessao)

    def _persistir_sessao(self, cliente, sessao):
        try:
            sessao_windows.salvar(self.pasta, cliente.url, sessao)
            self.aviso_sessao = ''
        except OSError:
            self.aviso_sessao = ' Não foi possível salvar a sessão protegida; será necessário entrar novamente na próxima abertura.'

    def _preparar_cliente(self, cliente):
        cliente.ao_renovar = lambda sessao: self._persistir_sessao(cliente, sessao)
        return cliente

    def restaurar_sessao(self):
        if self.ocupado or self.sessao:
            return
        try:
            config = nuvem.carregar_config(self.pasta)
            if not config:
                return
            sessao = sessao_windows.carregar(self.pasta, config['url'])
            if not sessao:
                return
            self.cliente = self._preparar_cliente(nuvem.ClienteNuvem(config['url'], config['chave_publica']))
            self.sessao = sessao
            if self.popup is not None and self.popup.winfo_exists():
                self.campos['email'].delete(0, 'end')
                self.campos['email'].insert(0, sessao.email)
            self.status.set('Sessão recuperada deste Windows. O acesso será renovado antes de sincronizar.')
            self.resumo.set('Nuvem: reconectando automaticamente…' if self.automatico.get() else 'Nuvem: sessão recuperada · Modo manual')
            self.agendador.ativar()
            self._controles()
        except nuvem.ErroNuvem as erro:
            self.status.set(str(erro))
            self.resumo.set('Nuvem: entre novamente para recuperar o acesso.')

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
        ttk.Label(corpo, text='No Windows, a sessão é recuperada ao abrir o programa, sem salvar sua senha.\nA opção automática consulta alterações a cada minuto. Desconectar remove a sessão salva.', wraplength=570, justify='left').grid(row=1, column=0, columnspan=2, sticky='w', pady=12)
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
        self.botao_sincronizar = ttk.Button(corpo, text='Sincronizar agora', command=self.sincronizar, style='Primary.TButton')
        self.botao_sincronizar.grid(row=9, column=0, columnspan=2, sticky='w', pady=(12, 0))
        self.check_automatico = ttk.Checkbutton(corpo,
            text='Sincronizar automaticamente a cada minuto enquanto estiver conectado',
            variable=self.automatico, command=self.alterar_automatico)
        self.check_automatico.grid(row=10, column=0, columnspan=2, sticky='w', pady=(12, 0))
        popup.protocol('WM_DELETE_WINDOW', self.fechar)
        popup.bind('<Escape>', lambda e: self.fechar())
        self._controles()
        if self.sessao:
            self.status.set(f'Conta conectada: {self.sessao.email}. A opção automática consulta alterações a cada minuto.' + self.aviso_sessao)
        return popup

    def _controles(self):
        if self.popup is None or not self.popup.winfo_exists():
            return
        self.check_automatico.configure(state='disabled' if self.ocupado else 'normal')
        for controle in [*self.campos.values(), self.botao_entrar, self.botao_sair]:
            controle.configure(state='disabled' if self.ocupado else 'normal')
        self.botao_sincronizar.configure(state='normal' if self.sessao and not self.ocupado else 'disabled')
        self.botao_conferir.configure(state='normal' if self.sessao and not self.ocupado and not self.vinculado else 'disabled')
        self.botao_transferir.configure(state='normal' if self.preparacao and not self.ocupado and not self.vinculado else 'disabled')

    def sair(self):
        if self.ocupado:
            return
        try:
            sessao_windows.remover(self.pasta)
        except OSError:
            self.status.set('Não foi possível remover a sessão salva. Confira as permissões da pasta e tente desconectar novamente.')
            return
        self.agendador.parar()
        self.resumo.set('Nuvem: desconectada. Os dados continuam salvos neste computador.')
        self.sessao = self.cliente = self.preparacao = None
        self.campos['senha'].delete(0, 'end')
        self.status.set('Sessão removida deste programa. Configuração pública e backups preservados.')
        self._controles()

    def fechar(self):
        if self.ocupado and not self.em_segundo_plano:
            return
        self.campos['senha'].delete(0, 'end')
        self.preparacao = None
        self.popup.destroy()

    def _rodar(self, operacao, concluir, mensagem, segundo_plano=False, ao_erro=None, travar=False):
        self.ocupado = True
        self.em_segundo_plano = segundo_plano
        self._controles()
        popup = self.popup if self.popup is not None and self.popup.winfo_exists() else None
        if popup is not None and not segundo_plano:
            popup.grab_set()
        self.status.set(mensagem)
        self.bloqueando_edicao = travar
        if travar and self.bloquear_edicao:
            self.bloquear_edicao(True)
        resultados = queue.Queue()

        def trabalhar():
            try:
                resultados.put((True, operacao()))
            except nuvem.ErroNuvem as erro:
                resultados.put((False, erro))
            except Exception:
                resultados.put((False, nuvem.ErroNuvem('Operação não confirmada. Confira a conexão e o espaço em disco antes de continuar.')))

        def acompanhar():
            try:
                sucesso, resultado = resultados.get_nowait()
            except queue.Empty:
                self.janela.after(100, acompanhar)
                return
            self.ocupado = self.em_segundo_plano = False
            self.bloqueando_edicao = False
            if travar and self.bloquear_edicao:
                self.bloquear_edicao(False)
            if popup is not None and popup.winfo_exists() and popup.grab_current() == popup:
                popup.grab_release()
            if sucesso:
                concluir(resultado)
            else:
                self.preparacao = None
                self.status.set(str(resultado))
                if ao_erro:
                    ao_erro(resultado)
                else:
                    self.resumo.set('Nuvem: operação não confirmada. Abra Conexão com a nuvem para conferir.')
            self.vinculado = sincronizacao.vinculado(self.pasta / 'vendas.db')
            self._controles()

        threading.Thread(target=trabalhar, daemon=True).start()
        self.janela.after(100, acompanhar)

    def entrar(self):
        if self.ocupado:
            return
        self.agendador.parar()
        self.resumo.set('Nuvem: verificando acesso…')
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
            self._preparar_cliente(cliente)
            self._persistir_sessao(cliente, sessao)
            self.sessao, self.cliente = sessao, cliente
            self.status.set(f'Acesso verificado para {sessao.email}. Configuração salva. Nenhum registro foi transferido.' + self.aviso_sessao)
            self.resumo.set('Nuvem: conectada. Sincronização automática ativa.' if self.automatico.get() and self.vinculado else 'Nuvem: conectada. Use Sincronizar agora.')
            self.agendador.ativar()

        self._rodar(operacao, concluir, 'Verificando acesso e autorização da conta…')

    def _validar_conta(self):
        if not self.sessao or not self.cliente:
            raise nuvem.ErroNuvem('Verifique o acesso antes de conferir a migração.')
        config = nuvem.validar_config(self.campos['url'].get(), self.campos['chave'].get())
        if config != {'url': self.cliente.url, 'chave_publica': self.cliente.chave} or self.campos['email'].get().strip().lower() != self.sessao.email.lower():
            raise nuvem.ErroNuvem('A configuração da conta mudou. Verifique o acesso novamente.')

    def conferir(self):
        if self.ocupado or self.vinculado:
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
        if self.ocupado or self.vinculado or not self.preparacao:
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
            self.status.set(f"Transferência concluída e validada registro por registro.\nRegistros inseridos: {sum(relatorio['inseridos'].values())}.\nRelatório: {p['caminho']}\n\nAbra o aplicativo web e clique em Atualizar para conferir as vendas. O próximo passo é clicar em Sincronizar agora para estabelecer o vínculo entre os registros.")

        self._rodar(lambda: migracao_nuvem.transferir(p), concluir, 'Transferindo e validando os dados. Aguarde sem fechar o programa…')

    def _falha_sincronizacao(self, erro):
        temporario = isinstance(erro, nuvem.ErroTemporario)
        if temporario:
            nova_tentativa = 'Nova tentativa em até 5 minutos.' if self.automatico.get() else 'Use Sincronizar agora para tentar novamente.'
            self.resumo.set('Nuvem: sem conexão; dados locais preservados. ' + nova_tentativa)
        else:
            self.resumo.set('Nuvem: sincronização pausada. Abra Conexão com a nuvem para conferir.')
        self.agendador.concluir(erro=erro)

    def _concluiu_sincronizacao(self, nova_sessao, resultado, automatico=False):
        self.sessao = nova_sessao
        self.vinculado = True
        horario = datetime.now().strftime('%H:%M:%S')
        self.resumo.set(f'Nuvem atualizada às {horario} · Automática ativa' if self.automatico.get() else f'Nuvem atualizada às {horario} · Modo manual')
        self.status.set(
            f"Sincronização concluída. Alterações enviadas: {resultado['enviadas']}; recebidas: {resultado['recebidas']}.\n"
            f"Vendas: {resultado['registros']['vendas']}. "
            + (f"Backup: {resultado['backup']}\n" if resultado['backup'] else 'Nenhuma alteração; não foi necessário outro backup.\n')
            + self.aviso_sessao + ('A consulta automática continuará a cada minuto enquanto o programa estiver aberto e autenticado.' if self.automatico.get() else 'Modo manual: use Sincronizar agora depois de editar em qualquer dispositivo.')
        )
        try:
            if self.ao_sincronizar and (not automatico or resultado['recebidas']):
                self.ao_sincronizar()
        finally:
            # Uma falha de renderização não pode cancelar as próximas consultas.
            if automatico:
                self.agendador.concluir()
            else:
                self.agendador.ativar()

    def sincronizar(self):
        if self.ocupado:
            return
        try:
            self._validar_conta()
            if self.antes_sincronizar:
                self.antes_sincronizar()
        except nuvem.ErroNuvem as erro:
            self.status.set(str(erro))
            return
        self.agendador.parar()
        self.preparacao = None
        cliente, sessao = self.cliente, self.sessao

        def operacao():
            nova = cliente.garantir_sessao(sessao)
            return nova, sincronizacao.sincronizar(self.pasta / 'vendas.db', cliente, nova)

        self._rodar(operacao, lambda r: self._concluiu_sincronizacao(*r),
            'Comparando versões, enviando e recebendo alterações… Aguarde sem fechar o programa.',
            ao_erro=self._falha_sincronizacao, travar=True)

    def alterar_automatico(self):
        try:
            automacao_nuvem.salvar_preferencia(self.pasta, self.automatico.get())
        except OSError:
            self.status.set('A preferência não pôde ser salva para a próxima abertura. Confira o espaço em disco.')
        if self.automatico.get():
            self.resumo.set('Nuvem: automática ativada; aguarde a próxima consulta.' if self.sessao else 'Nuvem: entre na sua conta para ativar a sincronização automática.')
            self.agendador.ativar()
        else:
            self.agendador.parar()
            self.resumo.set('Nuvem: modo manual. Use Sincronizar agora.')

    def _livre_automatico(self):
        if self.ocupado:
            return False
        self.vinculado = sincronizacao.vinculado(self.pasta / 'vendas.db')
        if not self.vinculado:
            return False
        try:
            if self.popup is not None and self.popup.winfo_exists():
                self._validar_conta()
            if self.antes_automatico:
                self.antes_automatico()
        except (ValueError, KeyError, tk.TclError) as erro:
            self.resumo.set(f'Nuvem: aguardando. {erro}')
            return False
        return True

    def _automatico(self):
        cliente, sessao = self.cliente, self.sessao
        self.resumo.set('Nuvem: consultando alterações…')

        def consultar():
            base = sincronizacao.assinatura_base(self.pasta / 'vendas.db')
            if base is None:
                raise nuvem.ErroNuvem('Confira o vínculo do banco antes de retomar a sincronização automática.')
            nova = cliente.garantir_sessao(sessao)
            return nova, cliente.sincronizar(nova), base

        def recebeu(resposta):
            nova, snapshot, base = resposta
            self.sessao = nova
            if not self.automatico.get() or self.agendador.pausado or not self._livre_automatico():
                self.agendador.concluir(adiar=True)
                return
            self.resumo.set('Nuvem: sincronizando; aguarde para editar…')
            self._rodar(lambda: sincronizacao.sincronizar(self.pasta / 'vendas.db', cliente, nova,
                    snapshot_inicial=snapshot, somente_se_mudou=True, base_inicial=base),
                lambda r: self._concluiu_sincronizacao(nova, r, automatico=True),
                'Sincronizando as alterações em segundo plano…', segundo_plano=True,
                ao_erro=self._falha_sincronizacao, travar=True)

        self._rodar(consultar, recebeu, 'Consultando alterações na nuvem…',
            segundo_plano=True, ao_erro=self._falha_sincronizacao)

    def notificar_alteracao(self):
        if not self.sessao:
            self.resumo.set('Nuvem: alterações locais salvas. Entre na sua conta para sincronizar.')
        elif self.agendador.pausado:
            self.resumo.set('Nuvem: alterações locais pendentes. Sincronização pausada; confira os detalhes.')
        elif self.automatico.get():
            self.resumo.set('Nuvem: alterações locais aguardando envio…')
            self.agendador.agendar(2000)
        else:
            self.resumo.set('Nuvem: alterações locais pendentes. Use Sincronizar agora.')

    def banco_restaurado(self):
        self.vinculado = sincronizacao.vinculado(self.pasta / 'vendas.db')
        erro = nuvem.ErroNuvem('Banco restaurado. Confira os dados e sincronize manualmente antes de retomar a automação.')
        self.status.set(str(erro))
        self._falha_sincronizacao(erro)
