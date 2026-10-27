"""Preferências e backup local Qt; mecanismos remotos aguardam integração própria."""
from pathlib import Path
import sqlite3
from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto, botao, caixa, ajuda
from tema_noturno import C
from ProgramFeira import preferencias
from ProgramFeira.database import banco
from ProgramFeira.semanas import PERIODOS_INICIAIS
from reforma_desktop.temas import NOMES


class Configuracoes(W.QDialog):
    def __init__(self, controlador):
        super().__init__(controlador)
        self.controlador = controlador
        self.pasta = Path(controlador.pasta)
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
        linha.addWidget(ajuda('Backup local', 'Cria uma cópia SQLite verificada na pasta backups deste estudo. Não envia ao Drive e não substitui dados. Restauração, Drive e nuvem serão integrados nas próximas partes.'))
        l.addLayout(linha)
        layout.addWidget(box)
        pendentes = texto('Restauração/verificação de cópias, Drive, sessão/nuvem, edição do fechamento e atualizador continuam disponíveis na versão estável. Suas telas Qt serão integradas na sequência do plano.', 9, C['muted'])
        pendentes.setWordWrap(True)
        layout.addWidget(pendentes)
        scroll.setWidget(corpo)
        root.addWidget(scroll, 1)
        self.status = texto('', 10, C['muted'])
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addWidget(botao('Fechar', self.accept))

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
