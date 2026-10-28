"""Datas explícitas e seletor financeiro adaptativo, sem importar widgets Tk."""
from datetime import date, timedelta
from decimal import Decimal
from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto
from tema_noturno import C
from estado_demo import MESES
from reforma_desktop.financas import ConsultaFinanceira, semanas_do_mes


def valor_br(centavos):
    return f'{Decimal(centavos) / 100:.2f}'.replace('.', ',')


class DataValidada(W.QDateEdit):
    """Não transforma uma edição incompleta em confirmação da data anterior."""
    def __init__(self, *args, **kwargs):
        self.entrada_incompleta = False
        super().__init__(*args, **kwargs)
        self.setCalendarPopup(True)
        self.lineEdit().textEdited.connect(self.marcar_edicao)
        self.calendarWidget().clicked.connect(self.confirmar_data)

    def marcar_edicao(self, *args):
        self.entrada_incompleta = not self.hasAcceptableInput()

    def confirmar_data(self, *args):
        self.entrada_incompleta = False

    def setDate(self, data):
        self.entrada_incompleta = False
        super().setDate(data)

    def stepBy(self, passos):
        super().stepBy(passos)
        self.entrada_incompleta = not self.hasAcceptableInput()

    def focusOutEvent(self, evento):
        if not self.hasAcceptableInput():
            self.entrada_incompleta = True
        super().focusOutEvent(evento)


def campo_data(data, nome):
    w = DataValidada(Q.QDate(date.fromisoformat(data) if isinstance(data, str) else data))
    w.setCalendarPopup(True)
    w.setDisplayFormat('dd/MM/yyyy')
    w.setAccessibleName(nome)
    return w


def data_iso(campo):
    if getattr(campo, 'entrada_incompleta', False) or not campo.hasAcceptableInput():
        raise ValueError('Confirme uma data válida pelo calendário ou complete a digitação.')
    campo.interpretText()
    return campo.date().toPython().isoformat()


class SeletorFinanceiro(W.QWidget):
    alterado = Q.Signal()

    def __init__(self, referencia, tipo='Fechamento', fixo=False):
        super().__init__()
        self.tipo = W.QComboBox()
        self.tipo.addItems(['Semana', 'Mês', 'Fechamento', 'Ano'])
        self.tipo.setCurrentText(tipo)
        self.ano = W.QSpinBox()
        self.ano.setRange(1900, 9998)
        self.ano.setValue(referencia.year)
        self.mes = W.QComboBox()
        self.mes.addItems(MESES)
        self.mes.setCurrentIndex(referencia.month - 1)
        self.semana = W.QComboBox()
        self.grade = W.QGridLayout(self)
        self.grade.setContentsMargins(0, 0, 0, 0)
        self.grade.setAlignment(Q.Qt.AlignmentFlag.AlignLeft)
        self.ano.setFixedWidth(100)
        self.rotulos = []
        for i, (nome, campo) in enumerate([('Período', self.tipo), ('Ano', self.ano), ('Mês', self.mes), ('Semana (segunda a domingo)', self.semana)]):
            rotulo = texto(nome, 9, C['muted'])
            self.rotulos.append(rotulo)
            campo.setAccessibleName(nome)
            self.grade.addWidget(rotulo, 0, i)
            self.grade.addWidget(campo, 1, i)
        self.fixo = fixo
        self.reconstruir(referencia)
        self.tipo.currentIndexChanged.connect(self.ajustar)
        self.ano.valueChanged.connect(lambda _: self.reconstruir())
        self.mes.currentIndexChanged.connect(lambda _: self.reconstruir())
        self.semana.currentIndexChanged.connect(lambda _: self.alterado.emit())

    def reconstruir(self, dia=None):
        anterior = self.semana.currentData()
        with Q.QSignalBlocker(self.semana):
            self.semana.clear()
            for inicio, fim in semanas_do_mes(self.ano.value(), self.mes.currentIndex() + 1):
                self.semana.addItem(f'{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}', inicio)
            procura = dia - timedelta(days=dia.weekday()) if dia else anterior
            # QVariant não compara datetime.date por valor em todos os backends.
            indice = next((i for i in range(self.semana.count()) if self.semana.itemData(i) == procura), 0)
            self.semana.setCurrentIndex(max(0, indice))
        self.ajustar()

    def ajustar(self):
        tipo = self.tipo.currentText()
        for i, mostrar in [(0, not self.fixo), (1, True), (2, tipo != 'Ano'), (3, tipo == 'Semana')]:
            self.rotulos[i].setVisible(mostrar)
            [self.tipo, self.ano, self.mes, self.semana][i].setVisible(mostrar)
        self.organizar()
        self.alterado.emit()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self.organizar()

    def organizar(self):
        campos = [self.tipo, self.ano, self.mes, self.semana]
        visiveis = [(r, c) for r, c in zip(self.rotulos, campos) if not c.isHidden()]
        colunas = 2 if self.width() < 650 else 4
        for r, c in zip(self.rotulos, campos):
            self.grade.removeWidget(r)
            self.grade.removeWidget(c)
        for i, (r, c) in enumerate(visiveis):
            linha, coluna = divmod(i, colunas)
            self.grade.addWidget(r, linha * 2, coluna)
            self.grade.addWidget(c, linha * 2 + 1, coluna)

    def consulta(self):
        if not self.ano.hasAcceptableInput():
            raise ValueError('Informe um ano entre 1900 e 9998.')
        self.ano.interpretText()
        tipo = self.tipo.currentText()
        referencia = self.semana.currentData() if tipo == 'Semana' else date(self.ano.value(), 1 if tipo == 'Ano' else self.mes.currentIndex() + 1, 1)
        if referencia is None:
            raise ValueError('Selecione uma semana válida.')
        return ConsultaFinanceira(tipo, referencia)
