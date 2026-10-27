"""Formatação de indicadores da demo, sem alterar os cálculos da aplicação real."""

from decimal import Decimal, ROUND_HALF_UP


def variacao_percentual(atual, anterior):
    if anterior == 0:
        return (
            "Sem base para percentual" if atual else "Sem movimento nos dois períodos"
        )
    valor = (Decimal(atual - anterior) * 100 / abs(Decimal(anterior))).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    return f"{valor:+.1f}% em relação ao anterior".replace(".", ",")
