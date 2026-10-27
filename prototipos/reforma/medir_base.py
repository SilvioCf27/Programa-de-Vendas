"""Medições isoladas da aplicação estável. Cada repetição usa outro processo."""

import argparse
from contextlib import closing
from datetime import date, timedelta, datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def medir(n):
    with tempfile.TemporaryDirectory(prefix="feira-base-reforma-") as pasta:
        os.environ["PROGRAMFEIRA_DATA_DIR"] = pasta
        caminho = Path(pasta) / "vendas.db"
        shutil.copy2(ROOT / "ProgramFeira/assets/banco_inicial.db", caminho)
        hoje = date.today()
        with closing(sqlite3.connect(caminho)) as c, c:
            c.executemany(
                "INSERT INTO vendas(data,dinheiro,pix,cartao) VALUES(?,?,?,?)",
                ((str(hoje - timedelta(days=i)), 80, 30, 40) for i in range(n)),
            )
        sys.path.insert(0, str(ROOT))
        from ProgramFeira import financeiro as f

        f.inicializar()
        with closing(sqlite3.connect(caminho)) as c, c:
            c.executemany(
                "INSERT INTO financeiro_lancamentos(tipo,data,descricao,valor_centavos,meio,categoria) VALUES(?,?,?,?,?,?)",
                (
                    (
                        "despesa",
                        str(hoje - timedelta(days=i)),
                        "Exemplo fictício",
                        1234,
                        "Pix",
                        "Feira",
                    )
                    for i in range(0, n, 3)
                ),
            )
        import tkinter as tk

        inicio = time.perf_counter()
        # A pasta temporária não contém configuração ou sessão. Impede também
        # abrir a rede caso algum caminho passe a tentar fazê-lo no futuro.
        with patch.object(tk.Tk, "mainloop"), patch(
            "urllib.request.OpenerDirector.open",
            side_effect=AssertionError("Rede bloqueada no ensaio"),
        ):
            from ProgramFeira import main as a

            a.janela.update()
            abertura = (time.perf_counter() - inicio) * 1000
            eventos = []
            acumulado = {}

            def instrumentar(obj, nome, categoria):
                original = getattr(obj, nome)

                def chamada(*args, **kwargs):
                    t = time.perf_counter()
                    try:
                        return original(*args, **kwargs)
                    finally:
                        d = acumulado.setdefault(categoria, dict(chamadas=0, ms=0))
                        d["chamadas"] += 1
                        d["ms"] += (time.perf_counter() - t) * 1000

                setattr(obj, nome, chamada)

            instrumentar(a, "listar_vendas", "leitura_vendas")
            from ProgramFeira.database import banco

            instrumentar(banco, "listar_vendas", "leitura_vendas")
            instrumentar(a.painel_analises, "atualizar", "reconstrucao_analises")
            instrumentar(a, "ajustar_larguras_colunas", "dimensionamento_colunas")
            instrumentar(a, "montar_relatorio", "preparar_exportacao")
            instrumentar(a.tabela, "insert", "insercao_linhas")
            instrumentar(f, "resumo_periodo", "resumo_financeiro")
            instrumentar(f, "listar_lancamentos", "leitura_lancamentos")

            def evento(nome, acao):
                acumulado.clear()
                t = time.perf_counter()
                acao()
                a.janela.update()
                eventos.append(
                    dict(
                        cenario=nome,
                        ms=round((time.perf_counter() - t) * 1000, 3),
                        partes={
                            k: {"chamadas": v["chamadas"], "ms": round(v["ms"], 3)}
                            for k, v in acumulado.items()
                        },
                    )
                )

            evento("primeira_analises", lambda: a.abas.select(a.aba_analises))
            evento("primeira_financas", lambda: a.abas.select(a.painel_financeiro))
            evento("retorno_vendas", lambda: a.abas.select(a.aba_vendas))
            evento("retorno_analises", lambda: a.abas.select(a.aba_analises))
            evento("retorno_financas", lambda: a.abas.select(a.painel_financeiro))

            def ano():
                a.painel_financeiro.tipo.set("Ano")
                a.painel_financeiro.consultar()

            evento("financas_ano", ano)
            a.abas.select(a.aba_vendas)
            a.janela.update()
            evento("todas_as_vendas", a.limpar_filtros)
            evento("repetir_consulta_todas", a.atualizar_tabela)
            linhas = len(a.tabela.get_children())
            resultado = dict(
                referencia_dados=hoje.isoformat(),
                vendas=n,
                lancamentos=(n + 2) // 3,
                abertura_ms=round(abertura, 3),
                eventos=eventos,
                linhas_tabela_final=linhas,
                tk=a.janela.tk.call("info", "patchlevel"),
                janela=a.janela.winfo_geometry(),
                rede="bloqueada; nenhuma conta configurada",
            )
            a.janela.destroy()
            return resultado


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--filho", type=int)
    p.add_argument(
        "--saida", default=str(Path(__file__).with_name("BASE_MEDICOES.json"))
    )
    args = p.parse_args()
    if args.filho is not None:
        if not 0 <= args.filho <= 10000:
            raise SystemExit("Volume inválido")
        print(json.dumps(medir(args.filho)))
        raise SystemExit()
    resultados = []
    for volume in (224, 5000):
        for repeticao in range(1, 4):
            r = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--filho", str(volume)],
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
                cwd=ROOT,
            )
            item = json.loads(r.stdout)
            item["repeticao"] = repeticao
            resultados.append(item)
    saida = dict(
        data_utc=datetime.now(timezone.utc).isoformat(),
        plataforma=platform.system() + " " + platform.machine(),
        python=sys.version.split()[0],
        sqlite=sqlite3.sqlite_version,
        observacao="Linux com display virtual, não representa o PC Windows. Tempos de partes podem se sobrepor; não somar. Abertura inclui importação/montagem, mas não inicialização do processo Python.",
        resultados=resultados,
    )
    Path(args.saida).write_text(
        json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Medições gravadas:", args.saida)
