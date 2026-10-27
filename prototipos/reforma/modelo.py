"""Massa fictícia compartilhada: não importa a aplicação nem abre arquivos de dados."""

from collections import defaultdict
from datetime import date, timedelta
import sys

CORES = dict(
    fundo="#0F1929",
    painel="#1B2A40",
    borda="#31465F",
    texto="#E9F0FC",
    suave="#AABBD2",
    destaque="#42D5AD",
    botao="#148568",
    vermelho="#FFACB5",
)
FONTE = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"
# Datas e valores inventados para demonstrar a mesma tela nas duas ferramentas.
LINHAS = (
    (
        "2026-11-09",
        "Compra parcelada de equipamento",
        "Cartão de crédito",
        "Feira",
        24990,
        "2/4",
    ),
    ("2026-11-09", "Assinatura de serviço", "Cartão de crédito", "Casa", 2990, "—"),
    ("2026-11-07", "Material de embalagem", "Pix", "Feira", 7850, "—"),
    ("2026-10-30", "Transporte", "Dinheiro", "Feira", 4500, "—"),
    ("2026-10-26", "Compra de mercadorias", "Cartão de crédito", "Feira", 32800, "1/3"),
    ("2026-10-25", "Taxas da maquininha", "Desconto nas vendas", "Taxa", 1680, "—"),
    ("2026-10-24", "Conta de energia", "Pix", "Casa", 12860, "—"),
    (
        "2026-10-23",
        "Reposição de mercadorias",
        "Cartão de crédito",
        "Feira",
        18640,
        "—",
    ),
    ("2026-10-21", "Material de limpeza", "Dinheiro", "Casa", 3240, "—"),
    ("2026-10-19", "Conta de água", "Pix", "Casa", 7640, "—"),
    ("2026-10-16", "Transporte", "Dinheiro", "Feira", 4500, "—"),
    ("2026-10-11", "Utensílios", "Cartão de crédito", "Casa", 11990, "3/6"),
)
VENDAS = (
    ("2026-10-11", 12500, 5400, 18600),
    ("2026-10-16", 8900, 4250, 17200),
    ("2026-10-18", 16000, 6200, 22400),
    ("2026-10-23", 11800, 7600, 18900),
    ("2026-10-25", 14500, 8900, 27500),
    ("2026-10-30", 0, 0, 0),
)
PERIODOS = ("Fechamento", "Mês", "Ano", "Semana")


def moeda(v):
    return "R$ " + f"{v / 100:,.2f}".replace(",", "_").replace(".", ",").replace(
        "_", "."
    )


def br(d):
    return date.fromisoformat(d).strftime("%d/%m/%Y")


def consultar(tipo="Fechamento"):
    limites = {
        "Fechamento": ("2026-10-10", "2026-11-09"),
        "Mês": ("2026-10-01", "2026-10-31"),
        "Ano": ("2026-01-01", "2026-12-31"),
        "Semana": ("2026-10-19", "2026-10-25"),
    }
    inicio, fim = limites[tipo]
    linhas = [r for r in LINHAS if inicio <= r[0] <= fim]
    vendas = [r for r in VENDAS if inicio <= r[0] <= fim]
    bruto = sum(sum(r[1:]) for r in vendas)
    taxas = sum(r[4] for r in linhas if r[3] == "Taxa")
    despesas = sum(r[4] for r in linhas if r[3] != "Taxa")
    saldo = bruto - taxas - despesas
    return dict(
        linhas=linhas,
        inicio=inicio,
        fim=fim,
        bruto=bruto,
        taxas=taxas,
        liquido=bruto - taxas,
        despesas=despesas,
        saldo=saldo,
        falta=max(0, -saldo),
    )


def semanas(linhas):
    totais = defaultdict(int)
    for r in linhas:
        if r[3] == "Taxa":
            continue
        dia = date.fromisoformat(r[0])
        segunda = dia - timedelta(days=dia.weekday())
        totais[segunda] += r[4]
    return [
        f"{d:%d/%m} a {d + timedelta(days=6):%d/%m}    {moeda(v)}"
        for d, v in sorted(totais.items(), reverse=True)
    ]


AJUDAS = {
    "saldo": "Vendas menos taxas e despesas cadastradas no período. Não é lucro nem saldo bancário. Inclui lançamentos futuros selecionados.",
    "meta": "Soma das despesas cadastradas na consulta. Contas e parcelas entram conforme sua data de pagamento.",
    "falta": "Quanto das despesas ainda não foi coberto pelas vendas após as taxas. Zero indica cobertura na simulação.",
    "taxas": "Descontos informados sobre as vendas. Não são despesas do cartão de compras. Taxa não cadastrada não significa isenção.",
    "consulta": "Nesta demonstração, os tipos consultam datas fixas de outubro de 2026. Não há conexão com seus dados.",
}


def indicadores_vendas():
    pagamentos = [sum(r[i] for r in VENDAS) for i in (1, 2, 3)]
    total = sum(pagamentos)
    return tuple(
        zip(
            (
                "TOTAL DO PERÍODO",
                "DIAS DE FEIRA",
                "MÉDIA POR DIA",
                "DINHEIRO",
                "PIX",
                "CARTÃO",
            ),
            (
                moeda(total),
                str(len(VENDAS)),
                moeda(round(total / len(VENDAS))),
                *(moeda(v) for v in pagamentos),
            ),
        )
    )


def resumo_semanal_vendas():
    grupos = defaultdict(list)
    for r in VENDAS:
        d = date.fromisoformat(r[0])
        grupos[d - timedelta(days=d.weekday())].append(r)
    return [
        f"{d:%d/%m} a {d+timedelta(days=6):%d/%m}     {len(rows)} {'dia de feira' if len(rows) == 1 else 'dias de feira'}      {moeda(sum(sum(r[1:]) for r in rows))}"
        for d, rows in sorted(grupos.items(), reverse=True)
    ]
