"""Controles de atualização Qt em ensaio explícito, sem tocar a instalação real."""
from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto, botao, ajuda
from tema_noturno import C
from ProgramFeira.versao import VERSAO
from reforma_desktop.servico_atualizacao_estudo import CENARIOS


class PainelAtualizacao(W.QDialog):
    def __init__(self,janela):
        super().__init__(janela)
        self.permite_atualizacao = True
        self.controlador = janela.atualizador
        real = self.controlador.real
        self.setWindowTitle('Atualizações — ensaio Qt')
        self.resize(720,580)
        l = W.QVBoxLayout(self)
        l.addWidget(texto('Atualizações — ensaio isolado',20,bold=True))
        l.addWidget(texto('Base funcional: '+VERSAO+' · Reforma para a futura 2.0',11,C['muted']))
        aviso = texto('Este estudo não consulta o GitHub nem instala programas. O pacote, o teste do programa e a troca de pastas são simulados. A conferência SHA-256, a extração e o backup são feitos em uma pasta temporária separada.',11,C['muted'])
        aviso.setWordWrap(True)
        l.addWidget(aviso)
        l.addWidget(texto('Cenário para testar',10,C['muted']))
        self.cenario = W.QComboBox()
        for chave,nome in CENARIOS.items():
            self.cenario.addItem(nome,chave)
        self.cenario.setCurrentIndex(self.cenario.findData(getattr(self.controlador.servico, 'cenario', 'normal')))
        self.cenario.setAccessibleName('Cenário fictício da atualização')
        self.cenario.currentIndexChanged.connect(lambda:self.controlador.selecionar_cenario(self.cenario.currentData()))
        l.addWidget(self.cenario)
        self.status = W.QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setAccessibleName('Resultado do ensaio de atualização')
        self.status.setMaximumHeight(160)
        l.addWidget(self.status,1)
        self.auto = W.QCheckBox('Consultar ao abrir o estudo (simulado; nunca instala automaticamente)')
        self.auto.toggled.connect(self.controlador.alterar_automatica)
        l.addWidget(self.auto)
        self.botoes = {}
        for chave,rotulo,funcao,dica in [
            ('verificar','Verificar ensaio',lambda:self.controlador.verificar(),'Exercita metadados de release estável e completa. Os dados vêm de uma fixture local, nunca da rede.'),
            ('preparar','Conferir pacote fictício',self.controlador.preparar,'Reutiliza as verificações de origem, SHA-256 e caminhos do ZIP. O teste do executável é simulado; não comprova um pacote Windows real.'),
            ('instalar','Ensaio da troca — sem instalar',self.confirmar,'Pede confirmação. Usa uma cópia temporária do banco, cria seu backup e simula a preparação da troca. Não troca pastas nem executa PowerShell.')]:
            linha = W.QHBoxLayout()
            b = botao(rotulo,funcao)
            self.botoes[chave] = b
            linha.addWidget(b)
            linha.addWidget(ajuda(rotulo,dica))
            l.addLayout(linha)
        l.addWidget(botao('Fechar',self.reject))
        if real:
            from reforma_desktop.versao import VERSAO as versao_desktop
            self.setWindowTitle('Atualizações')
            # Substitui os textos de ensaio, sem oferecer cenários fictícios.
            for i, valor in enumerate(('Atualizações', 'Versão instalada: '+versao_desktop,
                    'A nova versão será baixada e testada antes da confirmação. A instalação preserva backup e a pasta anterior.', '')):
                widget = l.itemAt(i).widget()
                widget.setText(valor)
                if not valor:
                    widget.hide()
            self.cenario.hide()
            self.auto.setText('Consultar ao abrir (nunca instala automaticamente)')
            for chave, rotulo in [('verificar','Verificar atualizações'),('preparar','Baixar e conferir'),('instalar','Instalar e reiniciar')]:
                self.botoes[chave].setText(rotulo)
            for ajuda_widget in self.findChildren(W.QPushButton):
                if ajuda_widget.text() == '?':
                    ajuda_widget.hide()
        self.controlador.mudou.connect(self.atualizar)
        self.atualizar()

    def atualizar(self):
        c = self.controlador
        self.status.setPlainText(c.status)
        self.cenario.setEnabled(not c.ocupado)
        self.auto.setEnabled(not c.ocupado)
        with Q.QSignalBlocker(self.auto):
            self.auto.setChecked(c.automatica)
        self.botoes['verificar'].setEnabled(not c.ocupado)
        self.botoes['preparar'].setEnabled(c.release is not None and not c.ocupado)
        self.botoes['instalar'].setEnabled(c.preparacao is not None and not c.ocupado)

    def confirmar(self):
        c = self.controlador
        if c.preparacao is None or c.ocupado:
            return
        if W.QMessageBox.question(self,'Instalar atualização' if c.real else 'Ensaiar atualização',
            ('Instalar a versão conferida e reiniciar o programa? Será criado um backup e a pasta anterior do aplicativo será preservada. A configuração de cópia no Drive existente será respeitada.' if c.real else 'Exercitar backup e preparação da troca com uma cópia temporária do banco de estudo? Nenhum executável real será trocado ou iniciado e nenhuma cópia será enviada ao Drive.'),
            W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No,W.QMessageBox.StandardButton.No)==W.QMessageBox.StandardButton.Yes:
            c.instalar()

    def reject(self):
        if not self.controlador.ocupado:
            super().reject()

    def closeEvent(self,evento):
        if self.controlador.ocupado:
            evento.ignore()
        else:
            super().closeEvent(evento)
