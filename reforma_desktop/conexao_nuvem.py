"""Coordenação Qt sobre os mecanismos existentes, com transporte local de estudo."""
from reforma_desktop.diagnostico_qt import pasta_do_objeto, registrar_seguro
from pathlib import Path
from PySide6 import QtCore as Q, QtWidgets as W
from ProgramFeira import nuvem, financeiro, migracao_nuvem, sincronizacao, automacao_nuvem, sessao_windows
from reforma_desktop.servico_nuvem_estudo import ClienteEstudo


class RelogioQt(Q.QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.tarefas = {}
        self.sequencia = 0

    def after(self, atraso, funcao):
        self.sequencia += 1
        i = self.sequencia
        timer = Q.QTimer(self)
        timer.setSingleShot(True)
        def disparar():
            self.tarefas.pop(i, None)
            timer.deleteLater()
            funcao()
        timer.timeout.connect(disparar)
        self.tarefas[i] = timer
        timer.start(atraso)
        return i

    def after_cancel(self, i):
        timer = self.tarefas.pop(i, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()


class Tarefa(Q.QThread):
    resultado = Q.Signal(bool, object)

    def __init__(self, funcao, parent):
        super().__init__(parent)
        self.funcao = funcao
        self.pasta_diagnostico = pasta_do_objeto(parent)

    def run(self):
        try:
            r = self.funcao()
        except nuvem.ErroNuvem as erro:
            self.resultado.emit(False, erro)
        except Exception as erro:
            registrar_seguro(erro, self.pasta_diagnostico)
            # Não exibe respostas HTTP, credenciais ou exceções de transporte.
            self.resultado.emit(False, nuvem.ErroNuvem('Operação não confirmada. Confira o armazenamento e tente novamente.'))
        else:
            self.resultado.emit(True, r)


class Conexao(Q.QObject):
    mudou = Q.Signal()

    def __init__(self, janela, *, cliente=None, validacao_real=False):
        super().__init__(janela)
        self.validacao_real = validacao_real
        self.sessao_verificada = False
        self.transferencia_confirmada = False
        self.janela = janela
        self.pasta = Path(janela.pasta)
        self.banco = self.pasta / 'vendas.db'
        # Nenhuma configuração pessoal é lida para escolher o transporte.
        self.cliente = cliente if cliente is not None else ClienteEstudo(self.pasta)
        self.cliente.ao_renovar = self.persistir
        self.sessao = self.preparacao = self.revisao = None
        self.tarefa = None
        self.ocupado = False
        self.recebendo = False
        self.automatico = False if validacao_real else automacao_nuvem.carregar_preferencia(self.pasta)
        self.status = 'Somente estudo: serviço local simulado, sem acesso ao Supabase ou à sua conta.'
        self.resumo = 'Nuvem simulada · desconectada'
        if validacao_real:
            self.status = 'Projeto de validação: ' + self.cliente.url + '. Login não envia registros; sincronização somente manual.'
            self.resumo = 'Validação online · desconectada'
        self.aviso_sessao = ''
        self.relogio = RelogioQt(self)
        self.agendador = automacao_nuvem.Agendador(self.relogio, self.ativo, self.livre, self.automaticamente)
        # Apenas arquivo DPAPI da pasta de estudo, nunca a configuração pessoal.
        self.restaurar_sessao()

    @property
    def vinculado(self):
        return sincronizacao.vinculado(self.banco)

    def ativo(self):
        return bool(self.automatico and self.sessao and self.vinculado)

    def livre(self):
        return not self.ocupado and self.janela.isEnabled() and not W.QApplication.activeModalWidget() and not getattr(self.janela, '_backup_fechamento', None)

    def informar(self, mensagem, resumo=None):
        self.status = mensagem
        if resumo is not None:
            self.resumo = resumo.replace('Nuvem simulada', 'Validação online', 1) if self.validacao_real else resumo
        self.mudou.emit()

    def persistir(self, sessao):
        # Callback também pode ser chamado pelo trabalhador. Somente I/O aqui.
        try:
            sessao_windows.salvar(self.pasta, self.cliente.url, sessao)
            self.aviso_sessao = '' if sessao_windows.DISPONIVEL else ' Fora do Windows, a sessão não é persistida.'
        except OSError:
            self.aviso_sessao = ' A sessão não pôde ser salva; reconecte na próxima abertura.'

    def restaurar_sessao(self):
        try:
            self.sessao = sessao_windows.carregar(self.pasta, self.cliente.url)
        except nuvem.ErroNuvem as erro:
            self.informar(str(erro))
            return
        if self.sessao:
            self.informar('Sessão recuperada. Clique em Retomar sessão para verificar o acesso; nenhum registro foi enviado.' if self.validacao_real else 'Sessão fictícia recuperada do Windows; será renovada antes da consulta.', 'Nuvem simulada · sessão recuperada')
            if not self.validacao_real:
                self.agendador.ativar()

    def rodar(self, funcao, concluir, mensagem, travar=True):
        if self.ocupado:
            return
        self.ocupado = True
        self.informar(mensagem)
        if travar:
            self.janela.relogio.stop()
            self.janela.setEnabled(False)
        resposta = []
        tarefa = Tarefa(funcao, self)
        self.tarefa = tarefa
        tarefa.resultado.connect(lambda ok, valor: resposta.append((ok, valor)))
        def terminou():
            tarefa.wait()  # Libera a UI só após terminar também a thread nativa.
            self.tarefa = None
            self.ocupado = False
            if travar:
                self.janela.setEnabled(True)
                self.janela.relogio.start()
            ok, valor = resposta[0] if resposta else (False, nuvem.ErroNuvem('Operação encerrada sem confirmação.'))
            try:
                if ok:
                    concluir(valor)
                else:
                    self.falhou(valor)
            except Exception as erro:
                registrar_seguro(erro, self.pasta)
                self.falhou(nuvem.ErroNuvem('A atualização da tela não foi concluída. Confira os dados antes de retomar.'))
            finally:
                tarefa.deleteLater()
                self.mudou.emit()
        tarefa.finished.connect(terminou)
        tarefa.start()

    def falhou(self, erro):
        if self.validacao_real and isinstance(erro, nuvem.SessaoExpirada):
            self.sessao_verificada = False
        self.preparacao = self.revisao = None
        self.agendador.concluir(erro=erro)
        texto = 'Nuvem simulada · temporariamente indisponível' if isinstance(erro, nuvem.ErroTemporario) else 'Nuvem simulada · sincronização pausada'
        self.informar(str(erro) + self.aviso_sessao, texto)

    def conectar(self, email=None, senha=None):
        if self.ocupado:
            return
        if self.validacao_real and (not email or not senha):
            self.informar('Informe o e-mail e a senha do aplicativo no projeto de validação.')
            return
        self.agendador.parar()
        self.sessao_verificada = False
        self.transferencia_confirmada = False
        self.preparacao = self.revisao = None
        if not self.validacao_real:
            self.sessao = None
        def concluir(sessao):
            self.sessao = sessao
            self.sessao_verificada = True
            self.persistir(sessao)
            self.informar(('Conta de validação conectada. Nenhum registro foi transferido.' if self.validacao_real else 'Conta fictícia conectada. Nenhum registro foi transferido.') + self.aviso_sessao, 'Nuvem simulada · conectada')
            self.agendador.ativar()
        self.rodar(lambda: self.cliente.entrar(email, senha) if self.validacao_real else self.cliente.entrar('estudo@example.invalid', 'somente-estudo'), concluir, ('Verificando acesso ao projeto de validação…' if self.validacao_real else 'Conectando somente ao serviço fictício local…'))

    def retomar(self):
        if not self.validacao_real or self.ocupado or not self.sessao:
            return
        self.sessao_verificada = False
        def verificar():
            s = self.cliente.garantir_sessao(self.sessao)
            if self.cliente._post('/rest/v1/rpc/usuario_autorizado', {}, s.token) is not True:
                raise nuvem.ErroNuvem('Esta conta não está autorizada no projeto de validação.')
            return s
        def pronto(s):
            self.sessao = s
            self.sessao_verificada = True
            self.informar('Acesso verificado. Nenhum registro foi transferido.', 'Validação online · conectada')
        self.rodar(verificar, pronto, 'Verificando a sessão do projeto de validação…')

    def desconectar(self):
        if self.ocupado:
            return
        try:
            sessao_windows.remover(self.pasta)
        except OSError:
            self.informar('Não foi possível remover a sessão protegida. Tente novamente.')
            return
        self.agendador.parar()
        self.sessao_verificada = False
        self.transferencia_confirmada = False
        self.sessao = self.preparacao = self.revisao = None
        self.cliente._ultima_sessao = None
        self.informar(('Sessão removida da validação. Dados e cópias preservados.' if self.validacao_real else 'Sessão fictícia removida. Dados e cópias preservados.'), 'Nuvem simulada · desconectada')

    def executar_autenticado(self, funcao):
        if not self.sessao or (self.validacao_real and not self.sessao_verificada):
            raise nuvem.ErroNuvem(('Verifique o acesso à conta de validação antes de continuar.' if self.validacao_real else 'Conecte a conta fictícia antes de continuar.'))
        nova = self.cliente.garantir_sessao(self.sessao)
        return nova, funcao(nova)

    def conferir(self):
        if not self.sessao or self.vinculado or self.ocupado:
            return
        self.agendador.parar()
        self.preparacao = None
        def preparar(sessao):
            financeiro.inicializar()
            return migracao_nuvem.preparar(self.banco, self.cliente, sessao)
        def concluir(resposta):
            self.sessao, self.preparacao = resposta
            r = self.preparacao['relatorio']
            self.informar('Conferência concluída sem transferência. Registros: ' + str(r['resumo']['registros']) + '\nNovos: ' + str(sum(r['novos'].values())) + '\nBackup: ' + r['backup'] + '\nRelatório: ' + str(self.preparacao['caminho']))
        self.rodar(lambda: self.executar_autenticado(preparar), concluir, ('Preservando cópia e conferindo os registros de validação…' if self.validacao_real else 'Preservando cópia e conferindo os registros fictícios…'))

    def transferir(self):
        if not self.preparacao or self.ocupado:
            return
        p = self.preparacao
        self.preparacao = None
        def enviar(sessao):
            p['sessao'] = sessao
            return migracao_nuvem.transferir(p)
        def concluir(resposta):
            self.sessao, r = resposta
            self.transferencia_confirmada = True
            self.informar(('Transferência no projeto de validação concluída. Registros inseridos: ' if self.validacao_real else 'Transferência fictícia validada. Registros inseridos: ') + str(sum(r['inseridos'].values())) + '. Clique em Sincronizar agora para estabelecer o vínculo.')
        self.rodar(lambda: self.executar_autenticado(enviar), concluir, ('Transferindo para o projeto de validação identificado na tela…' if self.validacao_real else 'Transferindo somente para o arquivo do serviço local simulado…'))

    def concluida(self, resposta, automatico=False):
        self.sessao, r = resposta
        self.revisao = None
        self.informar(f"Sincronização{' de validação' if self.validacao_real else ' fictícia'} concluída. Enviadas: {r['enviadas']}; recebidas: {r['recebidas']}.\n" + (f"Backup: {r['backup']}" if r['backup'] else 'Regra de fechamento recebida; cópia local anterior preservada.' if r.get('fechamento_alterado') else 'Sem alterações; não foi necessário novo backup.') + self.aviso_sessao,
            'Nuvem simulada · atualizada' + (' · automática ativa' if self.automatico else ' · modo manual'))
        try:
            if r['recebidas'] or r.get('fechamento_alterado') or not automatico:
                self.recebendo = True
                self.janela.atualizar()
                if self.janela.area == 'Finanças':
                    self.janela.financas.atualizar()
                elif self.janela.area == 'Análises':
                    self.janela.analises.atualizar()
        except Exception as erro:
            registrar_seguro(erro, self.pasta)
            self.informar(('Dados de validação sincronizados; a atualização da tela falhou. Reabra a validação para conferir. ' if self.validacao_real else 'Dados fictícios sincronizados; a atualização da tela falhou. Reabra o estudo para conferir. ') + ('A consulta automática continua agendada.' if self.automatico else 'O modo manual foi preservado.'), self.resumo)
        finally:
            self.recebendo = False
            if automatico:
                self.agendador.concluir()
            else:
                self.agendador.ativar()

    def sincronizar(self, revisao=None, escolhas=None):
        if self.validacao_real and not self.vinculado and not self.transferencia_confirmada:
            self.informar('Confira e confirme a transferência inicial antes de estabelecer o vínculo.')
            return
        if not self.sessao or self.ocupado:
            return
        self.agendador.parar()
        self.preparacao = None
        self.rodar(lambda: self.executar_autenticado(lambda s: sincronizacao.sincronizar(self.banco, self.cliente, s, revisao=revisao, escolhas=escolhas)), self.concluida, ('Comparando versões e sincronizando o projeto de validação…' if self.validacao_real else 'Comparando versões e sincronizando os dados fictícios…'))

    def automaticamente(self):
        if self.validacao_real:
            return
        def consultar(sessao):
            base = sincronizacao.assinatura_base(self.banco)
            return self.cliente.sincronizar(sessao), base
        def recebeu(resposta):
            self.sessao, (snapshot, base) = resposta
            if not self.ativo() or self.agendador.pausado or not self.livre():
                self.agendador.concluir(adiar=True)
                return
            self.rodar(lambda: self.executar_autenticado(lambda s: sincronizacao.sincronizar(self.banco, self.cliente, s, snapshot_inicial=snapshot, somente_se_mudou=True, base_inicial=base)),
                lambda r: self.concluida(r, True), 'Aplicando alterações fictícias…')
        self.rodar(lambda: self.executar_autenticado(consultar), recebeu, 'Consultando o serviço local simulado…', travar=False)

    def conferir_conflitos(self):
        if not self.sessao or not self.vinculado or self.ocupado:
            return
        self.agendador.parar()
        def concluir(resposta):
            self.sessao, self.revisao = resposta
            if self.revisao['conflitos']:
                self.agendador.pausado = True
                self.informar('Escolha uma versão para cada conflito. Nada será substituído sem confirmação.')
            else:
                self.informar('Nenhum conflito encontrado.')
                self.agendador.ativar()
        self.rodar(lambda: self.executar_autenticado(lambda s: sincronizacao.conferir_conflitos(self.banco, self.cliente, s)), concluir, ('Conferindo as duas versões do projeto de validação…' if self.validacao_real else 'Conferindo as duas versões fictícias…'))

    def atualizar_fechamento(self):
        self.preparacao = self.revisao = None
        try:
            self.recebendo = True
            self.janela.atualizar()
            if self.janela.area == 'Finanças':
                self.janela.financas.atualizar()
            elif self.janela.area == 'Análises':
                self.janela.analises.atualizar()
        finally:
            self.recebendo = False

    def consultar_fechamento(self, concluir):
        if self.ocupado or not self.sessao:
            return
        self.agendador.parar()
        from ProgramFeira import fechamento
        def ler(sessao):
            config = self.cliente.fechamentos(sessao)
            mudou = fechamento.guardar(self.banco, config, self.cliente.url, sessao.usuario_id)
            return config, mudou
        def pronto(resposta):
            self.sessao, (config, mudou) = resposta
            if mudou:
                self.atualizar_fechamento()
            concluir(config)
            self.informar(('Histórico consultado no projeto de validação. Nenhuma venda ou parcela foi movida.' if self.validacao_real else 'Histórico de fechamento consultado no serviço fictício. Nenhuma venda ou parcela foi movida.'))
            self.agendador.agendar(self.agendador.INTERVALO)
        self.rodar(lambda: self.executar_autenticado(ler), pronto, ('Consultando o histórico do projeto de validação…' if self.validacao_real else 'Consultando o histórico de fechamento fictício…'))

    def salvar_fechamento(self, versao, vigencia, dia, concluir):
        if self.ocupado or not self.sessao:
            return
        self.agendador.parar()
        from ProgramFeira import fechamento
        def gravar(sessao):
            config = self.cliente.salvar_fechamento(sessao, versao, vigencia, dia)
            import sqlite3
            try:
                fechamento.guardar(self.banco, config, self.cliente.url, sessao.usuario_id)
            except (OSError, ValueError, sqlite3.Error) as erro:
                raise nuvem.ErroNuvem(('O projeto de validação confirmou a regra, mas a cópia local não foi atualizada. Confira o armazenamento e consulte novamente antes de editar.' if self.validacao_real else 'O serviço fictício confirmou a regra, mas a cópia local não foi atualizada. Confira o armazenamento e consulte novamente antes de editar.')) from erro
            return config
        def pronto(resposta):
            self.sessao, config = resposta
            self.atualizar_fechamento()
            concluir(config)
            self.informar(('Nova regra salva no projeto de validação. Valores e parcelas existentes foram preservados.' if self.validacao_real else 'Nova regra fictícia salva por vigência. Valores e parcelas existentes foram preservados.'))
            self.agendador.agendar(self.agendador.INTERVALO)
        self.rodar(lambda: self.executar_autenticado(gravar), pronto, ('Salvando a regra futura no projeto de validação e preservando a cópia local…' if self.validacao_real else 'Salvando a regra futura no serviço fictício e preservando a cópia local…'))

    def alterar_automatico(self, valor):
        if self.validacao_real:
            self.informar('Esta entrada de validação usa sincronização manual.')
            return False
        if self.ocupado:
            return False
        try:
            automacao_nuvem.salvar_preferencia(self.pasta, valor)
        except OSError:
            self.informar('A preferência não pôde ser salva; o modo anterior foi preservado.')
            return False
        self.automatico = valor
        if valor:
            self.agendador.ativar()
        else:
            self.agendador.parar()
        self.informar('Sincronização fictícia automática ativada.' if valor else 'Modo manual ativado para o estudo.')
        return True

    def notificar_alteracao(self):
        if self.recebendo:
            return
        self.preparacao = None
        self.revisao = None
        if self.ativo() and not self.agendador.pausado:
            self.agendador.agendar(2000)
        self.mudou.emit()
