"""Protótipo isolado Qt/PySide6. Dados exclusivamente fictícios em memória."""

import time

INICIO = time.perf_counter()
import argparse
import json
import os
from pathlib import Path
import sys

if sys.platform != "win32":
    os.environ["QT_FONT_DPI"] = "96"
    os.environ["QT_SCALE_FACTOR"] = "1"
from PySide6 import QtCore, QtGui, QtWidgets as W
from modelo import (
    CORES as C,
    FONTE,
    PERIODOS,
    VENDAS,
    consultar,
    moeda,
    br,
    semanas,
    AJUDAS,
)

ESTILO = f"""
QWidget {{ background:{C['fundo']}; color:{C['texto']}; font-family:"{FONTE}"; font-size:10pt; }}
QLabel {{ background:transparent; }}
QLabel[muted="true"] {{ color:{C['suave']}; }}
QFrame[panel="true"] {{ background:{C['painel']}; border:1px solid {C['borda']}; border-radius:14px; }}
QPushButton {{ background:{C['painel']}; border:1px solid {C['borda']}; border-radius:9px; padding:9px 14px; font-weight:600; }}
QPushButton:hover {{ background:#2C3D55; }}
QPushButton:focus {{ border:1px solid {C['destaque']}; }}
QPushButton[primary="true"], QPushButton[active="true"] {{ background:{C['botao']}; color:white; }}
QComboBox {{ padding:8px 12px; background:{C['painel']}; border:1px solid {C['borda']}; border-radius:8px; min-width:130px; }}
QComboBox QAbstractItemView {{ background:{C['painel']}; selection-background-color:#24483F; }}
QTableWidget {{ background:{C['painel']}; alternate-background-color:#203047; border:0; gridline-color:{C['borda']}; selection-background-color:#24483F; }}
QTableWidget::item {{ padding:6px 10px; border-bottom:1px solid #26364D; }}
QHeaderView::section {{ background:#26364D; color:{C['suave']}; padding:12px 8px; border:0; font-size:9pt; font-weight:600; }}
QScrollBar:vertical {{ background:{C['painel']}; width:9px; margin:0; }}
QScrollBar::handle:vertical {{ background:#425B70; border-radius:4px; min-height:30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QToolTip {{ background:#26364D; color:white; border:1px solid {C['borda']}; padding:10px; }}
"""


def label(texto, tamanho=10, muted=False, bold=False):
    w = W.QLabel(texto)
    w.setProperty("muted", muted)
    w.setFont(
        QtGui.QFont(
            FONTE,
            tamanho,
            QtGui.QFont.Weight.Bold if bold else QtGui.QFont.Weight.Normal,
        )
    )
    # Fontes de título precisam prevalecer sobre a regra genérica da folha.
    w.setStyleSheet(f"font-size:{tamanho}pt;" + ("font-weight:600;" if bold else ""))
    return w


def botao(texto, acao, primary=False):
    w = W.QPushButton(texto)
    w.setProperty("primary", primary)
    w.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    w.clicked.connect(acao)
    return w


def painel():
    w = W.QFrame()
    w.setProperty("panel", True)
    l = W.QVBoxLayout(w)
    l.setContentsMargins(18, 18, 18, 18)
    l.setSpacing(14)
    return w, l


class Aplicativo(W.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestão da Feira — estudo PySide6")
        self.resize(1440, 960)
        self.setMinimumSize(980, 700)
        self.pages = {}
        self.nav = {}
        self.valores = {}
        self.layout = W.QVBoxLayout(self)
        self.layout.setContentsMargins(28, 20, 28, 12)
        self.layout.setSpacing(16)
        header = W.QHBoxLayout()
        header.setSpacing(12)
        icone = W.QLabel()
        icone.setPixmap(
            QtGui.QPixmap(
                str(Path(__file__).resolve().parents[2] / "web/public/icon-192.png")
            ).scaled(
                48,
                48,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )
        header.addWidget(icone)
        marca = W.QVBoxLayout()
        marca.setSpacing(3)
        marca.addWidget(label("Gestão da Feira", 25, bold=True))
        marca.addWidget(label("Suas feiras, seus resultados.", 10, True))
        header.addLayout(marca)
        header.addStretch()
        for nome in ("⚙", "Tema: Noite", "Exportar relatório", "+ Nova venda"):
            header.addWidget(
                botao(
                    nome,
                    lambda checked=False, n=nome: self.explicar(n),
                    nome == "+ Nova venda",
                )
            )
        self.layout.addLayout(header)
        self.superior = W.QWidget()
        self.superior_layout = W.QVBoxLayout(self.superior)
        self.superior_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.superior)
        nav = W.QHBoxLayout()
        nav.setSpacing(10)
        for nome in ("Vendas", "Análises", "Finanças"):
            b = botao(nome, lambda checked=False, n=nome: self.mostrar(n))
            nav.addWidget(b)
            self.nav[nome] = b
        nav.addStretch()
        nav.addWidget(label("ESTUDO DE INTERFACE · DADOS FICTÍCIOS", 9, True))
        self.layout.addLayout(nav)
        self.stack = W.QStackedWidget()
        self.layout.addWidget(self.stack, 1)
        self.layout.addWidget(
            label(
                "Demonstração isolada. Não há conexão com banco, nuvem ou Drive.",
                9,
                True,
            )
        )
        self.mostrar("Finanças")

    def explicar(self, nome):
        W.QMessageBox.information(
            self,
            nome,
            "Prévia de posicionamento. Esta ação permanece no plano de preservação; não está conectada ao programa neste protótipo.",
        )

    def mostrar(self, nome):
        if nome not in self.pages:
            p = W.QWidget()
            l = W.QVBoxLayout(p)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(12)
            {
                "Finanças": self.financas,
                "Vendas": self.vendas,
                "Análises": self.analises,
            }[nome](l)
            self.pages[nome] = p
            self.stack.addWidget(p)
        self.stack.setCurrentWidget(self.pages[nome])
        self.superior.setVisible(nome == "Vendas")
        for n, b in self.nav.items():
            b.setProperty("active", n == nome)
            b.style().unpolish(b)
            b.style().polish(b)

    def titulo(self, l, nome, sub):
        h = W.QVBoxLayout()
        h.setSpacing(4)
        h.addWidget(label(nome, 22, bold=True))
        h.addWidget(label(sub, 10, True))
        l.addLayout(h)

    def ajuda(self, chave):
        b = botao("?", lambda: self.detalhes("Como ler", [AJUDAS[chave]]))
        b.setFixedSize(24, 24)
        b.setStyleSheet("padding:0;font-size:9pt;")
        b.setToolTip(AJUDAS[chave])
        b.setAccessibleName("Ajuda: " + chave)
        return b

    def financas(self, l):
        consulta = W.QHBoxLayout()
        consulta.setSpacing(16)
        consulta.addWidget(label("Finanças", 22, bold=True))
        consulta.addStretch()
        self.periodo = W.QComboBox()
        self.periodo.addItems(PERIODOS)
        consulta.addWidget(self.periodo)
        consulta.addWidget(label("Outubro / 2026", 11, bold=True))
        consulta.addWidget(botao("Consultar", self.atualizar))
        consulta.addWidget(self.ajuda("consulta"))
        l.addLayout(consulta)
        self.intervalo = label("", 10, True)
        l.addWidget(self.intervalo)
        indicadores = W.QHBoxLayout()
        indicadores.setSpacing(12)
        for chave, titulo, ajuda in (
            ("saldo", "Saldo após despesas", "saldo"),
            ("despesas", "Despesas a cobrir", "meta"),
            ("falta", "Falta cobrir", "falta"),
        ):
            w, c = painel()
            c.setContentsMargins(14, 14, 14, 14)
            c.setSpacing(8)
            h = W.QHBoxLayout()
            h.addWidget(label(titulo, 10, True))
            h.addStretch()
            h.addWidget(self.ajuda(ajuda))
            c.addLayout(h)
            v = label("", 25, bold=True)
            if chave == "saldo":
                v.setStyleSheet(
                    f'font-size:25pt;font-weight:600;color:{C["destaque"]};'
                )
            c.addWidget(v)
            self.valores[chave] = v
            indicadores.addWidget(w, 1)
        l.addLayout(indicadores)
        secundario = W.QHBoxLayout()
        self.secundario = label("", 10, True)
        secundario.addWidget(self.secundario)
        secundario.addStretch()
        secundario.addWidget(self.ajuda("taxas"))
        l.addLayout(secundario)
        w, c = painel()
        barra = W.QHBoxLayout()
        barra.addWidget(label("Lançamentos do período", 14, bold=True))
        barra.addStretch()
        barra.addWidget(
            botao("Taxas da maquininha", lambda: self.explicar("Taxas da maquininha"))
        )
        barra.addWidget(
            botao("+ Nova despesa", lambda: self.explicar("Nova despesa"), True)
        )
        c.addLayout(barra)
        self.tabela = W.QTableWidget(0, 7)
        self.tabela.setHorizontalHeaderLabels(
            (
                "Pagamento",
                "Tipo",
                "Descrição / compra",
                "Meio de pagamento",
                "Categoria",
                "Parcela",
                "Valor",
            )
        )
        self.tabela.verticalHeader().hide()
        self.tabela.verticalHeader().setDefaultSectionSize(39)
        self.tabela.setShowGrid(False)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setSelectionBehavior(
            W.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tabela.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        for i, wid in enumerate((120, 90, 350, 180, 90, 70, 125)):
            self.tabela.setColumnWidth(i, wid)
        self.tabela.horizontalHeader().setSectionResizeMode(
            2, W.QHeaderView.ResizeMode.Stretch
        )
        self.tabela.doubleClicked.connect(lambda _: self.explicar("Editar compra"))
        c.addWidget(self.tabela, 1)
        baixo = W.QHBoxLayout()
        self.contagem = label("", 9, True)
        baixo.addWidget(self.contagem)
        baixo.addStretch()
        for t in ("Editar compra", "Excluir"):
            baixo.addWidget(botao(t, lambda checked=False, n=t: self.explicar(n)))
        c.addLayout(baixo)
        l.addWidget(w, 1)
        links = W.QHBoxLayout()
        links.addWidget(
            botao(
                "Despesas por semana ↗",
                lambda: self.detalhes(
                    "Despesas por semana",
                    semanas(consultar(self.periodo.currentText())["linhas"]),
                ),
            )
        )
        links.addWidget(
            botao(
                "Histórico de taxas ↗",
                lambda: self.detalhes(
                    "Histórico de taxas",
                    [
                        "2025 · Exemplo de ajuste histórico confirmado",
                        "2026 · Exemplo de ajuste histórico estimado",
                        "O cadastro e suas proteções serão preservados na implementação.",
                    ],
                ),
            )
        )
        links.addStretch()
        links.addWidget(
            label("Valores brutos e despesas futuras: veja as ajudas.", 9, True)
        )
        l.addLayout(links)
        self.atualizar()

    def atualizar(self):
        r = consultar(self.periodo.currentText())
        self.intervalo.setText(f'{br(r["inicio"])} a {br(r["fim"])}')
        for chave in ("saldo", "despesas", "falta"):
            self.valores[chave].setText(moeda(r[chave]))
        self.secundario.setText(
            f'Vendas brutas  {moeda(r["bruto"])}     ·     Taxas  {moeda(r["taxas"])}     ·     Vendas menos taxas  {moeda(r["liquido"])}'
        )
        self.tabela.setRowCount(len(r["linhas"]))
        for i, registro in enumerate(r["linhas"]):
            valores = (
                br(registro[0]),
                "Taxa" if registro[3] == "Taxa" else "Despesa",
                registro[1],
                registro[2],
                registro[3],
                registro[5],
                moeda(registro[4]),
            )
            for j, valor in enumerate(valores):
                item = W.QTableWidgetItem(valor)
                item.setTextAlignment(
                    (
                        QtCore.Qt.AlignmentFlag.AlignLeft
                        if j == 2
                        else (
                            QtCore.Qt.AlignmentFlag.AlignRight
                            if j == 6
                            else QtCore.Qt.AlignmentFlag.AlignHCenter
                        )
                    )
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                )
                self.tabela.setItem(i, j, item)
        self.contagem.setText(
            f'{len(r["linhas"])} lançamentos · edição da compra inteira por qualquer parcela'
        )

    def detalhes(self, titulo, linhas):
        w = W.QDialog(self)
        w.setWindowTitle(titulo + " — demonstração")
        l = W.QVBoxLayout(w)
        l.setContentsMargins(24, 18, 24, 18)
        l.addWidget(label(titulo, 16, bold=True))
        for s in linhas:
            t = label(s, 11)
            t.setWordWrap(True)
            l.addWidget(t)
        l.addWidget(botao("Fechar", w.accept))
        w.resize(660, 250)
        w.exec()

    def vendas(self, l):
        if not self.superior_layout.count():
            from modelo import indicadores_vendas

            linha = W.QHBoxLayout()
            for titulo, valor in indicadores_vendas():
                w, c = painel()
                c.addWidget(label(titulo, 9, True))
                c.addWidget(label(valor, 17, bold=True))
                linha.addWidget(w, 1)
            self.superior_layout.addLayout(linha)
            self.superior_layout.addWidget(
                label(
                    "Semana atual · exemplo visual preservado; valores fictícios",
                    10,
                    True,
                )
            )
        self.titulo(
            l,
            "Histórico de vendas",
            "Estudo da organização inferior; os blocos superiores são referência do layout já aprovado.",
        )
        w, c = painel()
        c.addWidget(
            label(
                "Data                   Dinheiro                 Pix                 Cartão                 Total",
                12,
                bold=True,
            )
        )
        for r in VENDAS:
            c.addWidget(
                label(
                    f"{br(r[0])}            "
                    + "            ".join(moeda(v) for v in (*r[1:], sum(r[1:]))),
                    11,
                )
            )
        c.addStretch()
        c.addWidget(
            botao(
                "Filtros: ano, mês, fechamento e dias da semana",
                lambda: self.explicar("Filtros de Vendas"),
            )
        )
        l.addWidget(w, 1)

    def analises(self, l):
        self.titulo(
            l,
            "Análises",
            "Resultados por semana em primeiro plano. Consulta aplicada em Vendas: outubro de 2026.",
        )
        h = W.QHBoxLayout()
        h.addWidget(botao("Comparar A e B ↗", lambda: self.explicar("Comparar A e B")))
        h.addWidget(
            botao(
                "Detalhes do período ↗",
                lambda: self.explicar("Resumo, pagamentos, dias da semana e evolução"),
            )
        )
        h.addStretch()
        l.addLayout(h)
        w, c = painel()
        c.addWidget(label("Resultados por semana", 16, bold=True))
        from modelo import resumo_semanal_vendas

        for s in resumo_semanal_vendas():
            c.addWidget(label(s, 13))
        c.addWidget(
            label(
                "Estudo de hierarquia. Comparação e detalhes ainda não conectados aos cálculos reais.",
                10,
                True,
            )
        )
        c.addStretch()
        l.addWidget(w, 1)

    def testar(self):
        assert self.tabela.rowCount() == 12
        self.periodo.setCurrentText("Semana")
        self.atualizar()
        assert self.tabela.rowCount() == 5
        self.periodo.setCurrentText("Fechamento")
        self.atualizar()
        self.tabela.selectRow(2)
        self.mostrar("Análises")
        self.mostrar("Vendas")
        self.mostrar("Finanças")
        W.QApplication.processEvents()
        assert self.tabela.currentRow() == 2
        assert self.tabela.height() > 300


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--pagina", choices=("Finanças", "Vendas", "Análises"), default="Finanças"
    )
    p.add_argument("--captura")
    p.add_argument("--relatorio")
    p.add_argument("--testar", action="store_true")
    args = p.parse_args()
    app = W.QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setStyleSheet(ESTILO)
    janela = Aplicativo()
    janela.show()
    app.processEvents()
    visivel_ms = round((time.perf_counter() - INICIO) * 1000, 2)
    if args.relatorio:
        import psutil

        rss_mib = round(psutil.Process().memory_info().rss / 2**20, 2)
    if args.testar:
        janela.testar()
    janela.mostrar(args.pagina)
    app.processEvents()
    if args.captura:
        janela.grab().save(args.captura)
    if args.relatorio:
        import psutil

        Path(args.relatorio).write_text(
            json.dumps(
                dict(
                    ferramenta="PySide6",
                    abertura_ms=visivel_ms,
                    rss_mib=rss_mib,
                    linhas=12,
                    altura_tabela=janela.tabela.height(),
                    qt=QtCore.__version__,
                ),
                indent=2,
            )
        )
    if args.captura or args.testar:
        janela.close()
    else:
        sys.exit(app.exec())
