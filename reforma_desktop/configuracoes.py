"""Preferências e backup local Qt; mecanismos remotos aguardam integração própria."""
from pathlib import Path
import sqlite3
from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto, botao, caixa, ajuda
from tema_noturno import C
from ProgramFeira import preferencias, recuperacao, backup_drive
from reforma_desktop.operacoes_backup import Operacao, configurar_drive, copiar_drive
from ProgramFeira.database import banco
from ProgramFeira.semanas import PERIODOS_INICIAIS
from reforma_desktop.temas import NOMES


class Configuracoes(W.QDialog):
    def __init__(self, controlador):
        super().__init__(controlador)
        self.controlador = controlador
        self.pasta = Path(controlador.pasta)
        self.operacao = None
        self.reiniciar = False
        self.setWindowTitle('Configurações — banco de estudo')
        self.resize(620, 580)
        root = W.QVBoxLayout(self)
        root.addWidget(texto('Configurações', 20, bold=True))
        scroll = W.QScrollArea()
        scroll.setWidgetResizable(True)
        corpo = W.QWidget()
        layout = W.QVBoxLayout(corpo)
        layout.setAlignment(Q.Qt.AlignmentFlag.AlignTop)
        box, l = caixa()
        l.addWidget(texto('Ao abrir o programa', 13, bold=True))
        self.periodo = W.QComboBox()
        self.periodo.addItems(PERIODOS_INICIAIS)
        self.periodo.setCurrentText(preferencias.carregar_periodo_inicial(self.pasta))
        self.periodo.setAccessibleName('Período inicial de Vendas')
        l.addWidget(self.periodo)
        linha = W.QHBoxLayout()
        linha.addWidget(botao('Salvar período inicial', self.salvar_periodo, 'check'))
        linha.addWidget(ajuda('Período inicial', 'Será usado na próxima abertura de Vendas. Salvar não aplica filtros, não muda a seleção atual nem altera os dados. A semana atual continua independente.'))
        l.addLayout(linha)
        layout.addWidget(box)
        box, l = caixa()
        l.addWidget(texto('Aparência', 13, bold=True))
        self.tema = W.QComboBox()
        for chave, nome in NOMES.items():
            self.tema.addItem(nome, chave)
        self.tema.setCurrentIndex(self.tema.findData(preferencias.carregar_tema(self.pasta)))
        self.tema.setAccessibleName('Tema para a próxima abertura')
        l.addWidget(self.tema)
        linha = W.QHBoxLayout()
        linha.addWidget(botao('Salvar tema para próxima abertura', self.salvar_tema, 'check'))
        linha.addWidget(ajuda('Tema', 'Noite preserva a identidade Noturno aprovada. Claro, Grafite, Areia e Aurora usam as paletas existentes adaptadas ao Qt. A mudança será aplicada ao fechar e abrir esta entrada; não reconstrói telas ou descarta edições.'))
        l.addLayout(linha)
        layout.addWidget(box)
        box, l = caixa()
        l.addWidget(texto('Dados de estudo', 13, bold=True))
        caminho = texto(str(banco.CAMINHO_BANCO), 9, C['muted'])
        caminho.setWordWrap(True)
        caminho.setTextInteractionFlags(Q.Qt.TextInteractionFlag.TextSelectableByMouse)
        l.addWidget(caminho)
        linha = W.QHBoxLayout()
        linha.addWidget(botao('Criar backup local agora', self.backup, 'download'))
        linha.addWidget(ajuda('Backup local', 'Cria uma cópia SQLite verificada na pasta backups deste estudo. Não envia ao Drive e não substitui dados. A verificação de integridade não substitui o banco; restaurar substitui e exige reabrir o estudo.'))
        l.addLayout(linha)
        layout.addWidget(box)
        for titulo, acao, dica in [
            ('Verificar integridade de um backup…', self.verificar, 'Ensaia a recuperação em pasta temporária. Não altera os dados em uso nem comprova a autoria do arquivo.'),
            ('Restaurar backup…', self.restaurar, 'Substitui os dados deste estudo. Preserva uma cópia anterior e encerra esta sessão para reabrir com os dados restaurados.'),
            ('Escolher pasta do Drive…', self.escolher_drive, 'Cria um conjunto separado, Gestao-da-Feira-Estudo-Qt-Backups. Nunca escolha uma pasta pública. O programa não verifica permissões ou envio remoto.'),
            ('Fazer cópia no Drive agora', self.drive, 'Grava e confere uma cópia na pasta configurada. O Google Drive para computador faz o envio à nuvem. Também cria uma cópia ao fechar o estudo, quando configurado.'),
            ('Desativar cópia no Drive', self.desativar_drive, 'Remove somente a configuração deste estudo. Não apaga cópias existentes.')]:
            linha = W.QHBoxLayout()
            linha.addWidget(botao(titulo, acao))
            linha.addWidget(ajuda(titulo, dica))
            l.addLayout(linha)
        self.destino_drive = texto('', 9, C['muted'])
        self.destino_drive.setWordWrap(True)
        l.addWidget(self.destino_drive)
        self.mostrar_drive()
        l.addWidget(botao('Sessão e sincronização — serviço simulado…', controlador.conexao_nuvem, 'arrow-right-left'))
        l.addWidget(botao('Regra de fechamento por vigência…', controlador.configurar_fechamento, 'calendar-days'))
        pendentes = texto('Drive configurado cria uma cópia ao fechar. Sessão/sincronização usa serviço fictício, sem conta real. O atualizador Qt segue na sequência do plano. A versão estável não foi alterada.', 9, C['muted'])
        pendentes.setWordWrap(True)
        layout.addWidget(pendentes)
        scroll.setWidget(corpo)
        root.addWidget(scroll, 1)
        self.status = texto('', 10, C['muted'])
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addWidget(botao('Fechar', self.reject))

    def salvar_periodo(self):
        try:
            preferencias.salvar_periodo_inicial(self.pasta, self.periodo.currentText())
        except (OSError, ValueError) as erro:
            self.status.setText('Período não salvo: ' + str(erro))
            return
        self.status.setText('Período salvo para a próxima abertura. A consulta atual foi preservada.')

    def salvar_tema(self):
        try:
            preferencias.salvar_tema(self.pasta, self.tema.currentData())
        except (OSError, ValueError) as erro:
            self.status.setText('Tema não salvo: ' + str(erro))
            return
        self.status.setText('Tema salvo. Feche e abra a entrada de estudo para aplicar; seus dados não serão alterados.')

    def backup(self):
        try:
            copia = banco.criar_backup()
        except (OSError, ValueError, sqlite3.Error) as erro:
            self.status.setText('Backup não concluído: ' + str(erro))
            return
        self.status.setText('Backup local criado e verificado:\n' + str(copia))

    def reject(self):
        if self.operacao is not None:
            return
        super().reject()
        if self.reiniciar:
            self.controlador.close()

    def closeEvent(self, evento):
        if self.operacao is not None:
            evento.ignore()
        else:
            super().closeEvent(evento)

    def executar(self, tarefa, concluir):
        if self.operacao is not None or self.reiniciar:
            return
        self.controlador.relogio.stop()
        self.status.setText('Aguarde: preparando e verificando a cópia…')
        self.findChild(W.QScrollArea).setEnabled(False)
        op = Operacao(tarefa, self)
        self.operacao = op
        self._retorno = None
        op.resultado.connect(self.receber)
        def terminou():
            self.operacao = None
            self.findChild(W.QScrollArea).setEnabled(True)
            sucesso, valor = self._retorno or (False, 'Operação encerrada sem resultado.')
            if sucesso:
                concluir(valor)
            else:
                self.status.setText('Operação não concluída: ' + str(valor))
            if not self.reiniciar:
                self.controlador.relogio.start()
            op.deleteLater()
        op.finished.connect(terminou)
        op.start()

    def receber(self, sucesso, valor):
        self._retorno = (sucesso, valor)

    def arquivo_backup(self):
        return W.QFileDialog.getOpenFileName(self, 'Selecionar backup SQLite', str(self.pasta / 'backups'), 'Banco SQLite (*.db);;Todos os arquivos (*)')[0]

    def verificar(self):
        arquivo = self.arquivo_backup()
        if arquivo:
            self.executar(lambda: recuperacao.testar_recuperacao(arquivo),
                lambda r: self.status.setText('Recuperação verificada em pasta temporária. Banco em uso preservado.\nRegistros por tabela: ' + str(r['tabelas'])))

    def restaurar(self):
        arquivo = self.arquivo_backup()
        if not arquivo:
            return
        resposta = W.QMessageBox.question(self, 'Restaurar banco de estudo',
            'Substituir os dados deste estudo pelo backup? Uma cópia anterior será preservada. Feche outras instâncias. Ao concluir, esta sessão será encerrada: abra novamente o estudo. A sincronização automática ficará desativada até você conferir e reativar. Preferências e sessão de conta não fazem parte do backup.',
            W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No)
        if resposta != W.QMessageBox.StandardButton.Yes:
            return
        if not self.controlador.nuvem.alterar_automatico(False):
            self.status.setText('Restauração cancelada: não foi possível pausar a automação para a próxima abertura.')
            return
        self.executar(lambda: banco.restaurar_backup(arquivo), self.restaurado)

    def restaurado(self, anterior):
        # Não reutiliza snapshots, formulários ou histórico de fechamento em memória.
        self.reiniciar = True
        self.controlador.nuvem.agendador.pausado = True
        self.controlador.nuvem.agendador.parar()
        self.controlador.relogio.stop()
        self.findChild(W.QScrollArea).setEnabled(False)
        self.status.setText('Dados restaurados. Cópia anterior: ' + str(anterior) + '\nFeche esta janela e abra novamente o estudo. Não continue editando nesta sessão.')
        self.controlador.setEnabled(False)
        self.setEnabled(True)

    def escolher_drive(self):
        pasta = W.QFileDialog.getExistingDirectory(self, 'Selecionar pasta sincronizada pelo Google Drive')
        if not pasta:
            return
        try:
            dados = configurar_drive(banco.CAMINHO_BANCO, pasta)
            self.mostrar_drive()
            self.status.setText('Pasta de estudo configurada: ' + dados['pasta'] + '\nUse Fazer cópia agora. Envio remoto não verificado; cópia ao fechar ativada neste estudo.')
        except (OSError, ValueError) as erro:
            self.status.setText('Configuração não salva: ' + str(erro))

    def drive(self):
        def concluido(r):
            self.status.setText('Cópia verificada na pasta: ' + str(r['arquivo']) + '\nConfira o envio no Drive pelo navegador.\n' + '\n'.join(r['avisos']))
        self.executar(lambda: copiar_drive(banco.CAMINHO_BANCO), concluido)

    def desativar_drive(self):
        try:
            backup_drive.desativar(banco.CAMINHO_BANCO)
            self.mostrar_drive()
            self.status.setText('Drive desativado neste estudo. Cópias existentes preservadas.')
        except OSError as erro:
            self.status.setText('Configuração não salva: ' + str(erro))

    def mostrar_drive(self):
        try:
            dados = backup_drive.carregar_config(self.pasta)
            self.destino_drive.setText('Pasta configurada: ' + dados['pasta'] if dados.get('pasta') else 'Drive não configurado neste estudo.')
        except ValueError as erro:
            self.destino_drive.setText(str(erro))
