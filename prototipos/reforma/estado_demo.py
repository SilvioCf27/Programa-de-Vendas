"""Estado descartável da revisão Noturno. Sem arquivos de dados, rede ou aplicação real."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from modelo import LINHAS, VENDAS

HOJE = date(2026, 10, 26)  # Relógio fixo e declarado para uma revisão reproduzível.
DIAS = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)
MESES = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def dividir(valor, quantidade):
    return int(
        (Decimal(valor) / max(quantidade, 1)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def limites(tipo, ano=2026, mes=10, semana=0):
    inicio = date(ano, mes, 1)
    proximo = date(ano + (mes == 12), 1 if mes == 12 else mes + 1, 1)
    if tipo == "Todas":
        return date.min, date.max
    if tipo == "Ano":
        return date(ano, 1, 1), date(ano, 12, 31)
    if tipo == "Fechamento":
        return inicio.replace(day=10), proximo.replace(day=9)
    if tipo == "Semana":
        segunda = inicio - timedelta(days=inicio.weekday()) + timedelta(weeks=semana)
        return segunda, segunda + timedelta(days=6)
    return inicio, proximo - timedelta(days=1)


@dataclass(frozen=True)
class Venda:
    id: int
    data: date
    dinheiro: int
    pix: int
    cartao: int

    @property
    def total(self):
        return self.dinheiro + self.pix + self.cartao


@dataclass(frozen=True)
class Lancamento:
    id: int
    data: date  # Fatura para crédito; pagamento nos demais meios.
    compra: date | None
    descricao: str
    meio: str
    categoria: str
    valor: int
    parcela: str

    @property
    def taxa(self):
        return self.categoria == "Taxa"


class Estado:
    def __init__(self):
        anteriores = [
            ("2026-09-13", 22000, 15000, 31000),
            ("2026-09-20", 14000, 9000, 17000),
            ("2026-09-27", 16000, 11000, 15000),
        ]
        self.vendas = [
            Venda(i, date.fromisoformat(d), a, b, c)
            for i, (d, a, b, c) in enumerate(anteriores + list(VENDAS), 1)
        ]
        self.lancamentos = []
        compras = {
            0: "2026-09-09",
            1: "2026-10-21",
            4: "2026-10-10",
            7: "2026-10-23",
            11: "2026-08-11",
        }
        for i, (d, desc, meio, cat, valor, parcela) in enumerate(LINHAS):
            compra = date.fromisoformat(compras[i]) if i in compras else None
            # Datas explicitamente fictícias, não inferidas de um banco real.
            fatura = date(2026, 11, 9) if compra else date.fromisoformat(d)
            self.lancamentos.append(
                Lancamento(i + 1, fatura, compra, desc, meio, cat, valor, parcela)
            )

    def consultar_vendas(self, intervalo, dias=range(7)):
        a, b = intervalo
        return sorted(
            (r for r in self.vendas if a <= r.data <= b and r.data.weekday() in dias),
            key=lambda r: (r.data, r.id),
            reverse=True,
        )

    def consultar_financas(self, intervalo):
        a, b = intervalo
        return sorted(
            (r for r in self.lancamentos if a <= r.data <= b),
            key=lambda r: (r.data, r.id),
            reverse=True,
        )

    def resumo(self, intervalo):
        linhas = self.consultar_financas(intervalo)
        bruto = sum(r.total for r in self.consultar_vendas(intervalo))
        taxas = sum(r.valor for r in linhas if r.taxa)
        despesas = sum(r.valor for r in linhas if not r.taxa)
        return dict(
            bruto=bruto,
            taxas=taxas,
            liquido=bruto - taxas,
            despesas=despesas,
            saldo=bruto - taxas - despesas,
            falta=max(0, despesas - (bruto - taxas)),
        )

    def excluir(self, area, ids):
        atributo = "vendas" if area == "Vendas" else "lancamentos"
        antes = getattr(self, atributo)
        selecionados = set(ids)
        if not selecionados.issubset({r.id for r in antes}):
            raise ValueError(
                "A seleção contém registros inexistentes. Consulte novamente."
            )
        # Estado em memória: uma única substituição, sem escrita em banco ou nuvem.
        setattr(self, atributo, [r for r in antes if r.id not in selecionados])


def agrupar(vendas):
    grupos = {}
    for r in vendas:
        segunda = r.data - timedelta(days=r.data.weekday())
        grupos.setdefault(segunda, []).append(r)
    return sorted(grupos.items(), reverse=True)
