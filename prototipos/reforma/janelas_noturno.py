"""Janelas de leitura da demonstração. Sem SQLite, rede ou escrita de dados."""

from dataclasses import dataclass
from datetime import date, timedelta
from PySide6 import QtCore as Q, QtGui as G, QtWidgets as W
from componentes_noturno import texto, botao, caixa, ajuda, tile
from tema_noturno import C, estilo
from estado_demo import DIAS, dividir
from modelo import moeda


def contexto(intervalo):
    a, b = intervalo
    return (
        "Todas as datas da consulta aplicada"
        if a == date.min
        else f"{a:%d/%m/%Y} a {b:%d/%m/%Y}"
    )


@dataclass(frozen=True)
class Coluna:
    nome: str
    formato: str = "texto"
    ampla: bool = False


class ModeloDetalhe(Q.QAbstractTableModel):
    """Snapshot de leitura; ordenação visual não altera a consulta de origem."""

    def __init__(self, colunas, linhas, parent=None):
        super().__init__(parent)
        self.colunas = tuple(colunas)
        self.linhas = list(linhas)

    def rowCount(self, parent=Q.QModelIndex()):
        return 0 if parent.isValid() else len(self.linhas)

    def columnCount(self, parent=Q.QModelIndex()):
        return 0 if parent.isValid() else len(self.colunas)

    def headerData(self, section, orientation, role=Q.Qt.ItemDataRole.DisplayRole):
        if role == Q.Qt.ItemDataRole.DisplayRole:
            return (
                self.colunas[section].nome
                if orientation == Q.Qt.Orientation.Horizontal
                else section + 1
            )
        return None

    def data(self, index, role=Q.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        c = self.colunas[index.column()]
        v = self.linhas[index.row()][index.column()]
        if role in (Q.Qt.ItemDataRole.DisplayRole, Q.Qt.ItemDataRole.ToolTipRole):
            return (
                moeda(v)
                if c.formato == "moeda"
                else (
                    v.strftime("%d/%m/%Y")
                    if c.formato == "data"
                    else v.strftime("%m/%Y") if c.formato == "mes" else str(v)
                )
            )
        if role == Q.Qt.ItemDataRole.TextAlignmentRole:
            return Q.Qt.AlignmentFlag.AlignVCenter | (
                Q.Qt.AlignmentFlag.AlignRight
                if c.formato in ("moeda", "numero")
                else Q.Qt.AlignmentFlag.AlignLeft
            )
        if role == Q.Qt.ItemDataRole.UserRole:
            return v
        return None

    def sort(self, column, order=Q.Qt.SortOrder.AscendingOrder):
        if not 0 <= column < len(self.colunas):
            return
        self.beginResetModel()
        self.linhas.sort(
            key=lambda row: row[column], reverse=order == Q.Qt.SortOrder.DescendingOrder
        )
        self.endResetModel()


class JanelaDetalhe(W.QDialog):
    def __init__(
        self, parent, titulo, subtitulo, icone="list", compacta=False, explicacao=None
    ):
        super().__init__(parent)
        self.setWindowTitle(titulo + " — estudo Noturno")
        self.setStyleSheet(f'QDialog{{background:{C["bg"]};}}')
        self.setModal(True)
        largura = min(960, max(480, parent.width() - 64))
        altura = min(600, max(320, parent.height() - 100))
        self.resize(
            min(640, largura) if compacta else largura, 340 if compacta else altura
        )
        self.setMinimumSize(460, 280)
        root = W.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(16)
        header = W.QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(tile(icone, C["turquoise"], 42))
        titles = W.QVBoxLayout()
        titles.setSpacing(4)
        title = texto(titulo, 16, bold=True)
        title.setWordWrap(True)
        titles.addWidget(title)
        sub = texto(subtitulo, 9, C["muted"])
        sub.setWordWrap(True)
        titles.addWidget(sub)
        header.addLayout(titles, 1)
        if explicacao:
            header.addWidget(ajuda(titulo, explicacao))
        root.addLayout(header)
        self.scroll = W.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.corpo = W.QWidget()
        self.conteudo = W.QVBoxLayout(self.corpo)
        self.conteudo.setContentsMargins(0, 0, 0, 0)
        self.conteudo.setSpacing(12)
        self.scroll.setWidget(self.corpo)
        root.addWidget(self.scroll, 1)
        footer = W.QHBoxLayout()
        nota = texto("Dados fictícios · somente leitura", 8, C["discrete"])
        footer.addWidget(nota)
        footer.addStretch()
        self.fechar = botao("Fechar", self.accept)
        self.fechar.setAutoDefault(False)
        self.fechar.setDefault(False)
        footer.addWidget(self.fechar)
        root.addLayout(footer)
        self.setAccessibleDescription(subtitulo)
        self.tabela = None
        self.modelo = None

    def resumo(self, valores):
        box, layout = caixa(12)
        linha = W.QHBoxLayout()
        linha.setSpacing(20)
        for titulo, valor in valores:
            item = W.QVBoxLayout()
            item.setSpacing(4)
            item.addWidget(texto(titulo, 9, C["muted"]))
            item.addWidget(texto(str(valor), 17, bold=True))
            linha.addLayout(item, 1)
        layout.addLayout(linha)
        self.conteudo.addWidget(box)

    def vazio(self, titulo, descricao):
        box, layout = caixa(16)
        layout.addWidget(texto(titulo, 12, bold=True))
        label = texto(descricao, 10, C["muted"])
        label.setWordWrap(True)
        layout.addWidget(label)
        self.conteudo.addWidget(box)
        self.conteudo.addStretch()

    def adicionar_tabela(self, colunas, linhas):
        self.modelo = ModeloDetalhe(colunas, linhas, self)
        table = W.QTableView()
        table.setAccessibleName(self.windowTitle().split(" — ")[0])
        table.setModel(self.modelo)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(36)
        h = table.horizontalHeader()
        h.setStretchLastSection(False)
        for i, c in enumerate(colunas):
            h.setSectionResizeMode(
                i,
                (
                    W.QHeaderView.ResizeMode.Stretch
                    if c.ampla
                    else W.QHeaderView.ResizeMode.ResizeToContents
                ),
            )
        table.setMinimumHeight(170)
        h.setSortIndicator(-1, Q.Qt.SortOrder.AscendingOrder)
        table.setSortingEnabled(True)
        self.conteudo.addWidget(table, 1)
        self.tabela = table
        self.setTabOrder(table, self.fechar)
        self.resize(
            self.width(), min(self.height(), max(400, 300 + min(len(linhas), 8) * 36))
        )
        return table


def janela_vendas(
    parent, rows, intervalo, titulo="Vendas da consulta completa", semana=False
):
    # Copiar o snapshot impede a ordenação do detalhe de reordenar o histórico.
    rows = list(rows)
    d = JanelaDetalhe(
        parent,
        titulo,
        contexto(intervalo),
        icone="calendar-days" if semana else "list",
        compacta=semana and not rows,
        explicacao=(
            "Semana: segunda-feira até hoje, sem vendas futuras e independente dos filtros."
            if semana
            else "Todos os registros da consulta aplicada, sem limitar à página visível. Campos ainda não aplicados não alteram este detalhe."
        ),
    )
    d.resumo(
        [
            (
                "Total da semana" if semana else "Total da consulta",
                moeda(sum(r.total for r in rows)),
            ),
            ("Dias registrados" if semana else "Registros", str(len(rows))),
        ]
    )
    if not rows:
        d.vazio(
            "Nenhuma venda nesta semana" if semana else "Nenhuma venda nesta consulta",
            (
                "A semana considera segunda-feira até hoje. Os filtros do histórico não alteram este resultado."
                if semana
                else "Não há registros nos filtros aplicados. Volte ao histórico para alterar a consulta."
            ),
        )
        return d
    if semana:
        d.resumo(
            [
                (s, moeda(sum(getattr(r, k) for r in rows)))
                for s, k in [
                    ("Dinheiro", "dinheiro"),
                    ("Pix", "pix"),
                    ("Cartão", "cartao"),
                ]
            ]
        )
    colunas = [
        Coluna("ID", "numero"),
        Coluna("Data", "data"),
        Coluna("Dia da semana", ampla=True),
        Coluna("Dinheiro", "moeda"),
        Coluna("Pix", "moeda"),
        Coluna("Cartão", "moeda"),
        Coluna("Total", "moeda"),
    ]
    d.adicionar_tabela(
        colunas,
        [
            (r.id, r.data, DIAS[r.data.weekday()], r.dinheiro, r.pix, r.cartao, r.total)
            for r in rows
        ],
    )
    return d


def janela_dias(parent, rows, intervalo):
    rows = list(rows)
    d = JanelaDetalhe(
        parent,
        "Resultados por dia da semana",
        contexto(intervalo),
        "calendar-days",
        explicacao="Cada barra é proporcional ao maior total por dia da semana nesta consulta. Dias zerados contam se há registro; ausência de registro tem quantidade zero. Não é uma participação percentual.",
    )
    d.resumo(
        [
            ("Total da consulta", moeda(sum(r.total for r in rows))),
            ("Dias registrados", len(rows)),
        ]
    )
    totais = [sum(r.total for r in rows if r.data.weekday() == i) for i in range(7)]
    d.barras = []
    d.dias_dados = []
    box, layout = caixa(14)
    layout.setSpacing(6)
    for i, nome in enumerate(DIAS):
        valor = totais[i]
        quantidade = sum(r.data.weekday() == i for r in rows)
        linha = W.QGridLayout()
        linha.setColumnStretch(1, 1)
        linha.setHorizontalSpacing(12)
        label = texto(nome, 10)
        label.setMinimumWidth(100)
        linha.addWidget(label, 0, 0)
        barra = W.QProgressBar()
        barra.setRange(0, 1000)
        barra.setValue(dividir(valor * 1000, max(totais)) if max(totais) > 0 else 0)
        barra.setTextVisible(False)
        barra.setFixedHeight(10)
        barra.setStyleSheet(
            estilo(
                "QProgressBar{background:@field@;border:0;border-radius:4px;}QProgressBar::chunk{background:@turquoise@;border-radius:4px;}"
            )
        )
        barra.setAccessibleName(
            nome + ": " + moeda(valor) + f", {quantidade} dias registrados"
        )
        linha.addWidget(barra, 0, 1)
        v = texto(moeda(valor), 11, bold=True)
        v.setMinimumWidth(110)
        v.setAlignment(Q.Qt.AlignmentFlag.AlignRight)
        linha.addWidget(v, 0, 2)
        c = texto(
            f"{quantidade} {'dia registrado' if quantidade==1 else 'dias registrados'}",
            9,
            C["muted"],
        )
        linha.addWidget(c, 1, 0, 1, 3)
        linha.setVerticalSpacing(2)
        layout.addLayout(linha)
        d.barras.append(barra)
        d.dias_dados.append((nome, valor, quantidade))
    d.conteudo.addWidget(box)
    d.conteudo.addStretch()
    return d


def janela_despesas(parent, rows, intervalo):
    # Mesmo recorte e exclusão de taxas do método anterior da demonstração.
    rows = [r for r in rows if not r.taxa]
    d = JanelaDetalhe(
        parent,
        "Despesas por semana",
        contexto(intervalo),
        "calendar-days",
        explicacao="Agrupa pela data da fatura para crédito e pela data de pagamento para os demais meios. Inclui só despesas dentro da consulta financeira aplicada; taxas não entram nesta soma. Os intervalos das semanas podem ultrapassar o recorte, mas seus valores não.",
    )
    d.resumo(
        [
            ("Despesas da consulta", moeda(sum(r.valor for r in rows))),
            ("Lançamentos", len(rows)),
        ]
    )
    if not rows:
        d.vazio(
            "Nenhuma despesa nesta consulta",
            "A consulta financeira é independente dos filtros de Vendas.",
        )
        return d
    grupos = {}
    for r in rows:
        segunda = r.data - timedelta(days=r.data.weekday())
        grupos.setdefault(segunda, []).append(r)
    dados = [
        (dia, dia + timedelta(days=6), len(rs), sum(r.valor for r in rs))
        for dia, rs in sorted(grupos.items(), reverse=True)
    ]
    d.adicionar_tabela(
        [
            Coluna("Início da semana", "data"),
            Coluna("Fim da semana", "data"),
            Coluna("Lançamentos", "numero", True),
            Coluna("Despesas", "moeda"),
        ],
        dados,
    )
    nota = texto(
        "Semanas podem ser parciais: valores limitados à consulta financeira aplicada.",
        9,
        C["muted"],
    )
    nota.setWordWrap(True)
    d.conteudo.addWidget(nota)
    return d


def janela_texto(parent, titulo, linhas):
    """Notas e acessos demonstrativos permanecem notas, sem inventar registros."""
    d = JanelaDetalhe(
        parent,
        titulo,
        "Informações da demonstração Noturno",
        "circle-help",
        compacta=True,
    )
    box, layout = caixa(14)
    for linha in linhas:
        label = texto(str(linha), 10, C["muted"])
        label.setWordWrap(True)
        label.setTextFormat(Q.Qt.TextFormat.PlainText)
        layout.addWidget(label)
    d.conteudo.addWidget(box)
    d.conteudo.addStretch()
    return d


def janela_pagamentos(parent, rows, intervalo):
    rows = list(rows)
    total = sum(r.total for r in rows)
    d = JanelaDetalhe(parent, "Formas de pagamento", contexto(intervalo), "chart-pie")
    d.resumo([("Total da consulta", moeda(total)), ("Dias registrados", len(rows))])
    dados = []
    for nome, key in [("Dinheiro", "dinheiro"), ("Pix", "pix"), ("Cartão", "cartao")]:
        v = sum(getattr(r, key) for r in rows)
        percent = f"{v/total*100:.1f}%".replace(".", ",") if total else "—"
        dados.append((nome, v, percent))
    d.adicionar_tabela(
        [Coluna("Meio", ampla=True), Coluna("Valor", "moeda"), Coluna("Participação")],
        dados,
    )
    return d
