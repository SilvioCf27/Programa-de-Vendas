"""Prévia e edição futura de fechamento Qt; mesma regra de negócio do núcleo."""
from datetime import date, timedelta
from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto, botao, ajuda, caixa
from tema_noturno import C
from estado_demo import MESES
from ProgramFeira import fechamento


class ConfiguracaoFechamento(W.QDialog):
    def __init__(self, controlador):
        super().__init__(controlador)
        self.controlador = controlador
        self.nuvem = controlador.nuvem
        self.hoje = controlador.servico.hoje
        self.config = fechamento.estado()
        self.conferida = False
        self.proposta = None
        self.setWindowTitle('Regra de fechamento — estudo')
        self.resize(720, 560)
        root = W.QVBoxLayout(self)
        root.addWidget(texto('Regra dos próximos fechamentos', 20, bold=True))
        aviso = texto(('Projeto: ' + self.nuvem.cliente.url + '. A regra preserva o histórico.') if self.nuvem.real else 'Serviço fictício local. A regra só começa em um mês futuro e preserva o histórico. Fechamento é diferente do prazo para pagar a fatura.', 11, C['muted'])
        aviso.setWordWrap(True)
        root.addWidget(aviso)
        self.consultar = botao('Consultar regra do projeto' if self.nuvem.real else 'Consultar regra do serviço simulado', self.carregar, 'rotate-ccw')
        root.addWidget(self.consultar)
        box, l = caixa()
        linha = W.QHBoxLayout()
        self.dia = W.QSpinBox()
        self.dia.setRange(1, 31)
        self.ano = W.QSpinBox()
        self.ano.setRange(1900, 9998)
        self.mes = W.QComboBox()
        self.mes.addItems(MESES)
        hoje = self.hoje()
        seguinte = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1)
        self.ano.setValue(seguinte.year)
        self.mes.setCurrentIndex(seguinte.month-1)
        self.dia.setValue(fechamento.dia_no_mes(seguinte.year, seguinte.month, self.config['historico']))
        for rotulo, campo in [('Dia de fechamento', self.dia), ('Primeira fatura com a regra', self.mes), ('Ano', self.ano)]:
            coluna = W.QVBoxLayout()
            coluna.addWidget(texto(rotulo, 10, C['muted']))
            campo.setAccessibleName(rotulo)
            coluna.addWidget(campo)
            linha.addLayout(coluna)
        l.addLayout(linha)
        self.previa = texto('', 11)
        self.previa.setWordWrap(True)
        l.addWidget(self.previa)
        l.addWidget(ajuda('O que muda?', 'O dia escolhido vale para o fechamento da primeira fatura indicada. Pode encurtar ou alongar o período ainda aberto. Um dia inexistente no mês usa seu último dia. Não recalcula valores nem move parcelas já cadastradas.'))
        root.addWidget(box)
        self.historico = W.QPlainTextEdit()
        self.historico.setReadOnly(True)
        self.historico.setAccessibleName('Histórico de regras de fechamento')
        self.historico.setMaximumHeight(150)
        root.addWidget(self.historico)
        nota = texto('Compras feitas no próprio dia do fechamento entram na fatura seguinte. Parcelas já cadastradas mantêm suas datas; confira as futuras se mudar a regra.', 10, C['muted'])
        nota.setWordWrap(True)
        root.addWidget(nota)
        self.erro = texto('', 10)
        self.erro.setWordWrap(True)
        root.addWidget(self.erro)
        self.status = texto('', 10, C['muted'])
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        acoes = W.QHBoxLayout()
        acoes.addWidget(botao('Fechar', self.reject))
        self.salvar = botao('Salvar nova regra', self.enviar, 'check', primary=True)
        acoes.addWidget(self.salvar)
        root.addLayout(acoes)
        for campo in (self.dia, self.ano):
            campo.valueChanged.connect(self.atualizar)
        self.mes.currentIndexChanged.connect(self.atualizar)
        self.nuvem.mudou.connect(self.controles)
        self.mostrar_historico()
        self.atualizar()

    def parametros(self):
        if not self.ano.hasAcceptableInput() or not self.dia.hasAcceptableInput():
            raise ValueError('Confirme o ano e o dia antes de salvar.')
        self.ano.interpretText()
        self.dia.interpretText()
        return f'{self.ano.value():04d}-{self.mes.currentIndex()+1:02d}-01', self.dia.value()

    def mostrar_historico(self):
        self.historico.setFixedHeight(min(150, 55 + 22*len(self.config['historico'])))
        self.historico.setPlainText('Regra inicial: dia 09.\n' + '\n'.join(f"A partir de {date.fromisoformat(r['vigencia']):%m/%Y}: dia {r['dia']:02d}." for r in self.config['historico']))

    def atualizar(self):
        try:
            vigencia, dia = self.parametros()
            self.proposta = fechamento.propor(self.config, vigencia, dia, hoje=self.hoje())
            primeiro = date.fromisoformat(vigencia)
            anterior = primeiro - timedelta(days=1)
            periodos = [fechamento.periodo(d.year, d.month, self.proposta['historico']) for d in (anterior, primeiro)]
            self.previa.setText('Prévia dos períodos de vendas:\n' + '\n'.join(f'{date.fromisoformat(i):%d/%m/%Y} a {date.fromisoformat(f):%d/%m/%Y}' for i, f in periodos))
            self.erro.setText('')
        except ValueError as erro:
            self.proposta = None
            self.previa.setText('')
            self.erro.setText(str(erro))
        self.controles()

    def controles(self):
        ocupado = self.nuvem.ocupado
        conectado = bool(self.nuvem.sessao)
        self.consultar.setEnabled(conectado and not ocupado)
        for campo in (self.dia, self.ano, self.mes):
            campo.setEnabled(self.conferida and conectado and not ocupado)
        self.salvar.setEnabled(self.conferida and conectado and not ocupado and self.proposta is not None)
        self.status.setText(self.nuvem.status if conectado else 'Histórico local em leitura. Verifique o acesso em Configurações → Conexão e consulte a regra antes de editar.')

    def receber(self, config):
        self.config = fechamento.validar(config)
        self.conferida = True
        self.mostrar_historico()
        self.atualizar()

    def carregar(self):
        if not self.nuvem.sessao or self.nuvem.ocupado:
            return
        self.conferida = False
        self.nuvem.consultar_fechamento(self.receber)

    def enviar(self):
        if not self.conferida or self.nuvem.ocupado or not self.nuvem.sessao:
            return
        self.atualizar()
        if self.proposta is None:
            return
        vigencia, dia = self.parametros()
        destino = ('A regra será salva em ' + self.nuvem.cliente.url + '.') if self.nuvem.real else 'A regra será salva somente no estudo.'
        if W.QMessageBox.question(self, 'Salvar fechamento futuro', f'Usar o dia {dia:02d} a partir da fatura de {date.fromisoformat(vigencia):%m/%Y}?\nO período ainda aberto pode mudar. Valores e parcelas existentes não serão movidos. {destino}', W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No) != W.QMessageBox.StandardButton.Yes:
            return
        self.conferida = False
        self.nuvem.salvar_fechamento(self.config['versao'], vigencia, dia, self.receber)

    def reject(self):
        if not self.nuvem.ocupado:
            super().reject()

    def closeEvent(self, evento):
        if self.nuvem.ocupado:
            evento.ignore()
        else:
            super().closeEvent(evento)
