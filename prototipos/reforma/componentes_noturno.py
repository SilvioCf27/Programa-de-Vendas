"""Componentes visuais compartilhados pela demo e suas janelas de detalhe."""

from pathlib import Path
from PySide6 import QtCore as Q, QtGui as G, QtWidgets as W, QtSvg
from tema_noturno import C, TIPOGRAFIA, ESPACOS, estilo
from modelo import AJUDAS

R = Path(__file__).resolve().parent / "recursos"


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
