"""Revisão visual Noturno: dados fictícios, descartáveis e sem conexão externa."""

import argparse
import os
from pathlib import Path
import sys

if sys.platform != "win32":
    os.environ.setdefault("QT_FONT_DPI", "96")
try:
    from PySide6 import QtCore as Q, QtGui as G, QtWidgets as W, QtSvg
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise
    prefixo = "& " if sys.platform == "win32" else ""
    print(
        "Falta instalar o PySide6 no Python que está abrindo a demo.\n"
        "No terminal da cópia de estudo, execute:\n"
        f'{prefixo}"{sys.executable}" -m pip install -r prototipos/reforma/requirements.txt\n'
        "Depois execute novamente noturno_demo.py.",
        file=sys.stderr,
    )
    raise SystemExit(1) from None
from estado_demo import Estado, HOJE, MESES, DIAS, agrupar, limites, dividir
from modelo import moeda, AJUDAS
from apresentacao_noturno import variacao_percentual

R = Path(__file__).resolve().parent / "recursos"
from tema_noturno import C, ESTILO, estilo, TIPOGRAFIA, ESPACOS

FAMILIA = "Segoe UI"


def texto(s, size=10, color=None, bold=False, tipo=None):
    w = W.QLabel(s)
    pixels = TIPOGRAFIA[tipo] if tipo else round(size * 4 / 3)
    w.setStyleSheet(
        f'font-size:{pixels}px;color:{color or C["text"]};font-weight:{600 if bold else 400};background:transparent;border:0;'
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
    b.setMinimumHeight(36)
    if nome:
        b.setIcon(icone(nome))
    b.setIconSize(Q.QSize(19, 19))
    b.setProperty("primary", primary)
    b.setProperty("query", nome == "search")
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
    b.setStyleSheet(estilo("padding:0;font-size:10pt;color:@muted@;"))
    b.setToolTip(s)
    b.setAccessibleName("Ajuda: " + chave)
    return b


def cor_alpha(valor, alfa):
    cor = G.QColor(valor)
    cor.setAlpha(alfa)
    return cor


def tile(nome, cor, size=40):
    w = W.QLabel()
    w.setPixmap(icone(nome, cor, 25).pixmap(25, 25))
    w.setAlignment(Q.Qt.AlignmentFlag.AlignCenter)
    w.setFixedSize(size, size)
    w.setStyleSheet(
        f"background:{cor}22;border:0;border-radius:9px;".replace(
            cor + "22",
            "rgba(" + ",".join(str(x) for x in G.QColor(cor).getRgb()[:3]) + ",35)",
        )
    )
    return w


def titulo_secao(nome, ico, sub=None):
    w = W.QWidget()
    h = W.QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(12)
    h.addWidget(tile(ico, C["blue"], 34))
    col = W.QVBoxLayout()
    col.setSpacing(3)
    col.addWidget(texto(nome, 14, bold=True, tipo="painel"))
    if sub:
        col.addWidget(texto(sub, 9, C["muted"]))
    h.addLayout(col, 1)
    w.setSizePolicy(W.QSizePolicy.Policy.Expanding, W.QSizePolicy.Policy.Fixed)
    return w


def acesso(nome, sub, ico, cor, acao):
    b = botao("", acao)
    h = W.QHBoxLayout(b)
    h.setContentsMargins(12, 12, 12, 12)
    h.addWidget(tile(ico, cor, 42))
    col = W.QVBoxLayout()
    col.setSpacing(5)
    title = texto(nome, 10, bold=True)
    title.setWordWrap(True)
    col.addWidget(title)
    label = texto(sub, 8, C["muted"])
    label.setWordWrap(True)
    col.addWidget(label)
    h.addLayout(col, 1)
    h.addWidget(texto("›", 22, cor))
    # Labels must not intercept clicks intended for the whole access card.
    for w in b.findChildren(W.QWidget):
        w.setAttribute(Q.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    b.setAccessibleName(nome)
    b.setMinimumHeight(76)
    return b


class FaixaSemana(W.QFrame):
    def __init__(self):
        super().__init__()
        self.foto = G.QPixmap(str(R / "fundo-lateral.png"))
        self.setMinimumHeight(132)

    def paintEvent(self, event):
        p = G.QPainter(self)
        p.setRenderHint(G.QPainter.RenderHint.Antialiasing)
        path = G.QPainterPath()
        path.addRoundedRect(Q.QRectF(self.rect().adjusted(1, 1, -1, -1)), 12, 12)
        p.setClipPath(path)
        p.fillRect(self.rect(), G.QColor(C["hero"]))
        target = Q.QRectF(self.width() * 0.65, 0, self.width() * 0.35, self.height())
        p.drawPixmap(
            target,
            self.foto,
            Q.QRectF(
                0,
                520,
                self.foto.width(),
                self.foto.width() * target.height() / max(1, target.width()),
            ),
        )
        fade = G.QLinearGradient(0, 0, self.width(), 0)
        fade.setColorAt(0, G.QColor(C["hero"]))
        fade.setColorAt(0.62, G.QColor(C["hero"]))
        fade.setColorAt(1, cor_alpha(C["hero"], 100))
        p.fillRect(self.rect(), fade)
        p.setClipping(False)
        p.setPen(G.QPen(G.QColor(C["green"]), 1))
        p.setBrush(Q.Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()


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
        p.fillRect(target, cor_alpha(C["bg"], 45 if self.lateral else 205))
        if self.lateral:
            grad = G.QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0, cor_alpha(C["bg"], 230))
            grad.setColorAt(0.36, cor_alpha(C["bg"], 105))
            grad.setColorAt(0.75, cor_alpha(C["bg"], 40))
            grad.setColorAt(1, cor_alpha(C["bg"], 230))
            p.fillRect(self.rect(), grad)
        p.end()


class LinhaResponsiva(W.QBoxLayout):
    """Empilha grupos completos quando a largura útil não comporta a linha."""

    def __init__(self, limite=950):
        super().__init__(W.QBoxLayout.Direction.TopToBottom)
        self.limite = limite

    def setGeometry(self, rect):
        sentido = (
            W.QBoxLayout.Direction.LeftToRight
            if rect.width() >= self.limite
            else W.QBoxLayout.Direction.TopToBottom
        )
        if self.direction() != sentido:
            self.setDirection(sentido)
        super().setGeometry(rect)


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
        n = 6 if self.width() >= 1200 else 3
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
        self.tipo.setMinimumContentsLength(6 if comparacao else 9)
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
            row, col = (i, 0) if compacto else (0, i)
            self.grid.addWidget(label, row, col)
            self.grid.addWidget(
                campo, row if compacto else row + 1, 1 if compacto else col
            )
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
                estilo(
                    "background:@field@;border:1px solid @border@;border-radius:6px;padding:7px;"
                )
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
            layout.setContentsMargins(5, 3, 5, 3)
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
                b.setStyleSheet(
                    "padding:3px;border:1px solid "
                    + (C["delete_border"] if nome == "trash-2" else C["edit_border"])
                    + ";background:"
                    + (C["delete"] if nome == "trash-2" else C["edit"])
                    + ";border-radius:5px;"
                )
                b.setToolTip(tip)
                b.setAccessibleName(f"{tip} {identificador}")
                layout.addWidget(b)
            self.table.setCellWidget(row, self.table.columnCount() - 1, acoes)
        self.table.setColumnWidth(self.table.columnCount() - 1, 92)
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
        self.alvos = []
        self.setMouseTracking(True)
        self.setMinimumHeight(155)
        self.setAccessibleName(
            "Gráfico; valores disponíveis também nas tabelas e legendas"
        )

    def mouseMoveEvent(self, event):
        for rect, tip in self.alvos:
            if rect.contains(event.position()):
                self.setToolTip(tip)
                break
        else:
            self.setToolTip("Valores também disponíveis nas tabelas da seleção.")
        super().mouseMoveEvent(event)

    def paintEvent(self, e):
        import math

        p = G.QPainter(self)
        p.setRenderHint(G.QPainter.RenderHint.Antialiasing)
        font = G.QFont(FAMILIA)
        font.setPixelSize(12)
        p.setFont(font)
        self.alvos = []
        if self.modo == "barras":
            left = 74
            right = self.width() - 12
            top = 28
            base = self.height() - 39
            maximum = max([v for _, v in self.dados] + [1])
            raw = max(100, maximum / 3)
            power = 10 ** math.floor(math.log10(raw))
            step_tick = math.ceil(raw / power) * power
            ceiling = step_tick * 3
            for n in range(4):
                y = base - (base - top) * n / 3
                p.setPen(G.QPen(G.QColor(C["border"]), 1))
                p.drawLine(left, int(y), right, int(y))
                p.setPen(G.QColor(C["muted"]))
                p.drawText(
                    Q.QRectF(0, y - 9, left - 8, 18),
                    Q.Qt.AlignmentFlag.AlignRight,
                    moeda(step_tick * n),
                )
            step = (right - left) / max(1, len(self.dados))
            stride = max(1, math.ceil(len(self.dados) / 6))
            for i, (label, value) in enumerate(self.dados):
                x = left + i * step + step * 0.16
                bw = step * 0.68
                bh = (base - top) * value / ceiling
                rect = Q.QRectF(x, base - bh, bw, bh)
                if value:
                    gradient = G.QLinearGradient(0, base - bh, 0, base)
                    gradient.setColorAt(0, G.QColor(C["blue"]).lighter(115))
                    gradient.setColorAt(1, G.QColor(C["query"]))
                    p.setPen(Q.Qt.PenStyle.NoPen)
                    p.setBrush(gradient)
                    p.drawRoundedRect(rect, 4, 4)
                else:
                    p.setPen(G.QPen(G.QColor(C["muted"]), 2))
                    p.drawLine(int(x), base, int(x + bw), base)
                p.setPen(G.QColor(C["text"]))
                if step >= 60:
                    p.drawText(
                        Q.QRectF(x - step * 0.15, base - bh - 23, step, 20),
                        Q.Qt.AlignmentFlag.AlignCenter,
                        moeda(value),
                    )
                if i % stride == 0:
                    p.setPen(G.QColor(C["muted"]))
                    partes = label.split("–")
                    p.drawText(
                        Q.QRectF(x - step * 0.15, base + 7, step, 30),
                        Q.Qt.AlignmentFlag.AlignCenter,
                        "\n".join(partes),
                    )
                self.alvos.append(
                    (
                        Q.QRectF(x, base - max(14, bh), bw, max(14, bh)),
                        label + ": " + moeda(value),
                    )
                )
            if not self.dados:
                p.setPen(G.QColor(C["muted"]))
                p.drawText(
                    self.rect(), Q.Qt.AlignmentFlag.AlignCenter, "Sem vendas na seleção"
                )
        else:
            total = sum(v for _, v in self.dados)
            diameter = min(145, self.width() * 0.30, self.height() - 6)
            box = Q.QRectF(5, (self.height() - diameter) / 2, diameter, diameter)
            start = 90 * 16
            for i, (label, value) in enumerate(self.dados):
                color = [C["yellow"], C["purple"], C["blue"]][i]
                angle = round(360 * 16 * value / total) if total else 0
                p.setPen(G.QPen(G.QColor(color), 15))
                p.drawArc(box.adjusted(9, 9, -9, -9), start, -angle)
                start -= angle
                y = (self.height() - 78) / 2 + i * 28
                name_x = box.right() + 17
                money_x = self.width() - 100
                percent_x = money_x - 57
                p.setPen(Q.Qt.PenStyle.NoPen)
                p.setBrush(G.QColor(color))
                p.drawEllipse(Q.QPointF(name_x + 4, y + 7), 4, 4)
                p.setPen(G.QColor(C["text"]))
                p.drawText(
                    Q.QRectF(name_x + 15, y - 2, max(50, percent_x - name_x - 15), 22),
                    Q.Qt.AlignmentFlag.AlignLeft,
                    label,
                )
                percent = f"{value/total*100:.1f}%".replace(".", ",") if total else "—"
                p.drawText(
                    Q.QRectF(percent_x, y - 2, 50, 22),
                    Q.Qt.AlignmentFlag.AlignRight,
                    percent,
                )
                p.drawText(
                    Q.QRectF(money_x, y - 2, 97, 22),
                    Q.Qt.AlignmentFlag.AlignRight,
                    moeda(value),
                )
                self.alvos.append(
                    (
                        Q.QRectF(name_x, y - 2, self.width() - name_x, 24),
                        label + ": " + moeda(value) + " · " + percent,
                    )
                )
            if not total:
                p.setPen(G.QPen(G.QColor(C["border"]), 15))
                p.drawArc(box.adjusted(9, 9, -9, -9), 0, 360 * 16)
                p.setPen(G.QColor(C["muted"]))
                p.drawText(box, Q.Qt.AlignmentFlag.AlignCenter, "Sem vendas")
            elif diameter >= 125:
                p.setPen(G.QColor(C["text"]))
                p.drawText(
                    box.adjusted(10, 35, -10, -45),
                    Q.Qt.AlignmentFlag.AlignCenter,
                    moeda(total),
                )
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
        side.setFixedWidth(226)
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
            b.setIconSize(Q.QSize(25, 25))
            sl.addWidget(b)
            self.nav[nome] = b
        sl.addStretch()
        sl.addWidget(texto("PRÉVIA DE INTERFACE", 9, C["muted"]))
        sl.addWidget(texto("Dados fictícios · sem conexão", 8, C["discrete"]))
        root.addWidget(side)
        main = Fundo()
        ml = W.QVBoxLayout(main)
        ml.setContentsMargins(ESPACOS["margem"], 18, ESPACOS["margem"], 10)
        ml.setSpacing(14)
        header = LinhaResponsiva(1050)
        title = W.QVBoxLayout()
        self.titulo = texto("", 24, bold=True, tipo="titulo")
        self.subtitulo = texto("", 10, C["muted"])
        title.addWidget(self.titulo)
        title.addWidget(self.subtitulo)
        header.addLayout(title)
        header.addStretch()
        acoes_cabecalho = W.QHBoxLayout()
        acoes_cabecalho.addWidget(
            botao("", lambda: self.aviso("Configurações"), "settings")
        )
        acoes_cabecalho.addWidget(
            botao("Tema: Noturno", lambda: self.aviso("Temas"), "moon")
        )
        acoes_cabecalho.addWidget(
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
        acoes_cabecalho.addWidget(self.novo)
        header.addLayout(acoes_cabecalho)
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
        area.setStyleSheet(
            estilo("background:@panel@;border:1px solid @border@;padding:15px;")
        )
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
            layout.setSpacing(ESPACOS["intervalo"])
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
        l.setSpacing(6)
        base = G.QColor(C["bg"])
        accent = G.QColor(cor)
        tint = G.QColor(
            *[
                round(base.getRgb()[i] * 0.88 + accent.getRgb()[i] * 0.12)
                for i in range(3)
            ]
        ).name()
        border = G.QColor(
            *[
                round(base.getRgb()[i] * 0.60 + accent.getRgb()[i] * 0.40)
                for i in range(3)
            ]
        ).name()
        w.setStyleSheet(
            estilo(
                f'QFrame[panel="true"]{{border:1px solid {border};background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {tint},stop:1 @card_end@);border-radius:12px;}}'
            )
        )
        h = W.QHBoxLayout()
        h.setSpacing(9)
        h.addWidget(tile(ico, cor, 30 if nota is None else 32))
        h.addWidget(texto(titulo, 9, C["text"]))
        h.addStretch()
        if chave:
            h.addWidget(ajuda(chave))
        l.addLayout(h)
        value = texto(valor, 22, cor, True, tipo="valor")
        l.addWidget(value)
        if nota:
            l.addWidget(texto(nota, 9, C["muted"]))
        return w, value

    def construir_vendas(self, l):
        cards = Cartoes()
        self.cards = []
        self.notas_cards = []
        self.barras_cards = []
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
            if len(self.cards) > 1:
                value.setStyleSheet(
                    f'font-size:22pt;font-weight:600;color:{C["text"]};background:transparent;border:0;'
                )
            note = texto("", 9, C["muted"])
            w.layout().addWidget(note)
            self.notas_cards.append(note)
            bar = W.QProgressBar()
            bar.setRange(0, 1000)
            bar.setTextVisible(False)
            bar.setFixedHeight(5)
            bar.setStyleSheet(
                estilo(
                    f"QProgressBar{{background:@progress_track@;border:0;border-radius:2px;}}QProgressBar::chunk{{background:{color};border-radius:2px;}}"
                )
            )
            bar.setVisible(len(self.cards) > 3)
            w.layout().addWidget(bar)
            self.barras_cards.append(bar)
        l.addWidget(cards)
        semana = FaixaSemana()
        sl = W.QVBoxLayout(semana)
        sl.setContentsMargins(18, 12, 18, 12)
        linha = W.QHBoxLayout()
        esquerda = W.QVBoxLayout()
        semana_header = W.QHBoxLayout()
        semana_header.addWidget(tile("calendar-days", C["turquoise"], 32))
        semana_header.addWidget(texto("Semana atual", 15, C["turquoise"], True))
        semana_header.addStretch()
        esquerda.addLayout(semana_header)
        self.semana_texto = texto("", 10, C["muted"])
        esquerda.addWidget(self.semana_texto)
        self.semana_valor = texto("", 24, bold=True)
        esquerda.addWidget(self.semana_valor)
        linha.addLayout(esquerda, 1)
        self.semana_formas = W.QWidget()
        sg = W.QGridLayout(self.semana_formas)
        sg.setContentsMargins(16, 0, 16, 0)
        sg.setVerticalSpacing(7)
        sg.setColumnStretch(1, 1)
        sg.addWidget(texto("Por forma de pagamento", 9, C["muted"]), 0, 0, 1, 3)
        self.semana_pagamentos = {}
        for n, (nome, key, ico, cor) in enumerate(
            [
                ("Dinheiro", "dinheiro", "banknote", C["yellow"]),
                ("Pix", "pix", "gem", C["purple"]),
                ("Cartão", "cartao", "credit-card", C["blue"]),
            ],
            1,
        ):
            image = W.QLabel()
            image.setPixmap(icone(ico, cor, 18).pixmap(18, 18))
            image.setFixedWidth(20)
            sg.addWidget(image, n, 0)
            sg.addWidget(texto(nome, 10, C["muted"]), n, 1)
            value = texto("", 10)
            value.setAlignment(Q.Qt.AlignmentFlag.AlignRight)
            sg.addWidget(value, n, 2)
            self.semana_pagamentos[key] = value
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
        faixa = LinhaResponsiva(900)
        faixa.setSpacing(10)
        anterior, fl = caixa(12)
        fl.addWidget(
            titulo_secao("Comparação com o período anterior", "arrow-right-left")
        )
        self.anterior = texto("", 10, C["muted"])
        self.anterior.setWordWrap(True)
        fl.setAlignment(Q.Qt.AlignmentFlag.AlignTop)
        comparacao_linha = W.QHBoxLayout()
        comparacao_linha.setSpacing(16)
        comparacao_linha.addWidget(self.anterior, 1)
        variacao = W.QVBoxLayout()
        variacao.setSpacing(3)
        variacao.addWidget(texto("Variação do total", 9, C["muted"]))
        self.anterior_diferenca = texto("", 18, bold=True)
        variacao.addWidget(self.anterior_diferenca)
        self.anterior_percentual = texto("", 10, C["muted"])
        variacao.addWidget(self.anterior_percentual)
        comparacao_linha.addLayout(variacao)
        fl.addLayout(comparacao_linha)
        faixa.addWidget(anterior, 6)
        participacao, pl = caixa(10)
        pl.setSpacing(6)
        ph = W.QHBoxLayout()
        ph.addWidget(texto("Participação no período", 11, bold=True))
        ph.addStretch()
        ph.addWidget(
            ajuda(
                "Participação",
                "Proporção de cada forma de pagamento no total bruto da consulta aplicada.",
            )
        )
        pl.addLayout(ph)
        self.pizza_vendas = Grafico("pizza")
        self.pizza_vendas.setMinimumHeight(94)
        self.pizza_vendas.setMaximumHeight(96)
        pl.addWidget(self.pizza_vendas)
        faixa.addWidget(participacao, 5)
        l.addLayout(faixa)
        baixo = LinhaResponsiva(995)
        baixo.setSpacing(12)
        hist, hl = caixa()
        header = W.QHBoxLayout()
        header.addWidget(titulo_secao("Histórico de vendas", "list"))
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
        ff.addWidget(titulo_secao("Filtros do histórico", "filter"))
        self.seletor_vendas = Seletor(True, True)
        ff.addWidget(self.seletor_vendas)
        ff.addWidget(texto("Dias da semana", 10, C["muted"]))
        grade = W.QGridLayout()
        self.dias_checks = []
        for i, s in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
            c = W.QPushButton("✓ " + s)
            c.setCheckable(True)
            c.setChecked(True)
            c.setProperty("day", True)
            c.setProperty("active", True)
            c.setAccessibleName(DIAS[i])
            c.setToolTip(DIAS[i])

            def estado_dia(checked, button=c, name=s):
                button.setText(("✓ " if checked else "") + name)
                button.setProperty("active", checked)
                button.style().unpolish(button)
                button.style().polish(button)
                self.pendente_vendas()

            c.toggled.connect(estado_dia)
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
        notas = [
            f"{len(rows)} dias de feira",
            f"Média: {moeda(dividir(total,len(rows)))}",
            "Inclui dias zerados",
        ] + [
            (
                f"{v/total*100:.1f}% do período".replace(".", ",")
                if total
                else "Sem participação"
            )
            for v in pagamentos
        ]
        for i, note in enumerate(self.notas_cards):
            note.setText(notas[i])
        for i, v in enumerate(pagamentos, 3):
            self.barras_cards[i].setValue(round(v / total * 1000) if total else 0)
        self.pizza_vendas.dados = list(zip(["Dinheiro", "Pix", "Cartão"], pagamentos))
        self.pizza_vendas.update()
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
                f"{anterior[0]:%d/%m/%Y} a {anterior[1]:%d/%m/%Y}\n{moeda(antes)} em {len(anteriores)} dias de feira\nMédia anterior: {moeda(dividir(antes,len(anteriores)))}"
            )
            delta = total - antes
            self.anterior_diferenca.setText(
                ("↑ " if delta > 0 else "↓ " if delta < 0 else "= ") + moeda(delta)
            )
            self.anterior_diferenca.setStyleSheet(
                f'font-size:24px;font-weight:700;color:{C["red"] if delta<0 else C["turquoise"]};'
            )
            self.anterior_percentual.setText(variacao_percentual(total, antes))
        else:
            self.anterior.setText("Selecione um período para comparar com o anterior.")
            self.anterior_diferenca.setText("—")
            self.anterior_percentual.setText("Sem período de referência")
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
        for key, label in self.semana_pagamentos.items():
            label.setText(moeda(sum(getattr(r, key) for r in semana)))

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
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(6)
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
        for key, title, ico, cor in [
            ("bruto", "Vendas brutas", "wallet", C["green"]),
            ("taxas", "Taxas cadastradas", "percent", C["yellow"]),
            ("liquido", "Vendas menos taxas", "banknote", C["blue"]),
        ]:
            col = W.QVBoxLayout()
            col.addWidget(texto(title, 9, C["muted"]))
            v = texto("", 15, bold=True)
            col.addWidget(v)
            item = W.QHBoxLayout()
            item.addWidget(tile(ico, cor, 36))
            item.addLayout(col, 1)
            sh.addLayout(item, 1)
            if key != "liquido":
                line = W.QFrame()
                line.setFrameShape(W.QFrame.Shape.VLine)
                line.setStyleSheet(f'color:{C["border"]};')
                sh.addWidget(line)
            self.fin_secundarios[key] = v
        sh.addWidget(ajuda("taxas"))
        sl.addLayout(sh)
        l.addWidget(secundario)
        lista, ll = caixa()
        h = W.QHBoxLayout()
        h.addWidget(titulo_secao("Lançamentos do período", "receipt"))
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
        self.fin_recorte.hide()
        self.fin_recorte.currentIndexChanged.connect(self.atualizar_financas)
        tipo = W.QHBoxLayout()
        tipo.addWidget(self.fin_recorte)
        self.recortes_botoes = []
        for i, label in enumerate(["Todas", "Despesas", "Taxas", "Parcelas"]):
            b = botao(
                label, lambda checked=False, n=i: self.fin_recorte.setCurrentIndex(n)
            )
            b.setProperty("active", i == 0)
            tipo.addWidget(b)
            self.recortes_botoes.append(b)

        def selecionar_recorte(index):
            for i, b in enumerate(self.recortes_botoes):
                b.setProperty("active", i == index)
                b.style().unpolish(b)
                b.style().polish(b)

        self.fin_recorte.currentIndexChanged.connect(selecionar_recorte)
        tipo.addWidget(
            ajuda(
                "Filtro da lista",
                "Este recorte altera só a lista de lançamentos. Os totais acima continuam considerando a consulta financeira completa.",
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
        self.tabela_financas.table.setMinimumHeight(245)
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
            sub = {
                "Despesas por semana": "Despesas agrupadas por semana.",
                "Histórico de taxas": "Taxas e ajustes históricos.",
                "Regra de fechamento": "Fechamento e vigência da regra.",
            }[nome]
            links.addWidget(
                acesso(
                    nome, sub, ico, C["yellow"] if ico == "percent" else C["blue"], acao
                ),
                1,
            )
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
        graficos = LinhaResponsiva(950)
        barras, bl = caixa()
        bl.addWidget(titulo_secao("Resultado por semana", "trending-up"))
        self.barras = Grafico()
        bl.addWidget(self.barras, 1)
        graficos.addWidget(barras, 5)
        resumo, rl = caixa(10)
        rl.setSpacing(8)
        rl.addWidget(titulo_secao("Resumo da seleção", "receipt"))
        self.ana_valores = {}
        mini = W.QGridLayout()
        mini.setSpacing(6)
        for key, nome, row, col, span in [
            ("total", "Total do período", 0, 0, 2),
            ("semanas", "Semanas", 1, 0, 1),
            ("dias", "Dias de feira", 1, 1, 1),
            ("media", "Média por dia", 2, 0, 2),
        ]:
            box, vl = caixa(5)
            vl.setSpacing(3)
            vl.addWidget(texto(nome, 8, C["muted"]))
            value = texto("", 15 if key in ("total", "media") else 17, bold=True)
            vl.addWidget(value)
            self.ana_valores[key] = value
            mini.addWidget(box, row, col, 1, span)
        rl.addLayout(mini)
        graficos.addWidget(resumo, 2)
        pizza, pl = caixa()
        pl.addWidget(titulo_secao("Participação por pagamento", "chart-pie"))
        self.pizza = Grafico("pizza")
        pl.addWidget(self.pizza, 1)
        graficos.addWidget(pizza, 4)
        l.addLayout(graficos)
        table, tl = caixa()
        tl.addWidget(titulo_secao("Detalhamento por semana", "calendar-days"))
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
        self.ana_tabela.setMinimumHeight(80)
        self.ana_tabela.setShowGrid(False)
        self.ana_tabela.verticalHeader().setDefaultSectionSize(29)
        self.ana_tabela.horizontalHeader().setFixedHeight(31)
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
        baixo = LinhaResponsiva(995)
        comp, cl = caixa()
        cl.addWidget(titulo_secao("Comparar períodos (A e B)", "arrow-right-left"))
        cl.addWidget(
            texto("Consulta independente dos filtros de Vendas.", 9, C["muted"])
        )
        campos = W.QHBoxLayout()
        self.a = Seletor(comparacao=True)
        self.b = Seletor(comparacao=True)
        self.a.tipo.setCurrentText("Mês")
        self.b.tipo.setCurrentText("Mês")
        self.b.mes.setCurrentIndex(8)
        for nome, c, cor in [
            ("Período A", self.a, C["turquoise"]),
            ("Período B", self.b, C["blue"]),
        ]:
            group, col = caixa(10)
            group.setStyleSheet(
                f'QFrame[panel="true"]{{background:{C["side"]};border:1px solid {cor};border-radius:9px;}}'
            )
            col.addWidget(texto(nome, 10, cor, True))
            col.addWidget(c)
            campos.addWidget(group, 1)
        cl.addLayout(campos)
        cl.addWidget(
            botao("Comparar períodos", self.comparar, "arrow-right-left", True)
        )
        self.ana_comparacao = texto("", 14, bold=True)
        self.ana_comparacao.setWordWrap(True)
        cl.addWidget(self.ana_comparacao)
        self.ana_diferenca = texto("", 16, bold=True)
        cl.addWidget(self.ana_diferenca)
        self.ana_percentual = texto("", 9, C["muted"])
        cl.addWidget(self.ana_percentual)
        baixo.addWidget(comp, 4)
        det, dl = caixa()
        dl.addWidget(titulo_secao("Detalhes do período", "list"))
        dl.addWidget(texto("Mesma seleção aplicada em Vendas.", 9, C["muted"]))
        acessos_grid = W.QGridLayout()
        acessos_grid.setSpacing(10)
        for indice, (nome, ico, acao) in enumerate(
            [
                ("Resultados por dia da semana", "calendar-days", self.detalhes_dias),
                ("Evolução mensal / fechamento", "trending-up", self.detalhes_evolucao),
                (
                    "Formas de pagamento",
                    "chart-pie",
                    lambda: self.detalhes("Formas de pagamento", [self.participacao]),
                ),
                ("Lista de vendas da seleção", "list", self.detalhes_vendas),
            ]
        ):
            sub = {
                "Resultados por dia da semana": "Totais e dias registrados de segunda a domingo.",
                "Evolução mensal / fechamento": "Compare a evolução da seleção ao longo dos períodos.",
                "Formas de pagamento": "Veja a distribuição entre dinheiro, Pix e cartão.",
                "Lista de vendas da seleção": "Confira todos os registros da consulta aplicada.",
            }[nome]
            button = acesso(
                nome, sub, ico, C["purple"] if ico == "chart-pie" else C["blue"], acao
            )
            button.setMinimumHeight(110)
            acessos_grid.addWidget(button, indice // 2, indice % 2)
        dl.addLayout(acessos_grid)
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
        for key, val in dict(
            total=moeda(total),
            semanas=str(len(grupos)),
            dias=str(len(rows)),
            media=moeda(dividir(total, len(rows))),
        ).items():
            self.ana_valores[key].setText(val)
        self.barras.dados = [
            (f"{d:%d/%m}–{d+timedelta(days=6):%d/%m}", sum(r.total for r in rs))
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
        altura = (
            self.ana_tabela.horizontalHeader().height()
            + 29 * max(1, min(len(grupos), 6))
            + 6
        )
        self.ana_tabela.setFixedHeight(altura)
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
        self.ana_comparacao.setText(f"A: {moeda(va)}   |   B: {moeda(vb)}")

        self.ana_diferenca.setText(f"Diferença A − B: {moeda(va-vb)}")
        self.ana_diferenca.setStyleSheet(
            f'font-size:22px;font-weight:700;color:{C["red"] if va<vb else C["turquoise"]};'
        )
        self.ana_percentual.setText(variacao_percentual(va, vb))

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
