"""Revisão visual Noturno: dados fictícios, descartáveis e sem conexão externa."""

import argparse
import os
from pathlib import Path
import sys

if sys.platform != "win32":
    os.environ.setdefault("QT_FONT_DPI", "96")
from PySide6 import QtCore as Q, QtGui as G, QtWidgets as W, QtSvg
from estado_demo import Estado, HOJE, MESES, DIAS, agrupar, limites, dividir
from modelo import moeda, AJUDAS

R = Path(__file__).resolve().parent / "recursos"
C = dict(
    bg="#071525",
    side="#091B30",
    panel="#10243B",
    field="#142C47",
    border="#254362",
    text="#EAF2FF",
    muted="#A5BCD5",
    green="#00B889",
    turquoise="#2ED9BA",
    blue="#3B91FF",
    yellow="#F5B942",
    purple="#A477F5",
    red="#F05264",
)
FAMILIA = "Segoe UI"
ESTILO = """
QWidget { color:#EAF2FF; font-family:"FONTE"; font-size:10pt; }
QLabel, QScrollArea, QScrollArea>QWidget>QWidget { background:transparent; }
QScrollArea { border:0; }
QFrame[panel="true"] { background:#10243B; border:1px solid #254362; border-radius:12px; }
QPushButton { background:#142C47; border:1px solid #254362; border-radius:7px; padding:8px 12px; font-weight:600; }
QPushButton:hover { background:#1C3C59; border-color:#3B91FF; }
QPushButton:focus, QComboBox:focus, QTableWidget:focus { border:2px solid #2ED9BA; }
QPushButton[primary="true"] { background:#008D73; border-color:#00B889; }
QPushButton[primary="true"]:hover { background:#00A585; }
QPushButton[danger="true"] { background:#5F2535; border-color:#A33B50; }
QPushButton[danger="true"]:hover { background:#883347; }
QPushButton[nav="true"] { text-align:left; padding:13px 15px; background:transparent; border-color:transparent; font-size:11pt; }
QPushButton[active="true"] { background:#00564F; border-color:#008C79; }
QPushButton:disabled { color:#718DA9; background:#102035; border-color:#1D324A; }
QComboBox { background:#142C47; border:1px solid #254362; border-radius:6px; padding:7px 8px; min-height:18px; }
QComboBox QAbstractItemView { background:#142C47; selection-background-color:#00564F; }
QCheckBox { spacing:6px; background:transparent; }
QCheckBox::indicator { width:15px; height:15px; border:1px solid #718DA9; border-radius:3px; background:#142C47; }
QCheckBox::indicator:checked { background:#00B889; border:2px solid #2ED9BA; }
QTableWidget { background:#10243B; alternate-background-color:#172E48; border:1px solid #254362; border-radius:6px; gridline-color:#254362; selection-background-color:#00564F; }
QTableWidget::item { padding:5px; border:0; }
QHeaderView::section { background:#142C47; color:#A5BCD5; padding:8px 4px; border:0; font-weight:600; }
QScrollBar:vertical { background:#091B30; width:8px; margin:0; }
QScrollBar::handle:vertical { background:#365878; border-radius:4px; min-height:30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar:horizontal { background:#091B30; height:8px; }
QScrollBar::handle:horizontal { background:#365878; min-width:30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
QToolTip { color:#EAF2FF; background:#142C47; border:1px solid #254362; padding:9px; }
QMessageBox, QDialog { background:#091B30; }
"""


def texto(s, size=10, color=None, bold=False):
    w = W.QLabel(s)
    w.setStyleSheet(
        f'font-size:{size}pt;color:{color or C["text"]};font-weight:{600 if bold else 400};background:transparent;border:0;'
    )
    return w


def icone(nome, cor=None, size=20):
    data = (
        (R / "icones" / f"{nome}.svg")
        .read_text()
        .replace("currentColor", cor or C["text"])
    )
    pix = G.QPixmap(size * 2, size * 2)
    pix.fill(Q.Qt.GlobalColor.transparent)
    painter = G.QPainter(pix)
    QtSvg.QSvgRenderer(Q.QByteArray(data.encode())).render(painter)
    painter.end()
    pix.setDevicePixelRatio(2)
    return G.QIcon(pix)


def botao(s, acao, nome=None, primary=False, danger=False):
    b = W.QPushButton(s)
    if nome:
        b.setIcon(icone(nome))
    b.setIconSize(Q.QSize(19, 19))
    b.setProperty("primary", primary)
    b.setProperty("danger", danger)
    b.setCursor(Q.Qt.CursorShape.PointingHandCursor)
    if not s and nome:
        b.setAccessibleName({"settings": "Configurações"}.get(nome, nome))
    b.clicked.connect(acao)
    return b


def combo(itens, atual=None):
    w = W.QComboBox()
    w.addItems([str(x) for x in itens])
    w.setSizeAdjustPolicy(
        W.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    w.setMinimumContentsLength(4)
    if atual is not None:
        w.setCurrentText(str(atual))
    return w


def caixa(margem=14):
    w = W.QFrame()
    w.setProperty("panel", True)
    layout = W.QVBoxLayout(w)
    layout.setContentsMargins(margem, margem, margem, margem)
    layout.setSpacing(10)
    return w, layout


def ajuda(chave, mensagem=None):
    s = mensagem or AJUDAS.get(
        chave,
        "Indicador da consulta aplicada, incluindo dias registrados com zero. Totais não são limitados à página visível.",
    )
    b = botao("?", lambda: W.QMessageBox.information(b, "Como interpretar", s))
    b.setFixedSize(23, 23)
    b.setStyleSheet("padding:0;font-size:10pt;color:#A5BCD5;")
    b.setToolTip(s)
    b.setAccessibleName("Ajuda: " + chave)
    return b


class Fundo(W.QWidget):
    def __init__(self, lateral=False):
        super().__init__()
        self.lateral = lateral
        self.pix = G.QPixmap(
            str(R / ("fundo-lateral.png" if lateral else "fundo-superior.png"))
        )

    def paintEvent(self, event):
        p = G.QPainter(self)
        p.fillRect(self.rect(), G.QColor(C["side"] if self.lateral else C["bg"]))
        if self.lateral:
            target = self.rect()
        else:
            target = Q.QRect(0, 0, self.width(), min(240, self.height()))
        scaled = self.pix.scaled(
            target.size(),
            Q.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Q.Qt.TransformationMode.SmoothTransformation,
        )
        p.drawPixmap(
            target,
            scaled,
            Q.QRect(
                (scaled.width() - target.width()) // 2,
                0,
                target.width(),
                target.height(),
            ),
        )
        p.fillRect(target, G.QColor(7, 21, 37, 145 if self.lateral else 205))
        if self.lateral:
            grad = G.QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0, G.QColor(7, 21, 37, 230))
            grad.setColorAt(0.36, G.QColor(7, 21, 37, 170))
            grad.setColorAt(0.75, G.QColor(7, 21, 37, 40))
            grad.setColorAt(1, G.QColor(7, 21, 37, 230))
            p.fillRect(self.rect(), grad)
        p.end()


class Cartoes(W.QWidget):
    """Seis indicadores em uma linha ampla; duas linhas em janela menor."""

    def __init__(self):
        super().__init__()
        self.itens = []
        self.grade = W.QGridLayout(self)
        self.grade.setContentsMargins(0, 0, 0, 0)
        self.grade.setSpacing(10)
        self.colunas = 0

    def adicionar(self, w):
        self.itens.append(w)
        self.organizar(3)

    def organizar(self, n):
        self.colunas = n
        for w in self.itens:
            self.grade.removeWidget(w)
        for i, w in enumerate(self.itens):
            self.grade.addWidget(w, i // n, i % n)
        for i in range(6):
            self.grade.setColumnStretch(i, 1 if i < n else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        n = 6 if self.width() >= 1230 else 3
        if n != self.colunas:
            self.organizar(n)


class Seletor(W.QWidget):
    """Consulta demonstrativa adaptativa; a regra real por vigência não é importada."""

    alterado = Q.Signal()

    def __init__(self, todas=False, compacto=False, comparacao=False):
        super().__init__()
        tipos = (
            ["Dia", "Mês", "Fechamento", "Intervalo"]
            if comparacao
            else (
                ["Todas", "Fechamento", "Mês", "Ano"]
                if todas
                else ["Fechamento", "Mês", "Ano", "Semana"]
            )
        )
        self.tipo = combo(tipos, "Fechamento")
        self.ano = combo(range(2025, 2028), 2026)
        self.mes = combo(MESES, "Outubro")
        self.semana = combo([])
        self.grid = W.QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.campos = []
        for i, (nome, campo) in enumerate(
            [
                ("Período", self.tipo),
                ("Ano", self.ano),
                ("Mês", self.mes),
                ("Semana", self.semana),
            ]
        ):
            label = texto(nome, 9, C["muted"])
            row, col = (i * 2, 0) if compacto else (0, i)
            self.grid.addWidget(label, row, col)
            self.grid.addWidget(campo, row + 1, col)
            self.campos.append((label, campo))
        self.tipo.currentTextChanged.connect(self.atualizar)
        self.ano.currentTextChanged.connect(self.atualizar)
        self.mes.currentTextChanged.connect(self.atualizar)
        self.semana.currentIndexChanged.connect(lambda _: self.alterado.emit())
        self.inicio_data = W.QDateEdit(Q.QDate(2026, 10, 1))
        self.fim_data = W.QDateEdit(Q.QDate(2026, 10, 31))
        self.datas = []
        for i, (nome, campo) in enumerate(
            [("Data / início", self.inicio_data), ("Fim", self.fim_data)]
        ):
            campo.setDisplayFormat("dd/MM/yyyy")
            campo.setCalendarPopup(True)
            campo.setStyleSheet(
                "background:#142C47;border:1px solid #254362;border-radius:6px;padding:7px;"
            )
            titulo = texto(nome, 9, C["muted"])
            self.grid.addWidget(titulo, 2, i)
            self.grid.addWidget(campo, 3, i)
            self.datas.append((titulo, campo))
            campo.dateChanged.connect(lambda _: self.alterado.emit())
        self.atualizar()

    def atualizar(self):
        tipo = self.tipo.currentText()
        for i, (label, campo) in enumerate(self.campos):
            visible = (
                i == 0
                or i == 1
                and tipo in ("Ano", "Mês", "Fechamento", "Semana")
                or i == 2
                and tipo in ("Mês", "Fechamento", "Semana")
                or i == 3
                and tipo == "Semana"
            )
            label.setVisible(visible)
            campo.setVisible(visible)
        for i, (label, campo) in enumerate(self.datas):
            visible = tipo == "Intervalo" or tipo == "Dia" and i == 0
            label.setVisible(visible)
            campo.setVisible(visible)
        anterior = self.semana.currentIndex()
        self.semana.blockSignals(True)
        self.semana.clear()
        for n in range(6):
            a, b = limites(
                "Semana", int(self.ano.currentText()), self.mes.currentIndex() + 1, n
            )
            if (
                a.month != self.mes.currentIndex() + 1
                and b.month != self.mes.currentIndex() + 1
            ):
                continue
            self.semana.addItem(f"{a:%d/%m} a {b:%d/%m}", n)
        self.semana.setCurrentIndex(max(0, min(anterior, self.semana.count() - 1)))
        self.semana.blockSignals(False)
        self.alterado.emit()

    def intervalo(self):
        if self.tipo.currentText() in ("Dia", "Intervalo"):
            a = self.inicio_data.date().toPython()
            b = (
                self.fim_data.date().toPython()
                if self.tipo.currentText() == "Intervalo"
                else a
            )
            if b < a:
                raise ValueError(
                    "O fim do intervalo deve ser igual ou posterior ao início."
                )
            return a, b
        return limites(
            self.tipo.currentText(),
            int(self.ano.currentText()),
            self.mes.currentIndex() + 1,
            self.semana.currentData() or 0,
        )


class Tabela(W.QWidget):
    """Seleção limitada à página; totais e consulta permanecem fora da paginação."""

    excluir = Q.Signal(list)
    editar = Q.Signal(int)

    def __init__(self, colunas, descricao):
        super().__init__()
        self.linhas = []
        self.pagina = 0
        self.descricao = descricao
        self.v = W.QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(9)
        self.todos = W.QCheckBox("Selecionar página")
        self.todos.setToolTip(
            "Seleciona apenas os registros da página visível. A seleção é limpa ao mudar página ou consulta."
        )
        self.todos.toggled.connect(self.selecionar_pagina)
        self.v.addWidget(self.todos)
        self.table = W.QTableWidget(0, len(colunas) + 2)
        self.table.setHorizontalHeaderLabels([""] + colunas + ["Ações"])
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(39)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            W.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setMinimumHeight(265)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(W.QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(descricao + 1, W.QHeaderView.ResizeMode.Stretch)
        h.setMinimumSectionSize(35)
        self.table.setColumnWidth(0, 35)
        self.table.cellDoubleClicked.connect(
            lambda row, col: self.editar.emit(self.visiveis[row][0])
        )
        self.v.addWidget(self.table, 1)
        linha = W.QHBoxLayout()
        self.apagar = botao(
            "Excluir selecionados",
            lambda: self.excluir.emit(self.selecionados()),
            "trash-2",
            danger=True,
        )
        self.apagar.setEnabled(False)
        linha.addWidget(self.apagar)
        self.contagem = texto("", 9, C["muted"])
        linha.addWidget(self.contagem)
        linha.addStretch()
        self.tamanho = combo([5, 10, 25], 10)
        self.tamanho.setAccessibleName("Registros por página")
        self.tamanho.currentIndexChanged.connect(self.reiniciar)
        linha.addWidget(self.tamanho)
        self.voltar = botao("", lambda: self.mover(-1), "chevron-left")
        self.avancar = botao("", lambda: self.mover(1), "chevron-right")
        self.voltar.setAccessibleName("Página anterior")
        self.avancar.setAccessibleName("Próxima página")
        self.numero = texto("", 9)
        for b in (self.voltar, self.numero, self.avancar):
            linha.addWidget(b)
        self.v.addLayout(linha)
        self.checks = {}

    def preencher(self, linhas):
        self.linhas = linhas
        self.reiniciar()

    def reiniciar(self):
        self.pagina = 0
        self.renderizar()

    def mover(self, delta):
        self.pagina = max(0, min(self.paginas() - 1, self.pagina + delta))
        self.renderizar()

    def paginas(self):
        return max(
            1,
            (len(self.linhas) + int(self.tamanho.currentText()) - 1)
            // int(self.tamanho.currentText()),
        )

    def renderizar(self):
        self.todos.blockSignals(True)
        self.todos.setChecked(False)
        self.todos.blockSignals(False)
        self.checks = {}
        size = int(self.tamanho.currentText())
        self.visiveis = self.linhas[self.pagina * size : (self.pagina + 1) * size]
        self.table.setRowCount(len(self.visiveis))
        for row, (identificador, campos) in enumerate(self.visiveis):
            check = W.QCheckBox()
            check.setAccessibleName(f"Selecionar registro {identificador}")
            check.toggled.connect(self.atualizar_selecao)
            self.checks[identificador] = check
            container = W.QWidget()
            layout = W.QHBoxLayout(container)
            layout.setContentsMargins(9, 0, 0, 0)
            layout.addWidget(check)
            self.table.setCellWidget(row, 0, container)
            for col, val in enumerate(campos, 1):
                item = W.QTableWidgetItem(str(val))
                item.setToolTip(str(val))
                item.setTextAlignment(
                    Q.Qt.AlignmentFlag.AlignVCenter
                    | (
                        Q.Qt.AlignmentFlag.AlignRight
                        if str(val).startswith("R$")
                        else Q.Qt.AlignmentFlag.AlignLeft
                    )
                )
                if str(val).startswith("R$"):
                    item.setFont(G.QFont(FAMILIA, 10, G.QFont.Weight.DemiBold))
                self.table.setItem(row, col, item)
            acoes = W.QWidget()
            layout = W.QHBoxLayout(acoes)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(5)
            for nome, tip, action in [
                (
                    "pencil",
                    "Editar",
                    lambda checked=False, i=identificador: self.editar.emit(i),
                ),
                (
                    "trash-2",
                    "Excluir este registro",
                    lambda checked=False, i=identificador: self.excluir.emit([i]),
                ),
            ]:
                b = botao("", action, nome, danger=nome == "trash-2")
                b.setFixedSize(30, 30)
                b.setStyleSheet("padding:3px;")
                b.setToolTip(tip)
                b.setAccessibleName(f"{tip} {identificador}")
                layout.addWidget(b)
            self.table.setCellWidget(row, self.table.columnCount() - 1, acoes)
        self.table.setColumnWidth(self.table.columnCount() - 1, 80)
        self.numero.setText(f"{self.pagina+1} / {self.paginas()}")
        self.voltar.setEnabled(self.pagina > 0)
        self.avancar.setEnabled(self.pagina + 1 < self.paginas())
        self.todos.setEnabled(bool(self.visiveis))
        self.atualizar_selecao()
        self.table.setAccessibleDescription(
            "Nenhum registro neste período."
            if not self.linhas
            else f"{len(self.linhas)} registros na consulta, seleção por página."
        )

    def selecionados(self):
        return [i for i, c in self.checks.items() if c.isChecked()]

    def selecionar_pagina(self, checked):
        for c in self.checks.values():
            c.setChecked(checked)
        self.atualizar_selecao()

    def atualizar_selecao(self):
        n = len(self.selecionados())
        self.apagar.setEnabled(n > 0)
        self.contagem.setText(
            f"{n} selecionado(s) · {len(self.linhas)} na consulta"
            if self.linhas
            else "Nenhum registro neste período"
        )
        self.todos.blockSignals(True)
        self.todos.setChecked(bool(self.checks) and n == len(self.checks))
        self.todos.blockSignals(False)


class Grafico(W.QWidget):
    def __init__(self, modo="barras"):
        super().__init__()
        self.modo = modo
        self.dados = []
        self.setMinimumHeight(155)
        self.setAccessibleName(
            "Gráfico; valores disponíveis também nas tabelas e legendas"
        )

    def paintEvent(self, e):
        p = G.QPainter(self)
        p.setRenderHint(G.QPainter.RenderHint.Antialiasing)
        p.setFont(G.QFont(FAMILIA, 9))
        if self.modo == "barras":
            base = self.height() - 32
            width = max(40, self.width() - 48)
            maximum = max([v for _, v in self.dados] + [1])
            for n in range(4):
                y = base - (base - 25) * n / 3
                p.setPen(G.QColor(C["border"]))
                p.drawLine(38, int(y), self.width() - 5, int(y))
            for i, (s, val) in enumerate(self.dados):
                step = width / max(len(self.dados), 1)
                x = 42 + i * step
                h = (base - 32) * val / maximum
                p.setPen(Q.Qt.PenStyle.NoPen)
                p.setBrush(G.QColor(C["blue"]))
                p.drawRoundedRect(
                    Q.QRectF(x, base - max(2, h), step * 0.65, max(2, h)), 4, 4
                )
                p.setPen(G.QColor(C["text"]))
                p.drawText(
                    Q.QRectF(x - 8, base - h - 22, step * 0.9, 20),
                    Q.Qt.AlignmentFlag.AlignCenter,
                    moeda(val),
                )
                p.setPen(G.QColor(C["muted"]))
                p.drawText(
                    Q.QRectF(x - 8, base + 6, step * 0.9, 22),
                    Q.Qt.AlignmentFlag.AlignCenter,
                    s,
                )
        else:
            total = sum(v for _, v in self.dados)
            box = Q.QRectF(
                8, 15, min(135, self.width() * 0.42), min(135, self.width() * 0.42)
            )
            start = 90 * 16
            for i, (s, v) in enumerate(self.dados):
                angle = round(360 * 16 * v / total) if total else 0
                pen = G.QPen(G.QColor([C["yellow"], C["purple"], C["blue"]][i]), 18)
                p.setPen(pen)
                p.drawArc(box.adjusted(10, 10, -10, -10), start, -angle)
                start -= angle
                p.setPen(G.QColor(C["text"]))
                p.drawText(
                    int(box.right() + 16),
                    40 + i * 39,
                    f"{s}  {v/total*100:.1f}%".replace(".", ",") if total else s + " —",
                )
                p.setPen(G.QColor(C["muted"]))
                p.drawText(int(box.right() + 16), 57 + i * 39, moeda(v))
            if not total:
                p.setPen(G.QColor(C["muted"]))
                p.drawText(box, Q.Qt.AlignmentFlag.AlignCenter, "Sem vendas")
        p.end()


class Aplicativo(W.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestão da Feira — revisão Noturno (dados fictícios)")
        self.resize(1536, 1024)
        self.setMinimumSize(1000, 700)
        self.estado = Estado()
        self.intervalo_vendas = limites("Fechamento")
        self.consulta_vendas = ("Fechamento", 2026, 10)
        self.dias = set(range(7))
        self.intervalo_financas = limites("Fechamento")
        self.area = ""
        self.nav = {}
        root = W.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        side = Fundo(True)
        side.setFixedWidth(210)
        sl = W.QVBoxLayout(side)
        sl.setContentsMargins(14, 22, 14, 18)
        marca = W.QHBoxLayout()
        logo = W.QLabel()
        renderer = QtSvg.QSvgRenderer(str(R / "logo.svg"))
        pix = G.QPixmap(90, 90)
        pix.fill(Q.Qt.GlobalColor.transparent)
        painter = G.QPainter(pix)
        renderer.render(painter)
        painter.end()
        logo.setPixmap(
            pix.scaled(
                42,
                42,
                Q.Qt.AspectRatioMode.KeepAspectRatio,
                Q.Qt.TransformationMode.SmoothTransformation,
            )
        )
        marca.addWidget(logo)
        nomes = W.QVBoxLayout()
        nomes.setSpacing(3)
        nomes.addWidget(texto("Gestão da Feira", 12, bold=True))
        nomes.addWidget(texto("Suas feiras, seus resultados.", 7, C["muted"]))
        marca.addLayout(nomes)
        sl.addLayout(marca)
        sl.addSpacing(28)
        for nome, ico in [
            ("Vendas", "chart-no-axes-combined"),
            ("Análises", "trending-up"),
            ("Finanças", "wallet"),
        ]:
            b = botao(nome, lambda checked=False, n=nome: self.mostrar(n), ico)
            b.setProperty("nav", True)
            sl.addWidget(b)
            self.nav[nome] = b
        sl.addStretch()
        sl.addWidget(
            botao("Configurações", lambda: self.aviso("Configurações"), "settings")
        )
        sl.addWidget(texto("Tema: Noturno", 10, C["muted"]))
        sl.addWidget(texto("ESTUDO VISUAL · SEM CONEXÃO", 8, C["muted"]))
        root.addWidget(side)
        main = Fundo()
        ml = W.QVBoxLayout(main)
        ml.setContentsMargins(20, 18, 20, 10)
        ml.setSpacing(14)
        header = W.QHBoxLayout()
        title = W.QVBoxLayout()
        self.titulo = texto("", 25, bold=True)
        self.subtitulo = texto("", 10, C["muted"])
        title.addWidget(self.titulo)
        title.addWidget(self.subtitulo)
        header.addLayout(title)
        header.addStretch()
        header.addWidget(botao("", lambda: self.aviso("Configurações"), "settings"))
        header.addWidget(botao("Noturno", lambda: self.aviso("Temas"), "moon"))
        header.addWidget(
            botao(
                "Exportar relatório",
                lambda: self.aviso("Exportar CSV / Excel da consulta de Vendas"),
                "download",
            )
        )
        self.novo = botao(
            "Nova venda",
            lambda: self.aviso(
                "Nova despesa" if self.area == "Finanças" else "Nova venda"
            ),
            "plus",
            True,
        )
        header.addWidget(self.novo)
        ml.addLayout(header)
        self.scroll = W.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Q.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        ml.addWidget(self.scroll, 1)
        self.status = texto(
            "Demo isolada · relógio fixo: 26/10/2026 · nenhuma conexão com banco, Drive ou nuvem",
            8,
            C["muted"],
        )
        ml.addWidget(self.status)
        root.addWidget(main, 1)
        self.paginas = {}
        self.mostrar("Vendas")

    def aviso(self, nome):
        W.QMessageBox.information(
            self,
            nome,
            "Prévia visual. Este formulário ainda não está conectado à lógica do aplicativo. Nenhum dado real será acessado ou alterado.",
        )

    def detalhes(self, nome, linhas):
        d = W.QDialog(self)
        d.setWindowTitle(nome)
        d.resize(760, 480)
        l = W.QVBoxLayout(d)
        l.addWidget(texto(nome, 18, bold=True))
        area = W.QTextBrowser()
        area.setPlainText("\n\n".join(linhas))
        area.setStyleSheet("background:#10243B;border:1px solid #254362;padding:15px;")
        l.addWidget(area)
        l.addWidget(botao("Fechar", d.accept))
        d.exec()

    def mostrar(self, nome):
        if self.area == nome:
            return
        if self.area:
            self.paginas[self.area]["rolagem"] = self.scroll.verticalScrollBar().value()
        atual = self.scroll.takeWidget()
        if atual:
            atual.setParent(self)
            atual.hide()
        if nome not in self.paginas:
            body = W.QWidget()
            layout = W.QVBoxLayout(body)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            self.paginas[nome] = {"widget": body, "layout": layout, "rolagem": 0}
            {
                "Vendas": self.construir_vendas,
                "Análises": self.construir_analises,
                "Finanças": self.construir_financas,
            }[nome](layout)
        self.area = nome
        self.scroll.setWidget(self.paginas[nome]["widget"])
        self.paginas[nome]["widget"].show()
        self.scroll.verticalScrollBar().setValue(self.paginas[nome]["rolagem"])
        for n, b in self.nav.items():
            b.setProperty("active", n == nome)
            b.style().unpolish(b)
            b.style().polish(b)
        self.titulo.setText(nome)
        self.subtitulo.setText(
            {
                "Vendas": "Registre, consulte e gerencie as vendas da feira.",
                "Análises": "Entenda seus resultados por semana e compare períodos.",
                "Finanças": "Controle suas despesas, taxas e compromissos do período.",
            }[nome]
        )
        self.novo.setText("Nova despesa" if nome == "Finanças" else "Nova venda")

    def cartao(self, titulo, valor, ico, cor, nota=None, chave=None):
        w, l = caixa(12)
        base = G.QColor(C["panel"])
        accent = G.QColor(cor)
        tint = G.QColor(
            *[
                round(base.getRgb()[i] * 0.88 + accent.getRgb()[i] * 0.12)
                for i in range(3)
            ]
        ).name()
        w.setStyleSheet(
            f'QFrame[panel="true"]{{border:1px solid {cor};background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {tint},stop:1 #10243B);border-radius:12px;}}'
        )
        h = W.QHBoxLayout()
        i = W.QLabel()
        i.setPixmap(icone(ico, cor, 21).pixmap(21, 21))
        h.addWidget(i)
        h.addWidget(texto(titulo, 9, C["muted"]))
        h.addStretch()
        if chave:
            h.addWidget(ajuda(chave))
        l.addLayout(h)
        value = texto(valor, 22, cor, True)
        l.addWidget(value)
        if nota:
            l.addWidget(texto(nota, 9, C["muted"]))
        return w, value

    def construir_vendas(self, l):
        cards = Cartoes()
        self.cards = []
        for title, ico, color in [
            ("TOTAL DO PERÍODO", "trending-up", C["turquoise"]),
            ("DIAS DE FEIRA", "calendar-days", C["blue"]),
            ("MÉDIA POR DIA", "banknote", C["turquoise"]),
            ("DINHEIRO", "banknote", C["yellow"]),
            ("PIX", "gem", C["purple"]),
            ("CARTÃO", "credit-card", C["blue"]),
        ]:
            w, value = self.cartao(title, "", ico, color, chave="Indicador", nota=None)
            # Ajuda comum específica dos indicadores de Vendas.
            for b in w.findChildren(W.QPushButton):
                b.setToolTip(
                    "Indicador calculado sobre todas as vendas da consulta aplicada, incluindo dias registrados com zero. Não é limitado à página visível."
                )
            cards.adicionar(w)
            self.cards.append(value)
        l.addWidget(cards)
        semana, sl = caixa()
        sl.setContentsMargins(18, 12, 18, 12)
        linha = W.QHBoxLayout()
        esquerda = W.QVBoxLayout()
        esquerda.addWidget(texto("Semana atual", 15, C["turquoise"], True))
        self.semana_texto = texto("", 10, C["muted"])
        esquerda.addWidget(self.semana_texto)
        self.semana_valor = texto("", 24, bold=True)
        esquerda.addWidget(self.semana_valor)
        linha.addLayout(esquerda, 1)
        self.semana_formas = texto("", 10, C["muted"])
        linha.addWidget(self.semana_formas, 1)
        linha.addWidget(
            botao("Ver detalhes da semana", self.detalhar_semana, "arrow-up-right")
        )
        linha.addWidget(
            ajuda(
                "Semana atual",
                "De segunda-feira até hoje (relógio fixo da demo: 26/10/2026), sem registros futuros e independente dos filtros do histórico.",
            )
        )
        sl.addLayout(linha)
        l.addWidget(semana)
        faixa, fl = caixa(12)
        linha = W.QHBoxLayout()
        self.anterior = texto("", 10, C["muted"])
        self.anterior.setWordWrap(True)
        linha.addWidget(self.anterior, 1)
        linha.addWidget(
            botao(
                "Participação e comparação",
                lambda: self.detalhes(
                    "Indicadores da seleção", [self.anterior.text(), self.participacao]
                ),
                "chart-pie",
            )
        )
        fl.addLayout(linha)
        l.addWidget(faixa)
        baixo = W.QHBoxLayout()
        baixo.setSpacing(12)
        hist, hl = caixa()
        header = W.QHBoxLayout()
        header.addWidget(texto("Histórico de vendas", 15, bold=True))
        header.addStretch()
        self.total_vendas = texto("", 10, C["muted"])
        header.addWidget(self.total_vendas)
        hl.addLayout(header)
        self.tabela_vendas = Tabela(
            ["ID", "Data", "Dia da semana", "Dinheiro", "Pix", "Cartão", "Total"], 2
        )
        header_vendas = self.tabela_vendas.table.horizontalHeader()
        for i in (3, 4, 5, 6, 7):
            header_vendas.setSectionResizeMode(i, W.QHeaderView.ResizeMode.Stretch)
        self.tabela_vendas.editar.connect(lambda i: self.aviso(f"Editar venda {i}"))
        self.tabela_vendas.excluir.connect(
            lambda ids: self.confirmar_exclusao("Vendas", ids)
        )
        hl.addWidget(self.tabela_vendas, 1)
        baixo.addWidget(hist, 1)
        filtro, ff = caixa(12)
        filtro.setFixedWidth(230)
        ff.setSpacing(6)
        ff.addWidget(texto("Filtros do histórico", 12, bold=True))
        self.seletor_vendas = Seletor(True, True)
        ff.addWidget(self.seletor_vendas)
        ff.addWidget(texto("Dias da semana", 10, C["muted"]))
        grade = W.QGridLayout()
        self.dias_checks = []
        for i, s in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
            c = W.QCheckBox(s)
            c.setChecked(True)
            c.toggled.connect(self.pendente_vendas)
            grade.addWidget(c, i // 3, i % 3)
            self.dias_checks.append(c)
        ff.addLayout(grade)
        self.pendente = texto("", 9, C["yellow"])
        self.pendente.setWordWrap(True)
        self.pendente.hide()
        ff.addWidget(self.pendente)
        ff.addWidget(botao("Aplicar filtros", self.aplicar_vendas, "filter", True))
        ff.addWidget(botao("Limpar filtros", self.limpar_vendas, "rotate-ccw"))
        self.aplicado = texto("", 9, C["muted"])
        self.aplicado.setWordWrap(True)
        ff.addWidget(self.aplicado)
        ff.addStretch()
        baixo.addWidget(filtro, 0, Q.Qt.AlignmentFlag.AlignTop)
        l.addLayout(baixo, 1)
        self.seletor_vendas.alterado.connect(self.pendente_vendas)
        self.atualizar_vendas()

    def pendente_vendas(self):
        self.pendente.setText("Há alterações ainda não aplicadas.")
        self.pendente.show()

    def aplicar_vendas(self):
        self.intervalo_vendas = self.seletor_vendas.intervalo()
        self.consulta_vendas = (
            self.seletor_vendas.tipo.currentText(),
            int(self.seletor_vendas.ano.currentText()),
            self.seletor_vendas.mes.currentIndex() + 1,
        )
        self.dias = {i for i, c in enumerate(self.dias_checks) if c.isChecked()}
        self.atualizar_vendas()
        self.pendente.setText("")
        self.pendente.hide()
        if "Análises" in self.paginas:
            self.atualizar_analises()

    def limpar_vendas(self):
        self.seletor_vendas.tipo.setCurrentText("Todas")
        for c in self.dias_checks:
            c.setChecked(True)
        self.aplicar_vendas()

    def atualizar_vendas(self):
        from datetime import timedelta

        rows = self.estado.consultar_vendas(self.intervalo_vendas, self.dias)
        pagamentos = [
            sum(getattr(r, k) for r in rows) for k in ("dinheiro", "pix", "cartao")
        ]
        total = sum(pagamentos)
        for w, v in zip(
            self.cards,
            [
                moeda(total),
                str(len(rows)),
                moeda(dividir(total, len(rows))),
                *(moeda(x) for x in pagamentos),
            ],
        ):
            w.setText(v)
        self.total_vendas.setText(f"{len(rows)} registros · {moeda(total)}")
        self.participacao = " · ".join(
            f"{s}: {v/total*100:.1f}%".replace(".", ",") if total else s + ": —"
            for s, v in zip(["Dinheiro", "Pix", "Cartão"], pagamentos)
        )
        a, b = self.intervalo_vendas
        desc = "Todas as vendas" if a.year == 1 else f"{a:%d/%m/%Y} a {b:%d/%m/%Y}"
        self.aplicado.setText(
            "Consulta aplicada\n"
            + desc
            + "\n"
            + f"{len(self.dias)} dias da semana selecionados"
        )
        if a.year > 1:
            duracao = b - a + timedelta(days=1)
            tipo, ano, mes = self.consulta_vendas
            if tipo in ("Fechamento", "Mês"):
                anterior = limites(tipo, ano - (mes == 1), 12 if mes == 1 else mes - 1)
            elif tipo == "Ano":
                anterior = limites("Ano", ano - 1, 1)
            else:
                anterior = (a - duracao, a - timedelta(days=1))
            anteriores = self.estado.consultar_vendas(anterior, self.dias)
            antes = sum(r.total for r in anteriores)
            self.anterior.setText(
                f"Período anterior: {moeda(antes)}   ·   Diferença: {moeda(total-antes)}\n"
                + self.participacao
            )
        else:
            self.anterior.setText(
                "Selecione um período para comparar com o anterior.\n"
                + self.participacao
            )
        self.tabela_vendas.preencher(
            [
                (
                    r.id,
                    [
                        r.id,
                        r.data.strftime("%d/%m/%Y"),
                        DIAS[r.data.weekday()],
                        moeda(r.dinheiro),
                        moeda(r.pix),
                        moeda(r.cartao),
                        moeda(r.total),
                    ],
                )
                for r in rows
            ]
        )
        segunda = HOJE - timedelta(days=HOJE.weekday())
        semana = self.estado.consultar_vendas((segunda, HOJE))
        self.semana_texto.setText(
            f"{segunda:%d/%m/%Y} até {HOJE:%d/%m/%Y} · {len(semana)} dias de feira"
        )
        self.semana_valor.setText(moeda(sum(r.total for r in semana)))
        self.semana_formas.setText(
            "Por forma de pagamento\n"
            + "\n".join(
                s + "   " + moeda(sum(getattr(r, k) for r in semana))
                for s, k in [
                    ("Dinheiro", "dinheiro"),
                    ("Pix", "pix"),
                    ("Cartão", "cartao"),
                ]
            )
        )

    def detalhar_semana(self):
        from datetime import timedelta

        rows = self.estado.consultar_vendas(
            (HOJE - timedelta(days=HOJE.weekday()), HOJE)
        )
        self.detalhes(
            "Semana atual — independente dos filtros",
            [f"{r.data:%d/%m/%Y} · {moeda(r.total)}" for r in rows]
            or ["Nenhuma venda registrada até hoje nesta semana fictícia."],
        )

    def construir_financas(self, l):
        filtro, fl = caixa(12)
        h = W.QHBoxLayout()
        self.seletor_financas = Seletor()
        h.addWidget(self.seletor_financas, 1)
        h.addWidget(botao("Consultar", self.aplicar_financas, "search", True))
        h.addWidget(botao("Limpar", self.limpar_financas, "rotate-ccw"))
        fl.addLayout(h)
        self.fin_intervalo = texto("", 9, C["muted"])
        fl.addWidget(self.fin_intervalo)
        self.fin_pendente = texto("", 9, C["yellow"])
        self.fin_pendente.hide()
        fl.addWidget(self.fin_pendente)
        self.seletor_financas.alterado.connect(self.pendente_financas)
        l.addWidget(filtro)
        cards = W.QHBoxLayout()
        self.fin_cards = {}
        for key, title, ico, color, note in [
            (
                "saldo",
                "Saldo após despesas",
                "wallet",
                C["turquoise"],
                "Vendas − taxas − despesas",
            ),
            (
                "despesas",
                "Despesas a cobrir",
                "receipt",
                C["red"],
                "Compromissos incluídos na consulta",
            ),
            (
                "falta",
                "Falta cobrir",
                "banknote",
                C["blue"],
                "Despesas ainda não cobertas",
            ),
        ]:
            w, v = self.cartao(
                title, "", ico, color, note, {"despesas": "meta"}.get(key, key)
            )
            cards.addWidget(w, 1)
            self.fin_cards[key] = v
        l.addLayout(cards)
        secundario, sl = caixa(12)
        sh = W.QHBoxLayout()
        self.fin_secundarios = {}
        for key, title in [
            ("bruto", "Vendas brutas"),
            ("taxas", "Taxas cadastradas"),
            ("liquido", "Vendas menos taxas"),
        ]:
            col = W.QVBoxLayout()
            col.addWidget(texto(title, 9, C["muted"]))
            v = texto("", 15, bold=True)
            col.addWidget(v)
            sh.addLayout(col, 1)
            self.fin_secundarios[key] = v
        sh.addWidget(ajuda("taxas"))
        sl.addLayout(sh)
        l.addWidget(secundario)
        lista, ll = caixa()
        h = W.QHBoxLayout()
        h.addWidget(texto("Lançamentos do período", 15, bold=True))
        h.addStretch()
        h.addWidget(
            botao(
                "Taxas da maquininha",
                lambda: self.aviso("Taxas da maquininha"),
                "percent",
            )
        )
        h.addWidget(
            botao("Nova despesa", lambda: self.aviso("Nova despesa"), "plus", True)
        )
        ll.addLayout(h)
        self.fin_recorte = combo(
            ["Todos os lançamentos", "Despesas", "Taxas", "Parcelas"]
        )
        self.fin_recorte.setMinimumWidth(200)
        self.fin_recorte.currentIndexChanged.connect(self.atualizar_financas)
        tipo = W.QHBoxLayout()
        tipo.addWidget(self.fin_recorte)
        tipo.addWidget(
            texto(
                "Totais acima: período completo, independente desta lista.",
                9,
                C["muted"],
            )
        )
        tipo.addStretch()
        ll.addLayout(tipo)
        self.tabela_financas = Tabela(
            [
                "Compra",
                "Fatura / pagamento",
                "Descrição / compra",
                "Meio",
                "Categoria",
                "Parcela",
                "Valor",
            ],
            2,
        )
        self.tabela_financas.excluir.connect(
            lambda ids: self.confirmar_exclusao("Finanças", ids)
        )
        self.tabela_financas.editar.connect(
            lambda i: self.aviso(f"Editar compra inteira — lançamento {i}")
        )
        ll.addWidget(self.tabela_financas, 1)
        ll.addWidget(
            texto(
                "Editar abre a compra inteira. Excluir remove somente os lançamentos escolhidos.",
                9,
                C["muted"],
            )
        )
        l.addWidget(lista, 1)
        links = W.QHBoxLayout()
        for nome, ico, acao in [
            ("Despesas por semana", "calendar-days", self.despesas_semanas),
            (
                "Histórico de taxas",
                "percent",
                lambda: self.detalhes(
                    "Histórico de taxas",
                    [
                        "Exemplo visual de acesso aos ajustes anuais confirmados ou estimados.",
                        "Cadastro e cobertura histórica ainda não conectados nesta demo.",
                    ],
                ),
            ),
            (
                "Regra de fechamento",
                "receipt",
                lambda: self.detalhes(
                    "Fechamento da demonstração",
                    [
                        "Regra fixa fictícia: Outubro = 10/10 a 09/11.",
                        "O programa real mantém regras por vigência. Essa configuração não está conectada à demo.",
                    ],
                ),
            ),
        ]:
            links.addWidget(botao(nome, acao, ico), 1)
        l.addLayout(links)
        self.atualizar_financas()

    def pendente_financas(self):
        self.fin_pendente.setText("Há alterações ainda não consultadas.")
        self.fin_pendente.show()

    def aplicar_financas(self):
        self.intervalo_financas = self.seletor_financas.intervalo()
        self.atualizar_financas()
        self.fin_pendente.hide()

    def limpar_financas(self):
        self.seletor_financas.tipo.setCurrentText("Fechamento")
        self.seletor_financas.ano.setCurrentText("2026")
        self.seletor_financas.mes.setCurrentIndex(9)
        self.fin_recorte.setCurrentIndex(0)
        self.aplicar_financas()

    def atualizar_financas(self):
        resumo = self.estado.resumo(self.intervalo_financas)
        for key, v in {**self.fin_cards, **self.fin_secundarios}.items():
            v.setText(moeda(resumo[key]))
            if key == "saldo":
                v.setStyleSheet(
                    f'font-size:22pt;font-weight:600;color:{C["red"] if resumo[key]<0 else C["turquoise"]};background:transparent;border:0;'
                )
        a, b = self.intervalo_financas
        self.fin_intervalo.setText(
            f"Consulta financeira independente: {a:%d/%m/%Y} a {b:%d/%m/%Y} · Faturas futuras no período estão incluídas."
        )
        rows = self.estado.consultar_financas(self.intervalo_financas)
        tipo = self.fin_recorte.currentIndex()
        rows = [
            r
            for r in rows
            if tipo == 0
            or tipo == 1
            and not r.taxa
            or tipo == 2
            and r.taxa
            or tipo == 3
            and "/" in r.parcela
        ]
        self.tabela_financas.preencher(
            [
                (
                    r.id,
                    [
                        r.compra.strftime("%d/%m/%Y") if r.compra else "—",
                        r.data.strftime("%d/%m/%Y"),
                        r.descricao,
                        r.meio,
                        r.categoria,
                        r.parcela,
                        moeda(r.valor),
                    ],
                )
                for r in rows
            ]
        )

    def despesas_semanas(self):
        from datetime import timedelta

        grupos = {}
        for r in self.estado.consultar_financas(self.intervalo_financas):
            if not r.taxa:
                segunda = r.data - timedelta(days=r.data.weekday())
                grupos[segunda] = grupos.get(segunda, 0) + r.valor
        self.detalhes(
            "Despesas por semana",
            [
                f"{d:%d/%m} a {d+timedelta(days=6):%d/%m}: {moeda(v)}"
                for d, v in sorted(grupos.items(), reverse=True)
            ]
            or ["Sem despesas no período."],
        )

    def construir_analises(self, l):
        topo = W.QHBoxLayout()
        self.ana_intervalo = texto("", 10, C["muted"])
        topo.addWidget(self.ana_intervalo, 1)
        topo.addWidget(
            botao("Alterar filtros em Vendas", lambda: self.mostrar("Vendas"), "filter")
        )
        l.addLayout(topo)
        graficos = W.QHBoxLayout()
        barras, bl = caixa()
        bl.addWidget(texto("Resultado por semana", 14, bold=True))
        self.barras = Grafico()
        bl.addWidget(self.barras, 1)
        graficos.addWidget(barras, 5)
        resumo, rl = caixa()
        rl.addWidget(texto("Resumo da seleção", 12, bold=True))
        self.ana_resumo = texto("", 12)
        rl.addWidget(self.ana_resumo)
        rl.addStretch()
        graficos.addWidget(resumo, 2)
        pizza, pl = caixa()
        pl.addWidget(texto("Participação por pagamento", 12, bold=True))
        self.pizza = Grafico("pizza")
        pl.addWidget(self.pizza, 1)
        graficos.addWidget(pizza, 4)
        l.addLayout(graficos)
        table, tl = caixa()
        tl.addWidget(texto("Detalhamento por semana", 14, bold=True))
        self.ana_tabela = W.QTableWidget(0, 8)
        self.ana_tabela.setHorizontalHeaderLabels(
            [
                "Início / fim",
                "Dias",
                "Total",
                "Média/dia",
                "Dinheiro",
                "Pix",
                "Cartão",
                "Recorte",
            ]
        )
        self.ana_tabela.verticalHeader().hide()
        self.ana_tabela.setMinimumHeight(205)
        self.ana_tabela.setAlternatingRowColors(True)
        self.ana_tabela.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ana_tabela.horizontalHeader().setSectionResizeMode(
            W.QHeaderView.ResizeMode.Stretch
        )
        self.ana_tabela.horizontalHeader().setSectionResizeMode(
            0, W.QHeaderView.ResizeMode.ResizeToContents
        )
        tl.addWidget(self.ana_tabela)
        l.addWidget(table)
        baixo = W.QHBoxLayout()
        comp, cl = caixa()
        cl.addWidget(texto("Comparar períodos (A e B)", 14, bold=True))
        cl.addWidget(
            texto("Consulta independente dos filtros de Vendas.", 9, C["muted"])
        )
        campos = W.QHBoxLayout()
        self.a = Seletor(comparacao=True)
        self.b = Seletor(comparacao=True)
        self.a.tipo.setCurrentText("Mês")
        self.b.tipo.setCurrentText("Mês")
        self.b.mes.setCurrentIndex(8)
        for nome, c in [("Período A", self.a), ("Período B", self.b)]:
            col = W.QVBoxLayout()
            col.addWidget(texto(nome, 10, C["turquoise"], True))
            col.addWidget(c)
            campos.addLayout(col, 1)
        cl.addLayout(campos)
        cl.addWidget(
            botao("Comparar períodos", self.comparar, "arrow-right-left", True)
        )
        self.ana_comparacao = texto("", 10)
        self.ana_comparacao.setWordWrap(True)
        cl.addWidget(self.ana_comparacao)
        baixo.addWidget(comp, 4)
        det, dl = caixa()
        dl.addWidget(texto("Detalhes do período", 14, bold=True))
        dl.addWidget(texto("Mesma seleção aplicada em Vendas.", 9, C["muted"]))
        for nome, ico, acao in [
            ("Resultados por dia da semana", "calendar-days", self.detalhes_dias),
            ("Evolução mensal / fechamento", "trending-up", self.detalhes_evolucao),
            (
                "Formas de pagamento",
                "chart-pie",
                lambda: self.detalhes("Formas de pagamento", [self.participacao]),
            ),
            ("Lista de vendas da seleção", "list", self.detalhes_vendas),
        ]:
            dl.addWidget(botao(nome, acao, ico))
        dl.addStretch()
        baixo.addWidget(det, 3)
        l.addLayout(baixo)
        self.atualizar_analises()
        self.comparar()

    def atualizar_analises(self):
        from datetime import timedelta

        rows = self.estado.consultar_vendas(self.intervalo_vendas, self.dias)
        grupos = agrupar(rows)
        a, b = self.intervalo_vendas
        self.ana_intervalo.setText(
            "Seleção aplicada em Vendas: "
            + ("todas" if a.year == 1 else f"{a:%d/%m/%Y} a {b:%d/%m/%Y}")
        )
        total = sum(r.total for r in rows)
        self.ana_resumo.setText(
            f"Total do período\n{moeda(total)}\n\nSemanas: {len(grupos)}\nDias de feira: {len(rows)}\n\nMédia por dia\n{moeda(dividir(total,len(rows)))}"
        )
        self.barras.dados = [
            (d.strftime("%d/%m"), sum(r.total for r in rs))
            for d, rs in reversed(grupos)
        ]
        self.barras.update()
        self.pizza.dados = [
            (nome, sum(getattr(r, key) for r in rows))
            for nome, key in [
                ("Dinheiro", "dinheiro"),
                ("Pix", "pix"),
                ("Cartão", "cartao"),
            ]
        ]
        self.pizza.update()
        self.ana_tabela.setRowCount(len(grupos))
        for n, (d, rs) in enumerate(grupos):
            total = sum(r.total for r in rs)
            parcial = d < a or d + timedelta(days=6) > b
            vals = [
                f"{d:%d/%m} — {d+timedelta(days=6):%d/%m}",
                len(rs),
                moeda(total),
                moeda(dividir(total, len(rs))),
                *(
                    moeda(sum(getattr(r, key) for r in rs))
                    for key in ("dinheiro", "pix", "cartao")
                ),
                "Parcial" if parcial else "Completa",
            ]
            for col, val in enumerate(vals):
                self.ana_tabela.setItem(n, col, W.QTableWidgetItem(str(val)))

    def comparar(self):
        try:
            ia, ib = self.a.intervalo(), self.b.intervalo()
        except ValueError as exc:
            W.QMessageBox.warning(self, "Confira o intervalo", str(exc))
            return
        va = sum(r.total for r in self.estado.consultar_vendas(ia))
        vb = sum(r.total for r in self.estado.consultar_vendas(ib))
        self.ana_comparacao.setText(
            f"A: {moeda(va)}   |   B: {moeda(vb)}\nDiferença A − B: {moeda(va-vb)}"
        )

    def detalhes_dias(self):
        rows = self.estado.consultar_vendas(self.intervalo_vendas, self.dias)
        self.detalhes(
            "Resultados por dia da semana",
            [
                f"{s}: {moeda(sum(r.total for r in rows if r.data.weekday()==i))} · {sum(r.data.weekday()==i for r in rows)} dias registrados"
                for i, s in enumerate(DIAS)
            ],
        )

    def detalhes_evolucao(self):
        from datetime import timedelta

        modo, ok = W.QInputDialog.getItem(
            self, "Evolução da seleção", "Agrupar por:", ["Mês", "Fechamento"], 0, False
        )
        if not ok:
            return
        grupos = {}
        for r in self.estado.consultar_vendas(self.intervalo_vendas, self.dias):
            d = (
                r.data
                if modo == "Mês" or r.data.day > 9
                else r.data.replace(day=1) - timedelta(days=1)
            )
            key = d.replace(day=1)
            grupos[key] = grupos.get(key, 0) + r.total
        self.detalhes(
            "Evolução por " + modo.lower() + " — seleção aplicada",
            [f"{k:%m/%Y}: {moeda(v)}" for k, v in sorted(grupos.items())]
            or ["Sem vendas."],
        )

    def detalhes_vendas(self):
        self.detalhes(
            "Vendas da consulta completa",
            [
                f"{r.data:%d/%m/%Y}: {moeda(r.total)}"
                for r in self.estado.consultar_vendas(self.intervalo_vendas, self.dias)
            ]
            or ["Sem vendas."],
        )

    def confirmar_exclusao(self, area, ids):
        if not ids:
            return
        texto_aviso = f"Excluir {len(ids)} registro(s) fictício(s) selecionado(s) de {area}?\n\nApenas esta demonstração em memória será alterada. Fechar e abrir a demo restaura os exemplos."
        if area == "Finanças":
            texto_aviso += "\n\nSomente os lançamentos selecionados serão removidos, sem excluir automaticamente as demais parcelas da compra."
        box = W.QMessageBox(
            W.QMessageBox.Icon.Warning,
            "Excluir seleção da demo",
            texto_aviso,
            parent=self,
        )
        excluir = box.addButton(
            "Excluir selecionados", W.QMessageBox.ButtonRole.DestructiveRole
        )
        cancelar = box.addButton("Cancelar", W.QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancelar)
        box.setEscapeButton(cancelar)
        box.exec()
        if box.clickedButton() == excluir:
            self.excluir_confirmado(area, ids)

    def excluir_confirmado(self, area, ids):
        self.estado.excluir(area, ids)
        self.atualizar_vendas()
        if "Finanças" in self.paginas:
            self.atualizar_financas()
        if "Análises" in self.paginas:
            self.atualizar_analises()
        self.status.setText(
            f"Demo: {len(ids)} registro(s) removido(s) apenas da memória · dados reais não acessados"
        )


def preparar():
    global FAMILIA
    app = W.QApplication.instance() or W.QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    families = []
    for path in sorted((R / "fontes").glob("*.ttf")):
        key = G.QFontDatabase.addApplicationFont(str(path))
        if key >= 0:
            families.extend(G.QFontDatabase.applicationFontFamilies(key))
    if families:
        FAMILIA = families[0]
    app.setFont(G.QFont(FAMILIA, 10))
    app.setStyleSheet(
        ESTILO.replace("FONTE", FAMILIA)
        + '\nQCheckBox::indicator:checked { image:url("'
        + (R / "icones/check-selecao.svg").as_posix()
        + '"); }'
    )
    return app


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--pagina", choices=["Vendas", "Análises", "Finanças"], default="Vendas"
    )
    p.add_argument("--captura")
    p.add_argument("--largura", type=int, default=1536)
    p.add_argument("--altura", type=int, default=1024)
    args = p.parse_args()
    app = preparar()
    janela = Aplicativo()
    janela.resize(args.largura, args.altura)
    janela.mostrar(args.pagina)
    janela.show()
    app.processEvents()
    if args.captura:
        for _ in range(6):
            app.processEvents()
        janela.grab().save(args.captura)
        janela.close()
    else:
        sys.exit(app.exec())
