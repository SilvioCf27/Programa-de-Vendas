"""Ensaio Qt em processo separado; não substitui validação no Windows real."""

import argparse
import json
import os
from pathlib import Path
from PySide6 import QtWidgets as W
from noturno_demo import Aplicativo, preparar

p = argparse.ArgumentParser()
p.add_argument("--saida", required=True)
args = p.parse_args()
app = preparar()
janela = Aplicativo()
janela.show()
resultados = []
janelas = []
for largura, altura in [(1536, 1024), (1280, 800), (1000, 700)]:
    janela.resize(largura, altura)
    for area in ["Vendas", "Análises", "Finanças"]:
        janela.mostrar(area)
        for _ in range(12):
            app.processEvents()
        visao = janela.scroll.viewport()
        assert janela.scroll.widget().width() <= visao.width(), (area, largura)
        janela.grab()  # Exercita a pintura na escala escolhida.
        resultados.append(
            dict(
                area=area,
                largura_logica=largura,
                altura_logica=altura,
                viewport=visao.width(),
                conteudo=janela.scroll.widget().width(),
                rolagem_vertical=janela.scroll.verticalScrollBar().maximum(),
                dpr=janela.devicePixelRatioF(),
            )
        )
    for nome in ["vendas", "dias", "despesas", "semana"]:
        d = janela.criar_detalhe(nome)
        d.show()
        for _ in range(12):
            app.processEvents()
        assert d.corpo.width() <= d.scroll.viewport().width(), (nome, largura)
        assert d.fechar.isVisible()
        d.grab()
        janelas.append(
            dict(
                detalhe=nome,
                janela_principal=[largura, altura],
                dimensoes=d.size().toTuple(),
                viewport=d.scroll.viewport().width(),
                conteudo=d.corpo.width(),
                rolagem_vertical=d.scroll.verticalScrollBar().maximum(),
                dpr=d.devicePixelRatioF(),
            )
        )
        d.close()
        d.deleteLater()
        app.processEvents()
Path(args.saida).write_text(
    json.dumps(
        dict(
            plataforma="Linux / Qt offscreen; não é um ensaio Windows",
            escala=os.environ.get("QT_SCALE_FACTOR", "1"),
            cenarios=resultados,
            janelas_secundarias=janelas,
        ),
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
janela.close()
print(
    f"{len(resultados)} telas e {len(janelas)} janelas secundárias renderizadas sem corte horizontal externo; escala Qt "
    + os.environ.get("QT_SCALE_FACTOR", "1")
)
