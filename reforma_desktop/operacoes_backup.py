"""Operações de cópia fora da thread gráfica; usa as proteções do núcleo."""
from reforma_desktop.diagnostico_qt import pasta_do_objeto, registrar_seguro
from pathlib import Path
from PySide6 import QtCore as Q, QtWidgets as W
from ProgramFeira import backup_drive

PASTA_ESTUDO = 'Gestao-da-Feira-Estudo-Qt-Backups'


def configurar_drive(banco, pasta):
    # Nunca compartilhar o conjunto/retenção de backups com a versão funcional.
    raiz = Path(pasta)
    if raiz.name != PASTA_ESTUDO:
        raiz = raiz / PASTA_ESTUDO
    from ProgramFeira.database.seguranca_arquivos import sem_redirecionamentos
    sem_redirecionamentos(raiz)
    raiz.mkdir(exist_ok=True)
    return backup_drive.configurar(banco, raiz)


def copiar_drive(banco, *, producao=False):
    dados = backup_drive.carregar_config(Path(banco).parent)
    if not producao and Path(dados.get('pasta', '')).name != PASTA_ESTUDO:
        raise ValueError('Escolha uma pasta de Drive própria para este estudo antes de copiar.')
    return backup_drive.executar(banco, dados)


class Operacao(Q.QThread):
    resultado = Q.Signal(bool, object)

    def __init__(self, executar, parent=None):
        super().__init__(parent)
        self.executar = executar
        self.pasta_diagnostico = pasta_do_objeto(parent)

    def run(self):
        try:
            valor = self.executar()
        except Exception as erro:
            registrar_seguro(erro, self.pasta_diagnostico)
            self.resultado.emit(False, str(erro))
        else:
            self.resultado.emit(True, valor)


class Progresso(W.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.concluido = False
        self.setWindowTitle('Backup ao fechar — estudo')
        self.setWindowFlag(Q.Qt.WindowType.WindowCloseButtonHint, False)
        self.setWindowModality(Q.Qt.WindowModality.ApplicationModal)
        layout = W.QVBoxLayout(self)
        layout.addWidget(W.QLabel('Criando e verificando a cópia na pasta do Drive…'))
        barra = W.QProgressBar()
        barra.setRange(0, 0)
        layout.addWidget(barra)

    def reject(self):
        if self.concluido:
            super().reject()

    def closeEvent(self, evento):
        if self.concluido:
            super().closeEvent(evento)
        else:
            evento.ignore()


def fechar_com_backup(janela, evento):
    """Fechamento assíncrono, com opção explícita se a cópia falhar."""
    from ProgramFeira.database import banco
    if getattr(janela, '_fechamento_autorizado', False):
        evento.accept()
        return
    if getattr(janela, '_backup_fechamento', None) is not None:
        evento.ignore()
        return
    try:
        dados = backup_drive.carregar_config(Path(banco.CAMINHO_BANCO).parent)
    except ValueError as erro:
        dados = None
        falha = str(erro)
    else:
        falha = None
    if dados == {} or (dados is not None and not dados.get('pasta')):
        evento.accept()
        return
    evento.ignore()

    def finalizar(sucesso, mensagem=''):
        if not sucesso:
            resposta = W.QMessageBox.question(janela, 'Backup não concluído',
                'A cópia na pasta do Drive não foi concluída. Os dados permanecem locais.\n' + mensagem + '\n\nFechar mesmo assim?',
                W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No)
            if resposta != W.QMessageBox.StandardButton.Yes:
                janela.relogio.start()
                return
        janela._fechamento_autorizado = True
        janela.close()

    if falha:
        finalizar(False, falha)
        return
    progresso = Progresso(janela)
    progresso.show()
    janela.relogio.stop()
    resultado = []
    caminho = Path(banco.CAMINHO_BANCO)
    op = Operacao(lambda: copiar_drive(caminho, producao=getattr(janela, 'producao', False)), janela)
    janela._backup_fechamento = op
    op.resultado.connect(lambda ok, valor: resultado.append((ok, valor)))
    def terminou():
        op.wait()  # Libera a UI só após terminar também a thread nativa.
        janela._backup_fechamento = None
        progresso.concluido = True
        progresso.close()
        progresso.deleteLater()
        ok, valor = resultado[0] if resultado else (False, 'Operação encerrada sem resultado.')
        if ok and valor['avisos']:
            W.QMessageBox.warning(janela, 'Cópia criada com observações', '\n'.join(valor['avisos']))
        op.deleteLater()
        finalizar(ok, '' if ok else str(valor))
    op.finished.connect(terminou)
    op.start()
