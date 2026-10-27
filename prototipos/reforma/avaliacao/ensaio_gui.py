"""Ensaio técnico equivalente. Nenhum módulo de produção, conta ou banco pessoal."""

import argparse
from collections import defaultdict
from contextlib import closing
from datetime import date, timedelta
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
import psutil

FONTE = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def memoria():
    return psutil.Process().memory_info().rss


def base(c, n):
    c.executescript(
        "CREATE TABLE vendas(id INTEGER PRIMARY KEY,data TEXT UNIQUE,dinheiro INTEGER,pix INTEGER,cartao INTEGER);CREATE TABLE despesas(id INTEGER PRIMARY KEY,data TEXT,valor INTEGER);"
    )
    hoje = date(2026, 10, 26)
    c.executemany(
        "INSERT INTO vendas VALUES(?,?,?,?,?)",
        [
            (
                i,
                str(hoje - timedelta(days=i)),
                i % 17 * 100 + 8000,
                i % 11 * 100 + 3000,
                i % 23 * 100 + 4000,
            )
            for i in range(n)
        ],
    )
    c.executemany(
        "INSERT INTO despesas VALUES(?,?,?)",
        [(i, str(hoje - timedelta(days=i)), 1234 + i % 7) for i in range(0, n, 3)],
    )
    c.commit()


def dados(c, pagina, inicio="0001-01-01"):
    vendas = c.execute(
        "SELECT id,data,dinheiro,pix,cartao FROM vendas WHERE data>=? ORDER BY data DESC",
        (inicio,),
    ).fetchall()
    if pagina == "Vendas":
        return ["Data", "Dinheiro", "Pix", "Cartão", "Total"], [
            (r[1], r[2], r[3], r[4], sum(r[2:])) for r in vendas
        ]
    if pagina == "Análises":
        grupos = defaultdict(list)
        for r in vendas:
            d = date.fromisoformat(r[1])
            grupos[str(d - timedelta(days=d.weekday()))].append(r)
        return ["Semana", "Dias", "Dinheiro", "Pix", "Cartão", "Total"], [
            (
                d,
                len(rs),
                *(sum(r[i] for r in rs) for i in (2, 3, 4)),
                sum(sum(r[2:]) for r in rs),
            )
            for d, rs in sorted(grupos.items(), reverse=True)
        ]
    despesas = c.execute(
        "SELECT data,valor FROM despesas WHERE data>=? ORDER BY data DESC", (inicio,)
    ).fetchall()
    return ["Data", "Descrição", "Meio", "Categoria", "Valor"], [
        (d, "Despesa fictícia", "Pix", "Feira", v) for d, v in despesas
    ]


def formatar(headers, rows):
    def valor(v):
        return "R$ " + f"{v/100:,.2f}".replace(",", "_").replace(".", ",").replace(
            "_", "."
        )

    return [
        [
            valor(v) if isinstance(v, int) and headers[i] not in ("Dias",) else str(v)
            for i, v in enumerate(row)
        ]
        for row in rows
    ]


class TkAdapter:
    def __init__(self, escala):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.geometry(f"{round(1280*escala)}x{round(800*escala)}")
        self.root.title("Estudo técnico — Tkinter")
        self.root.tk.call("tk", "scaling", 96 / 72 * escala)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Treeview", font=(FONTE, 10), rowheight=round(30 * escala))
        style.configure("Treeview.Heading", font=(FONTE, 10, "bold"))
        self.root.option_add("*Font", (FONTE, 10))
        self.paginas = {}
        self.current = None
        nav = ttk.Frame(self.root)
        nav.pack(fill="x", padx=20, pady=12)
        self.buttons = []
        for nome in ("Vendas", "Análises", "Finanças"):
            b = ttk.Button(nav, text=nome, command=lambda n=nome: self.show(n))
            b.pack(side="left", padx=6)
            self.buttons.append(b)
        self.area = ttk.Frame(self.root)
        self.area.pack(fill="both", expand=True, padx=20, pady=12)
        self.tick_delays = []
        self.expected = time.perf_counter() + 0.01
        self.root.after(10, self.tick)

    def tick(self):
        now = time.perf_counter()
        self.tick_delays.append(max(0, (now - self.expected) * 1000))
        self.expected = now + 0.01
        self.root.after(10, self.tick)

    def pump(self):
        self.root.update_idletasks()
        self.root.update()

    def table(self, parent, headers, rows):
        t = self.ttk.Treeview(
            parent,
            columns=list(range(len(headers))),
            show="headings",
            selectmode="browse",
            takefocus=True,
        )
        for i, h in enumerate(headers):
            t.heading(i, text=h)
            t.column(
                i,
                width=140,
                anchor=(
                    "e" if h in ("Dinheiro", "Pix", "Cartão", "Total", "Valor") else "w"
                ),
            )
        t.pack(fill="both", expand=True)
        self.fill(t, headers, rows)
        return t

    def fill(self, t, headers, rows):
        t.delete(*t.get_children())
        for row in formatar(headers, rows):
            t.insert("", "end", values=row)

    def show(self, nome, headers=None, rows=None):
        if self.current:
            self.paginas[self.current][0].pack_forget()
        if nome not in self.paginas:
            f = self.ttk.Frame(self.area)
            t = self.table(f, headers, rows)
            self.paginas[nome] = (f, t)
        elif rows is not None:
            self.fill(self.paginas[nome][1], headers, rows)
        self.paginas[nome][0].pack(fill="both", expand=True)
        self.current = nome

    def detail(self, headers, rows):
        d = self.tk.Toplevel(self.root)
        d.title("Consulta fictícia")
        d.geometry("900x500")
        self.table(d, headers, rows)
        self.pump()
        d.destroy()

    def keyboard(self):
        t = self.paginas[self.current][1]
        ids = t.get_children()
        t.focus_force()
        t.selection_set(ids[0])
        t.focus(ids[0])
        self.pump()
        t.event_generate("<Down>")
        self.pump()
        return dict(
            tecla="Down",
            selecao=t.focus() == ids[min(1, len(ids) - 1)],
            foco=t.focus_get() == t,
            takefocus=str(t.cget("takefocus")),
        )

    def acessibilidade(self):
        return dict(
            ponte="Tk/ttk; exige validação UIA e leitor de tela no Windows",
            nome_janela=self.root.title(),
            cabecalhos=True,
        )

    def hwnd(self):
        return self.root.winfo_id()

    def tamanho(self):
        return [self.root.winfo_width(), self.root.winfo_height()]

    def close(self):
        self.root.destroy()


class QtAdapter:
    def __init__(self, escala):
        from PySide6 import QtCore, QtGui, QtWidgets, QtSvg

        self.Q = QtCore
        self.G = QtGui
        self.W = QtWidgets
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self.app.setStyle("Fusion")
        self.app.setFont(QtGui.QFont(FONTE, 10))
        self.root = QtWidgets.QWidget()
        self.root.resize(1280, 800)
        self.root.setWindowTitle("Estudo técnico — PySide6")
        l = QtWidgets.QVBoxLayout(self.root)
        l.setContentsMargins(20, 12, 20, 12)
        nav = QtWidgets.QHBoxLayout()
        self.buttons = []
        for nome in ("Vendas", "Análises", "Finanças"):
            b = QtWidgets.QPushButton(nome)
            b.setAccessibleName(nome)
            b.clicked.connect(lambda checked=False, n=nome: self.show(n))
            nav.addWidget(b)
            self.buttons.append(b)
        nav.addStretch()
        l.addLayout(nav)
        self.area = QtWidgets.QStackedWidget()
        l.addWidget(self.area, 1)
        self.paginas = {}
        self.current = None
        self.tick_delays = []
        self.expected = time.perf_counter() + 0.01
        self.timer = QtCore.QTimer(self.root)
        self.timer.timeout.connect(self.tick)
        self.timer.start(10)
        self.root.show()

    def tick(self):
        now = time.perf_counter()
        self.tick_delays.append(max(0, (now - self.expected) * 1000))
        self.expected = now + 0.01

    def pump(self):
        self.app.processEvents()
        self.Q.QCoreApplication.sendPostedEvents(
            None, self.Q.QEvent.Type.DeferredDelete
        )

    def table(self, parent, headers, rows):
        W = self.W
        Q = self.Q

        class Model(Q.QAbstractTableModel):
            def __init__(self, headers, rows, parent=None):
                super().__init__(parent)
                self.headers = headers
                self.rows = formatar(headers, rows)

            def rowCount(self, parent=Q.QModelIndex()):
                return 0 if parent.isValid() else len(self.rows)

            def columnCount(self, parent=Q.QModelIndex()):
                return 0 if parent.isValid() else len(self.headers)

            def data(self, index, role=Q.Qt.ItemDataRole.DisplayRole):
                if index.isValid() and role in (
                    Q.Qt.ItemDataRole.DisplayRole,
                    Q.Qt.ItemDataRole.AccessibleTextRole,
                ):
                    return self.rows[index.row()][index.column()]
                return None

            def headerData(self, n, o, role=Q.Qt.ItemDataRole.DisplayRole):
                return (
                    self.headers[n]
                    if o == Q.Qt.Orientation.Horizontal
                    and role == Q.Qt.ItemDataRole.DisplayRole
                    else None
                )

        t = W.QTableView(parent)
        t.setAccessibleName("Tabela de registros fictícios")
        t.setModel(Model(headers, rows, t))
        t.verticalHeader().setDefaultSectionSize(30)
        t.verticalHeader().hide()
        t.horizontalHeader().setSectionResizeMode(W.QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
        return t

    def fill(self, t, headers, rows):
        m = t.model()
        m.beginResetModel()
        m.headers = headers
        m.rows = formatar(headers, rows)
        m.endResetModel()

    def show(self, nome, headers=None, rows=None):
        if nome not in self.paginas:
            page = self.W.QWidget()
            l = self.W.QVBoxLayout(page)
            l.setContentsMargins(0, 0, 0, 0)
            t = self.table(page, headers, rows)
            l.addWidget(t)
            self.paginas[nome] = (page, t)
            self.area.addWidget(page)
        elif rows is not None:
            self.fill(self.paginas[nome][1], headers, rows)
        self.area.setCurrentWidget(self.paginas[nome][0])
        self.current = nome

    def detail(self, headers, rows):
        d = self.W.QDialog(self.root)
        d.resize(900, 500)
        l = self.W.QVBoxLayout(d)
        l.addWidget(self.table(d, headers, rows))
        d.show()
        self.pump()
        d.close()
        d.deleteLater()
        self.pump()

    def keyboard(self):
        self.root.activateWindow()
        self.pump()
        t = self.paginas[self.current][1]
        t.setFocus()
        t.selectRow(0)
        self.pump()
        self.app.sendEvent(
            t,
            self.G.QKeyEvent(
                self.Q.QEvent.Type.KeyPress,
                self.Q.Qt.Key.Key_Down,
                self.Q.Qt.KeyboardModifier.NoModifier,
            ),
        )
        self.app.sendEvent(
            t,
            self.G.QKeyEvent(
                self.Q.QEvent.Type.KeyRelease,
                self.Q.Qt.Key.Key_Down,
                self.Q.Qt.KeyboardModifier.NoModifier,
            ),
        )
        self.pump()
        return dict(
            tecla="Down",
            selecao=t.currentIndex().row() == min(1, t.model().rowCount() - 1),
            foco=t.hasFocus(),
            nome=t.accessibleName(),
        )

    def acessibilidade(self):
        t = self.paginas[self.current][1]
        iface = self.G.QAccessible.queryAccessibleInterface(t)
        return dict(
            ponte="QAccessible; não substitui UIA/NVDA",
            interface=bool(iface),
            role=str(iface.role()) if iface else None,
            nome=iface.text(self.G.QAccessible.Text.Name) if iface else None,
        )

    def hwnd(self):
        return int(self.root.winId())

    def tamanho(self):
        return [self.root.width(), self.root.height()]

    def close(self):
        self.timer.stop()
        self.root.close()
        self.pump()


def probe_uia(adapter):
    if sys.platform != "win32":
        return dict(disponivel=False, motivo="UI Automation somente no Windows")
    import ctypes
    import subprocess

    ctypes.windll.user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    ctypes.windll.user32.GetAncestor.restype = ctypes.c_void_p
    hwnd = int(ctypes.windll.user32.GetAncestor(adapter.hwnd(), 2) or adapter.hwnd())
    script = """[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); Add-Type -AssemblyName UIAutomationClient; Add-Type -AssemblyName UIAutomationTypes;
$r=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]HWND);
$x=$r.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition);
$out=@();for($i=0;$i -lt [Math]::Min($x.Count,200);$i++){$c=$x[$i].Current;$out+=@{tipo=$c.ControlType.ProgrammaticName;nome=$c.Name;foco=$c.IsKeyboardFocusable}};
@{janela=$r.Current.Name;total=$x.Count;elementos=$out}|ConvertTo-Json -Depth 5 -Compress""".replace(
        "HWND", str(hwnd)
    )
    with tempfile.TemporaryDirectory(prefix="feira-uia-") as temp:
        arq = Path(temp) / "probe.ps1"
        arq.write_text(script, encoding="utf-8-sig")
        out_path = Path(temp) / "out.txt"
        err_path = Path(temp) / "err.txt"
        with out_path.open("w", encoding="utf-8") as stdout, err_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            proc = subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(arq),
                ],
                stdout=stdout,
                stderr=stderr,
            )
            prazo = time.monotonic() + 20
            while proc.poll() is None and time.monotonic() < prazo:
                adapter.pump()
                time.sleep(0.005)
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
        out = out_path.read_text(encoding="utf-8-sig", errors="replace")
        err = err_path.read_text(encoding="utf-8-sig", errors="replace")
        try:
            return dict(disponivel=proc.returncode == 0, resultado=json.loads(out))
        except ValueError:
            return dict(disponivel=False, motivo=(err or out)[-1000:])


def verificar_paletas(adapter):
    import ast

    path = Path(__file__).resolve().parents[3] / "ProgramFeira/interface/visual.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    paletas = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "PALETAS":
                paletas.update(ast.literal_eval(node.value))
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "PALETAS"
            ):
                paletas[ast.literal_eval(target.slice)] = ast.literal_eval(node.value)
    result = []

    def contraste(a, b):
        def lum(x):
            v = [int(x[i : i + 2], 16) / 255 for i in (1, 3, 5)]
            v = [n / 12.92 if n <= 0.04045 else ((n + 0.055) / 1.055) ** 2.4 for n in v]
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

        x, y = sorted([lum(a), lum(b)])
        return round((y + 0.05) / (x + 0.05), 2)

    for nome, p in paletas.items():
        if isinstance(adapter, TkAdapter):
            style = adapter.ttk.Style(adapter.root)
            adapter.root.configure(bg=p["fundo"])
            style.configure("TFrame", background=p["fundo"])
            style.configure(
                "TButton", foreground=p["texto"], background=p["superficie"]
            )
            style.configure(
                "Treeview",
                background=p["superficie"],
                fieldbackground=p["superficie"],
                foreground=p["texto"],
            )
            style.configure(
                "Treeview.Heading", background=p["cabecalho"], foreground=p["texto"]
            )
            style.map(
                "Treeview",
                background=[("selected", p["selecionado"])],
                foreground=[("selected", p["texto_selecionado"])],
            )
        else:
            adapter.app.setStyleSheet(
                f'QWidget{{background:{p["fundo"]};color:{p["texto"]};}} QTableView{{background:{p["superficie"]};alternate-background-color:{p["alternada"]};color:{p["texto"]};selection-background-color:{p["selecionado"]};selection-color:{p["texto_selecionado"]};}} QHeaderView::section{{background:{p["cabecalho"]};color:{p["texto"]};}} QPushButton{{background:{p["superficie"]};color:{p["texto"]};padding:8px;}}'
            )
        adapter.pump()
        result.append(
            dict(
                tema=nome,
                texto_sobre_superficie=contraste(p["texto"], p["superficie"]),
                secundario_sobre_superficie=contraste(p["muted"], p["superficie"]),
                selecao=contraste(p["texto_selecionado"], p["selecionado"]),
                observacao="Renderização da paleta no cenário técnico; não equivalência dos cinco temas na futura interface.",
            )
        )
    return result


def executar(ferramenta):
    p = argparse.ArgumentParser()
    p.add_argument("--volume", type=int, default=224)
    p.add_argument("--saida", required=True)
    p.add_argument("--ciclos", type=int, default=40)
    p.add_argument("--escala", type=float, default=1)
    p.add_argument("--uia", action="store_true")
    p.add_argument("--visual", action="store_true")
    args = p.parse_args()
    if not 1 <= args.volume <= 10000 or not 1 <= args.ciclos <= 200:
        raise SystemExit("Limites do estudo inválidos")
    peak = [memoria()]
    stop = threading.Event()

    def monitor():
        while not stop.wait(0.01):
            peak[0] = max(peak[0], memoria())

    th = threading.Thread(target=monitor, daemon=True)
    th.start()
    try:
        with tempfile.TemporaryDirectory(prefix="feira-tecnico-") as tmp, closing(
            sqlite3.connect(str(Path(tmp) / "ficticio.db"))
        ) as c:
            base(c, args.volume)
            h, rows = dados(c, "Vendas")
            digest = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
            inicio = time.perf_counter()
            a = TkAdapter(args.escala) if ferramenta == "tk" else QtAdapter(args.escala)
            a.show("Vendas", h, rows[:50])
            a.pump()
            abertura = (time.perf_counter() - inicio) * 1000
            inicial = memoria()
            medidas = defaultdict(list)

            def medir(nome, acao):
                t = time.perf_counter()
                result = acao()
                if not nome.startswith("consulta_"):
                    a.pump()
                medidas[nome].append((time.perf_counter() - t) * 1000)
                return result

            for pagina in ("Análises", "Finanças"):
                h1, r1 = medir("consulta_" + pagina, lambda p=pagina: dados(c, p))
                medir(
                    "primeira_" + pagina,
                    lambda p=pagina, h=h1, r=r1: a.show(p, h, r[:50]),
                )
            medir("consulta_todas", lambda: dados(c, "Vendas"))
            medir("tabela_completa", lambda: a.show("Vendas", h, rows))
            medir("retorno_paginado", lambda: a.show("Vendas", h, rows[:50]))
            depois_carga = memoria()
            memoria_ciclos = []
            for ciclo in range(args.ciclos):
                h2, r2 = medir("consulta_mes", lambda: dados(c, "Vendas", "2026-10-01"))
                medir("aplicar_mes", lambda: a.show("Vendas", h2, r2[:50]))
                medir("aplicar_todas", lambda: a.show("Vendas", h, rows[:50]))
                for pagina in ("Análises", "Finanças", "Vendas"):
                    medir("navegacao_" + pagina, lambda p=pagina: a.show(p))
                medir("abrir_fechar_detalhe", lambda: a.detail(h, rows[:50]))
                if (ciclo + 1) % 5 == 0:
                    memoria_ciclos.append(dict(ciclo=ciclo + 1, rss=memoria()))
            for _ in range(30):
                a.pump()
                time.sleep(0.005)
            gc.collect()
            a.pump()
            final = memoria()
            vivos = (
                len(a.root.findChildren(a.W.QDialog))
                if ferramenta == "qt"
                else sum(isinstance(w, a.tk.Toplevel) for w in a.root.winfo_children())
            )
            assert vivos == 0, "Diálogos pendentes no ensaio"
            keyboard = a.keyboard()
            access = a.acessibilidade()
            uia = probe_uia(a) if args.uia else None
            visual = verificar_paletas(a) if args.visual else None
            versao = (
                a.root.tk.call("info", "patchlevel")
                if ferramenta == "tk"
                else a.Q.__version__
            )
            timings = {
                k: dict(
                    n=len(v),
                    mediana_ms=round(statistics.median(v), 3),
                    p95_ms=round(
                        sorted(v)[max(0, __import__("math").ceil(len(v) * 0.95) - 1)], 3
                    ),
                    max_ms=round(max(v), 3),
                )
                for k, v in medidas.items()
            }
            so_peak = getattr(psutil.Process().memory_info(), "peak_wset", None)
            if so_peak is None:
                try:
                    import resource

                    so_peak = (
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
                        if sys.platform != "darwin"
                        else resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    )
                except ImportError:
                    pass
            result = dict(
                ferramenta=ferramenta,
                plataforma=sys.platform,
                python=platform.python_version(),
                biblioteca=versao,
                sqlite=sqlite3.sqlite_version,
                frozen=bool(getattr(sys, "frozen", False)),
                volume=args.volume,
                ciclos=args.ciclos,
                escala=args.escala,
                janela=a.tamanho(),
                fonte=FONTE,
                sha_dados=digest,
                registros=len(rows),
                total_centavos=sum(r[-1] for r in rows),
                abertura_gui_ms=round(abertura, 3),
                rss_inicial=inicial,
                rss_pos_carga=depois_carga,
                rss_final=final,
                crescimento_ciclos=final - depois_carga,
                memoria_por_ciclo=memoria_ciclos,
                dialogos_vivos_apos_ciclos=vivos,
                pico_amostrado=max(peak[0], final),
                pico_processo_so=so_peak,
                atraso_heartbeat_max_ms=round(max(a.tick_delays or [0]), 3),
                tempos=timings,
                teclado=keyboard,
                acessibilidade=access,
                uia=uia,
                visual=visual,
            )
            a.close()
            Path(args.saida).write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    finally:
        stop.set()
        th.join(timeout=1)
