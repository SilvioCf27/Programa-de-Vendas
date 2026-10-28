"""Orquestração Qt do ensaio de atualização; nenhuma instalação real é feita."""
import json
import os
from reforma_desktop.diagnostico_qt import pasta_do_objeto, registrar_seguro
from pathlib import Path
import tempfile
from PySide6 import QtCore as Q, QtWidgets as W
from reforma_desktop.servico_atualizacao_estudo import ServicoEstudo, CENARIOS


class Tarefa(Q.QThread):
    resultado = Q.Signal(bool, object)

    def __init__(self, funcao, parent):
        super().__init__(parent)
        self.funcao = funcao
        self.pasta_diagnostico = pasta_do_objeto(parent)

    def run(self):
        try:
            r = self.funcao()
        except ValueError as erro:
            self.resultado.emit(False, str(erro))
        except Exception as erro:
            registrar_seguro(erro, self.pasta_diagnostico)
            self.resultado.emit(False, 'Ensaio não concluído. Confira o armazenamento e tente novamente. Nenhum programa foi instalado.')
        else:
            self.resultado.emit(True, r)


class Atualizacoes(Q.QObject):
    mudou = Q.Signal()

    def __init__(self, janela):
        super().__init__(janela)
        self.janela = janela
        self.servico = ServicoEstudo(Path(janela.pasta)/'vendas.db')
        self.preferencia = Path(janela.pasta)/'atualizacoes.json'
        self.automatica = self.ler_preferencia()
        self.ocupado = False
        self.release = self.preparacao = self.resultado = None
        self.tarefa = self.timer = None
        self.status = 'Ensaio local: nenhuma consulta ao GitHub, instalação ou reinício real.'
        if self.automatica:
            self.agendar(12000)

    def ler_preferencia(self):
        try:
            d = json.loads(self.preferencia.read_text(encoding='utf-8'))
            return isinstance(d,dict) and d.get('consultar') is True
        except (OSError,ValueError):
            # O estudo não deve anunciar uma versão fictícia sem solicitação.
            return False

    def informar(self, mensagem):
        self.status = mensagem
        self.mudou.emit()

    def alterar_automatica(self, valor):
        if self.ocupado:
            return
        nome = None
        try:
            fd,nome = tempfile.mkstemp(dir=self.preferencia.parent,prefix='.atualizacoes-',suffix='.json')
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump({'consultar':bool(valor)},f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(nome,self.preferencia)
        except OSError:
            self.informar('Não foi possível salvar a preferência. O modo anterior foi preservado.')
            return
        finally:
            if nome is not None:
                Path(nome).unlink(missing_ok=True)
        self.automatica = bool(valor)
        if self.automatica:
            self.agendar(12000)
        else:
            self.parar()
        self.informar('Consulta automática fictícia ativada para o estudo.' if valor else 'Consulta automática do estudo desativada.')

    def parar(self):
        if self.timer is not None:
            self.timer.stop()
            self.timer.deleteLater()
            self.timer = None

    def agendar(self, atraso):
        self.parar()
        if not self.automatica:
            return
        self.timer = Q.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.automaticamente)
        self.timer.start(atraso)

    def pode_atualizar(self):
        if not self.janela.isEnabled() or self.janela.nuvem.ocupado or getattr(self.janela,'_backup_fechamento',None):
            raise ValueError('Aguarde a operação em andamento antes de iniciar o ensaio de atualização.')
        for d in self.janela.findChildren(W.QDialog):
            if d.isVisible() and (getattr(d,'operacao',None) is not None or not getattr(d,'permite_atualizacao',False)):
                raise ValueError('Finalize a edição ou a operação aberta antes de iniciar o ensaio.')

    def automaticamente(self):
        self.parar()
        if not self.automatica:
            return
        try:
            self.pode_atualizar()
        except ValueError:
            self.agendar(30000)
            return
        if self.ocupado:
            self.agendar(30000)
            return
        # Apenas consulta: nunca prepara, instala ou abre confirmação sozinha.
        self.verificar(silenciosa=True)

    def selecionar_cenario(self, cenario):
        if self.ocupado or cenario not in CENARIOS:
            return
        self.servico.limpar()
        self.servico.cenario = cenario
        self.release = self.preparacao = self.resultado = None
        self.informar('Cenário selecionado: '+CENARIOS[cenario]+'. Clique em Verificar ensaio.')

    def rodar(self, funcao, concluir, mensagem, silenciosa=False):
        if self.ocupado:
            return
        try:
            self.pode_atualizar()
        except ValueError as erro:
            if not silenciosa:
                self.informar(str(erro))
            return
        self.ocupado = True
        self.informar(mensagem)
        self.janela.relogio.stop()
        self.janela.setEnabled(False)
        resposta = []
        t = Tarefa(funcao,self)
        self.tarefa = t
        t.resultado.connect(lambda ok,valor:resposta.append((ok,valor)))
        def terminou():
            t.wait()  # Libera a UI só após terminar também a thread nativa.
            self.ocupado = False
            self.tarefa = None
            self.janela.setEnabled(True)
            self.janela.relogio.start()
            ok,valor = resposta[0] if resposta else (False,'Ensaio encerrado sem resultado.')
            try:
                if ok:
                    concluir(valor)
                else:
                    self.release = self.preparacao = self.resultado = None
                    self.servico.limpar()
                    self.informar('Ensaio interrompido. Nenhum programa foi instalado.\n'+str(valor))
            finally:
                t.deleteLater()
                self.mudou.emit()
        t.finished.connect(terminou)
        t.start()

    def verificar(self, silenciosa=False):
        if self.ocupado:
            return
        self.release = self.preparacao = self.resultado = None
        self.servico.limpar()
        def recebeu(release):
            self.release = release
            self.informar('Versão fictícia disponível: '+release['versao']+'. Não é uma publicação real.' if release else 'Ensaio: nenhuma versão mais recente. A base funcional continua inalterada.')
        self.rodar(self.servico.consultar,recebeu,'Consultando metadados fictícios locais…',silenciosa)

    def preparar(self):
        if self.release is None or self.ocupado:
            return
        self.preparacao = self.resultado = None
        def pronto(preparacao):
            self.preparacao = preparacao
            self.informar('SHA-256 e estrutura do pacote fictício conferidos. O teste da candidata foi simulado. Clique em Ensaio da troca para exercitar backup e preparação, sem instalar ou reiniciar.')
        self.rodar(lambda:self.servico.preparar(self.release),pronto,'Conferindo o pacote fictício local. Nenhum download real…')

    def instalar(self):
        if self.preparacao is None or self.ocupado:
            return
        def pronto(r):
            self.resultado = r
            self.preparacao = None
            self.informar(r['observacao']+'\nBackup da cópia fictícia: '+r['backup']+'\nO banco do estudo e as pastas do Drive não foram alterados.')
        self.rodar(self.servico.instalar,pronto,'Ensaiando backup e preparação da troca, sem executar processos…')
