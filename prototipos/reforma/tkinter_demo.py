"""Protótipo isolado Tkinter. Executar este arquivo não abre banco nem rede."""

import time

INICIO = time.perf_counter()
import argparse
import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
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


class Painel(tk.Frame):
    def __init__(self, parent, padding=18, **kwargs):
        super().__init__(parent, bg=C["fundo"], **kwargs)
        self.fundo = tk.Canvas(self, bg=C["fundo"], highlightthickness=0)
        self.fundo.place(x=0, y=0, relwidth=1, relheight=1)
        self.corpo = tk.Frame(self, bg=C["painel"])
        self.corpo.pack(fill="both", expand=True, padx=padding, pady=padding)
        self.bind("<Configure>", self.desenhar)

    def desenhar(self, event=None):
        w, h = self.winfo_width(), self.winfo_height()
        r = min(14, w // 2, h // 2)
        self.fundo.delete("all")
        self.fundo.create_polygon(
            1,
            r,
            1,
            1,
            r,
            1,
            w - r,
            1,
            w - 1,
            1,
            w - 1,
            r,
            w - 1,
            h - r,
            w - 1,
            h - 1,
            w - r,
            h - 1,
            r,
            h - 1,
            1,
            h - 1,
            1,
            h - r,
            smooth=True,
            fill=C["painel"],
            outline=C["borda"],
        )


def texto(p, s, tamanho=10, cor=None, bold=False, **kw):
    return tk.Label(
        p,
        text=s,
        bg=p.cget("bg"),
        fg=cor or C["texto"],
        font=(FONTE, tamanho, "bold" if bold else "normal"),
        anchor="w",
        **kw,
    )


def botao(p, s, comando, principal=False):
    return tk.Button(
        p,
        text=s,
        command=comando,
        bg=C["botao"] if principal else C["painel"],
        fg="white" if principal else C["texto"],
        activebackground="#225F56" if principal else "#2C3D55",
        activeforeground="white",
        bd=0,
        padx=14,
        pady=9,
        font=(FONTE, 10, "bold"),
        cursor="hand2",
        highlightthickness=1,
        highlightbackground=C["borda"],
    )


class Dica:
    def __init__(self, w, s):
        self.popup = None
        self.w = w
        self.s = s
        w.bind("<Enter>", self.mostrar)
        w.bind("<FocusIn>", self.mostrar)
        for e in ("<Leave>", "<FocusOut>", "<Destroy>"):
            w.bind(e, self.fechar)

    def mostrar(self, e=None):
        if self.popup:
            return
        self.popup = tk.Toplevel(self.w)
        self.popup.overrideredirect(True)
        self.popup.geometry(f"+{self.w.winfo_rootx()}+{self.w.winfo_rooty()+30}")
        texto(self.popup, self.s, 10, wraplength=350, padx=12, pady=12).pack()

    def fechar(self, e=None):
        if self.popup:
            self.popup.destroy()
            self.popup = None


class Aplicativo:
    def __init__(self):
        self.root = tk.Tk()
        if sys.platform != "win32":
            self.root.tk.call("tk", "scaling", 96 / 72)
        self.root.title("Gestão da Feira — estudo Tkinter")
        self.root.geometry("1440x960+0+0")
        self.root.minsize(980, 700)
        self.root.configure(bg=C["fundo"])
        self.root.option_add("*TCombobox*Listbox.background", C["painel"])
        self.root.option_add("*TCombobox*Listbox.foreground", C["texto"])
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure(
            "TCombobox",
            fieldbackground=C["painel"],
            background=C["painel"],
            foreground=C["texto"],
            padding=8,
            arrowsize=14,
        )
        st.map(
            "TCombobox",
            fieldbackground=[("readonly", C["painel"])],
            foreground=[("readonly", C["texto"])],
        )
        st.configure(
            "Treeview",
            background=C["painel"],
            fieldbackground=C["painel"],
            foreground=C["texto"],
            rowheight=39,
            font=(FONTE, 10),
            borderwidth=0,
        )
        st.configure(
            "Treeview.Heading",
            background="#26364D",
            foreground=C["suave"],
            font=(FONTE, 9, "bold"),
            padding=(8, 10),
            relief="flat",
        )
        st.map(
            "Treeview",
            background=[("selected", "#24483F")],
            foreground=[("selected", "white")],
        )
        st.configure(
            "Vertical.TScrollbar",
            background="#31465F",
            troughcolor=C["painel"],
            borderwidth=0,
            arrowsize=10,
        )
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)
        self.pages = {}
        self.nav = {}
        self.widgets = {}
        self.periodo = tk.StringVar(value="Fechamento")
        header = tk.Frame(self.root, bg=C["fundo"])
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 12))
        self.logo = tk.PhotoImage(
            file=str(Path(__file__).resolve().parents[2] / "web/public/icon-192.png")
        ).subsample(4)
        tk.Label(header, image=self.logo, bg=C["fundo"]).pack(side="left", padx=(0, 12))
        marca = tk.Frame(header, bg=C["fundo"])
        marca.pack(side="left")
        texto(marca, "Gestão da Feira", 25, bold=True).pack(anchor="w")
        texto(marca, "Suas feiras, seus resultados.", 10, C["suave"]).pack(
            anchor="w", pady=(3, 0)
        )
        for nome in ("+ Nova venda", "Exportar relatório", "Tema: Noite", "⚙"):
            botao(
                header, nome, lambda n=nome: self.explicar(n), nome == "+ Nova venda"
            ).pack(side="right", padx=(8, 0))
        self.superior = tk.Frame(self.root, bg=C["fundo"])
        self.superior.grid(row=1, column=0, sticky="ew", padx=28)
        nav = tk.Frame(self.root, bg=C["fundo"])
        nav.grid(row=2, column=0, sticky="ew", padx=28, pady=(10, 16))
        for nome in ("Vendas", "Análises", "Finanças"):
            b = botao(nav, nome, lambda n=nome: self.mostrar(n))
            b.pack(side="left", padx=(0, 10))
            self.nav[nome] = b
        texto(nav, "ESTUDO DE INTERFACE · DADOS FICTÍCIOS", 9, C["suave"]).pack(
            side="right"
        )
        self.area = tk.Frame(self.root, bg=C["fundo"])
        self.area.grid(row=3, column=0, sticky="nsew", padx=28)
        self.area.columnconfigure(0, weight=1)
        self.area.rowconfigure(0, weight=1)
        self.status = texto(
            self.root,
            "Demonstração isolada. Não há conexão com banco, nuvem ou Drive.",
            9,
            C["suave"],
        )
        self.status.grid(row=4, column=0, sticky="ew", padx=28, pady=12)
        self.mostrar("Finanças")

    def explicar(self, nome):
        messagebox.showinfo(
            nome,
            "Prévia de posicionamento. Esta ação permanece no plano de preservação; não está conectada ao programa neste protótipo.",
            parent=self.root,
        )

    def mostrar(self, nome):
        if nome not in self.pages:
            p = tk.Frame(self.area, bg=C["fundo"])
            p.grid(row=0, column=0, sticky="nsew")
            self.pages[nome] = p
            {
                "Finanças": self.financas,
                "Vendas": self.vendas,
                "Análises": self.analises,
            }[nome](p)
        self.pages[nome].tkraise()
        for n, b in self.nav.items():
            b.configure(bg=C["botao"] if n == nome else C["painel"])
        self.superior.grid() if nome == "Vendas" else self.superior.grid_remove()

    def titulo(self, p, nome, sub):
        h = tk.Frame(p, bg=C["fundo"])
        h.pack(fill="x", pady=(0, 14))
        texto(h, nome, 22, bold=True).pack(anchor="w")
        texto(h, sub, 10, C["suave"]).pack(anchor="w", pady=(4, 0))
        return h

    def ajuda(self, p, chave):
        b = botao(
            p,
            "?",
            lambda: messagebox.showinfo("Como ler", AJUDAS[chave], parent=self.root),
        )
        b.configure(padx=0, pady=0, width=2)
        b.pack(side="right")
        b.dica = Dica(b, AJUDAS[chave])

    def financas(self, p):
        cabecalho = tk.Frame(p, bg=C["fundo"])
        cabecalho.pack(fill="x", pady=(0, 6))
        texto(cabecalho, "Finanças", 22, bold=True).pack(side="left")
        consulta = tk.Frame(cabecalho, bg=C["fundo"])
        consulta.pack(side="right")
        ttk.Combobox(
            consulta,
            textvariable=self.periodo,
            values=PERIODOS,
            state="readonly",
            width=14,
        ).pack(side="left")
        texto(consulta, "Outubro / 2026", 11, bold=True).pack(side="left", padx=16)
        botao(consulta, "Consultar", self.atualizar).pack(side="left")
        self.ajuda(consulta, "consulta")
        self.intervalo = texto(p, "", 10, C["suave"])
        self.intervalo.pack(anchor="w", pady=(0, 12))
        indicadores = tk.Frame(p, bg=C["fundo"])
        indicadores.pack(fill="x", pady=(0, 8))
        for i, (chave, titulo, ajuda) in enumerate(
            (
                ("saldo", "Saldo após despesas", "saldo"),
                ("despesas", "Despesas a cobrir", "meta"),
                ("falta", "Falta cobrir", "falta"),
            )
        ):
            indicadores.columnconfigure(i, weight=1, uniform="resumo")
            caixa = Painel(indicadores, padding=14)
            caixa.grid(row=0, column=i, sticky="ew", padx=(0, 12 if i < 2 else 0))
            linha = tk.Frame(caixa.corpo, bg=C["painel"])
            linha.pack(fill="x")
            texto(linha, titulo, 10, C["suave"]).pack(side="left")
            self.ajuda(linha, ajuda)
            v = texto(
                caixa.corpo,
                "",
                25,
                C["destaque"] if chave == "saldo" else C["texto"],
                True,
            )
            v.pack(anchor="w", pady=(6, 0))
            self.widgets[chave] = v
        secundario = tk.Frame(p, bg=C["fundo"])
        secundario.pack(fill="x", pady=(0, 12))
        self.secundario = texto(secundario, "", 10, C["suave"])
        self.secundario.pack(side="left")
        self.ajuda(secundario, "taxas")
        caixa = Painel(p)
        caixa.pack(fill="both", expand=True)
        barra = tk.Frame(caixa.corpo, bg=C["painel"])
        barra.pack(fill="x", pady=(0, 14))
        texto(barra, "Lançamentos do período", 14, bold=True).pack(side="left")
        botao(
            barra, "+ Nova despesa", lambda: self.explicar("Nova despesa"), True
        ).pack(side="right")
        botao(
            barra, "Taxas da maquininha", lambda: self.explicar("Taxas da maquininha")
        ).pack(side="right", padx=8)
        corpo = tk.Frame(caixa.corpo, bg=C["painel"])
        corpo.pack(fill="both", expand=True)
        colunas = ("data", "tipo", "descricao", "meio", "categoria", "parcela", "valor")
        self.tabela = ttk.Treeview(
            corpo, columns=colunas, show="headings", selectmode="browse", height=10
        )
        for n, t, w in zip(
            colunas,
            (
                "Pagamento",
                "Tipo",
                "Descrição / compra",
                "Meio de pagamento",
                "Categoria",
                "Parcela",
                "Valor",
            ),
            (120, 90, 350, 180, 90, 70, 125),
        ):
            self.tabela.heading(n, text=t, anchor="w" if n == "descricao" else "center")
            self.tabela.column(
                n,
                width=w,
                minwidth=65,
                stretch=n == "descricao",
                anchor="w" if n == "descricao" else "e" if n == "valor" else "center",
            )
        self.tabela.tag_configure("alternada", background="#203047")
        self.tabela.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(corpo, orient="vertical", command=self.tabela.yview)
        scroll.pack(side="right", fill="y")
        self.tabela.configure(yscrollcommand=scroll.set)
        self.tabela.bind("<Double-1>", lambda e: self.explicar("Editar compra"))
        baixo = tk.Frame(caixa.corpo, bg=C["painel"])
        baixo.pack(side="bottom", fill="x", pady=(14, 0), before=corpo)
        self.contagem = texto(baixo, "", 9, C["suave"])
        self.contagem.pack(side="left")
        for t in ("Excluir", "Editar compra"):
            botao(baixo, t, lambda n=t: self.explicar(n)).pack(
                side="right", padx=(8, 0)
            )
        links = tk.Frame(p, bg=C["fundo"])
        links.pack(side="bottom", fill="x", pady=(12, 0), before=caixa)
        botao(
            links,
            "Despesas por semana ↗",
            lambda: self.detalhes(
                "Despesas por semana", semanas(consultar(self.periodo.get())["linhas"])
            ),
        ).pack(side="left")
        botao(
            links,
            "Histórico de taxas ↗",
            lambda: self.detalhes(
                "Histórico de taxas",
                [
                    "2025 · Exemplo de ajuste histórico confirmado",
                    "2026 · Exemplo de ajuste histórico estimado",
                    "O cadastro e suas proteções serão preservados na implementação.",
                ],
            ),
        ).pack(side="left", padx=10)
        texto(
            links, "Valores brutos e despesas futuras: veja as ajudas.", 9, C["suave"]
        ).pack(side="right")
        self.atualizar()

    def atualizar(self):
        r = consultar(self.periodo.get())
        self.intervalo.configure(text=f'{br(r["inicio"])} a {br(r["fim"])}')
        for k in ("saldo", "despesas", "falta"):
            self.widgets[k].configure(text=moeda(r[k]))
        self.secundario.configure(
            text=f'Vendas brutas  {moeda(r["bruto"])}     ·     Taxas  {moeda(r["taxas"])}     ·     Vendas menos taxas  {moeda(r["liquido"])}'
        )
        self.tabela.delete(*self.tabela.get_children())
        for i, r in enumerate(r["linhas"]):
            self.tabela.insert(
                "",
                "end",
                values=(
                    br(r[0]),
                    "Taxa" if r[3] == "Taxa" else "Despesa",
                    r[1],
                    r[2],
                    r[3],
                    r[5],
                    moeda(r[4]),
                ),
                tags=("alternada",) if i % 2 else (),
            )
        self.contagem.configure(
            text=f"{len(self.tabela.get_children())} lançamentos · edição da compra inteira por qualquer parcela"
        )

    def detalhes(self, titulo, linhas):
        w = tk.Toplevel(self.root)
        w.title(titulo + " — demonstração")
        w.configure(bg=C["painel"])
        w.transient(self.root)
        texto(w, titulo, 16, bold=True, padx=24, pady=18).pack(anchor="w")
        for s in linhas:
            texto(w, s, 11, padx=24, pady=8, wraplength=650).pack(anchor="w")
        botao(w, "Fechar", w.destroy).pack(anchor="e", padx=24, pady=18)

    def vendas(self, p):
        if not self.superior.winfo_children():
            from modelo import indicadores_vendas

            for i, (t, v) in enumerate(indicadores_vendas()):
                self.superior.columnconfigure(i, weight=1, uniform="cards")
                c = Painel(self.superior, 12)
                c.grid(row=0, column=i, sticky="ew", padx=(0, 8))
                texto(c.corpo, t, 9, C["suave"]).pack(anchor="w")
                texto(c.corpo, v, 17, bold=True).pack(anchor="w", pady=9)
            texto(
                self.superior,
                "Semana atual · exemplo visual preservado; valores fictícios",
                10,
                C["suave"],
            ).grid(row=1, column=0, columnspan=6, sticky="w", pady=12)
        self.titulo(
            p,
            "Histórico de vendas",
            "Estudo da organização inferior; os blocos superiores são referência do layout já aprovado.",
        )
        c = Painel(p)
        c.pack(fill="both", expand=True)
        texto(
            c.corpo,
            "Data                   Dinheiro                 Pix                 Cartão                 Total",
            12,
            bold=True,
        ).pack(anchor="w", pady=(0, 18))
        for r in VENDAS:
            texto(
                c.corpo,
                f"{br(r[0])}            "
                + "            ".join(moeda(v) for v in (*r[1:], sum(r[1:]))),
                11,
                pady=12,
            ).pack(anchor="w")
        botao(
            c.corpo,
            "Filtros: ano, mês, fechamento e dias da semana",
            lambda: self.explicar("Filtros de Vendas"),
        ).pack(anchor="e", pady=16)

    def analises(self, p):
        self.titulo(
            p,
            "Análises",
            "Resultados por semana em primeiro plano. Consulta aplicada em Vendas: outubro de 2026.",
        )
        barra = tk.Frame(p, bg=C["fundo"])
        barra.pack(fill="x", pady=(0, 16))
        botao(barra, "Comparar A e B ↗", lambda: self.explicar("Comparar A e B")).pack(
            side="left"
        )
        botao(
            barra,
            "Detalhes do período ↗",
            lambda: self.explicar("Resumo, pagamentos, dias da semana e evolução"),
        ).pack(side="left", padx=10)
        c = Painel(p)
        c.pack(fill="both", expand=True)
        texto(c.corpo, "Resultados por semana", 16, bold=True).pack(anchor="w")
        from modelo import resumo_semanal_vendas

        for s in resumo_semanal_vendas():
            texto(c.corpo, s, 13, pady=20).pack(anchor="w")
        texto(
            c.corpo,
            "Estudo de hierarquia. Comparação e detalhes ainda não conectados aos cálculos reais.",
            10,
            C["suave"],
        ).pack(anchor="w", pady=20)

    def testar(self):
        assert len(self.tabela.get_children()) == 12
        self.periodo.set("Semana")
        self.atualizar()
        assert len(self.tabela.get_children()) == 5
        self.periodo.set("Fechamento")
        self.atualizar()
        self.tabela.selection_set(self.tabela.get_children()[2])
        escolhido = self.tabela.selection()
        self.mostrar("Análises")
        self.mostrar("Vendas")
        self.mostrar("Finanças")
        self.root.update()
        assert self.tabela.selection() == escolhido
        assert self.tabela.winfo_height() > 300, dict(
            tabela=self.tabela.winfo_height(),
            janela=self.root.winfo_geometry(),
            area=self.area.winfo_height(),
            escala=self.root.tk.call("tk", "scaling"),
            superior=self.superior.winfo_ismapped(),
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--pagina", choices=("Finanças", "Vendas", "Análises"), default="Finanças"
    )
    p.add_argument("--captura")
    p.add_argument("--relatorio")
    p.add_argument("--testar", action="store_true")
    args = p.parse_args()
    app = Aplicativo()
    app.root.update()
    visivel_ms = round((time.perf_counter() - INICIO) * 1000, 2)
    if args.relatorio:
        import psutil

        rss_mib = round(psutil.Process().memory_info().rss / 2**20, 2)
    if args.testar:
        app.testar()
    app.mostrar(args.pagina)
    app.root.update()
    if args.captura:
        from PIL import ImageGrab

        x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
        ImageGrab.grab(
            bbox=(x, y, x + app.root.winfo_width(), y + app.root.winfo_height())
        ).save(args.captura)
    if args.relatorio:
        import psutil

        Path(args.relatorio).write_text(
            json.dumps(
                dict(
                    ferramenta="Tkinter",
                    abertura_ms=visivel_ms,
                    rss_mib=rss_mib,
                    linhas=12,
                    altura_tabela=app.tabela.winfo_height(),
                    tk=app.root.tk.call("info", "patchlevel"),
                ),
                indent=2,
            )
        )
    if args.captura or args.testar:
        app.root.destroy()
    else:
        app.root.mainloop()
