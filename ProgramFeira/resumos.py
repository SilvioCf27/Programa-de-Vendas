"""Indicadores financeiros dos registros visíveis, incluindo dias zerados."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal('0')


def dinheiro(valor):
    return Decimal(str(valor))


def moeda(valor):
    texto = f'{valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):,.2f}'
    return 'R$ ' + texto.replace(',', '_').replace('.', ',').replace('_', '.')


def calcular_indicadores(vendas):
    totais = tuple(sum((dinheiro(v[i]) for v in vendas), ZERO) for i in (2, 3, 4))
    total = sum(totais, ZERO)
    quantidade = len(vendas)
    return {
        'quantidade': quantidade,
        'total': total,
        'media': total / quantidade if quantidade else ZERO,
        'participacoes': tuple(v * 100 / total if total else ZERO for v in totais),
    }


def periodo_anterior(tipo, inicio, fim):
    if not inicio or not fim:
        return None
    inicio, fim = date.fromisoformat(inicio), date.fromisoformat(fim)
    if tipo == 'Ano':
        return date(inicio.year - 1, 1, 1).isoformat(), date(inicio.year - 1, 12, 31).isoformat()
    if tipo == 'Mês':
        ultimo = inicio - timedelta(days=1)
        return ultimo.replace(day=1).isoformat(), ultimo.isoformat()
    if tipo == 'Período de fechamento':
        ultimo = inicio - timedelta(days=1)
        mes_anterior = inicio.replace(day=1) - timedelta(days=1)
        primeiro = mes_anterior.replace(day=inicio.day)
        return primeiro.isoformat(), ultimo.isoformat()
    return None


def descrever_comparacao(atual, anteriores, periodo):
    if periodo is None:
        return 'Comparação: selecione um ano ou mês nos filtros para comparar períodos.'
    inicio, fim = (date.fromisoformat(d).strftime('%d/%m/%Y') for d in periodo)
    prefixo = f'Anterior ({inicio} a {fim}): '
    if not anteriores['quantidade']:
        return prefixo + 'sem registros para comparação.'
    base = anteriores['total']
    detalhes = f'{moeda(base)} em {anteriores["quantidade"]} dias | Média: {moeda(anteriores["media"])}'
    if not atual['quantidade']:
        return prefixo + detalhes + ' | Período atual sem registros.'
    diferenca = atual['total'] - base
    if base == 0:
        variacao = 'variação percentual indisponível (total anterior zero)'
    else:
        percentual = (diferenca * 100 / base).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        variacao = f'{percentual:+.1f}%'.replace('.', ',')
    return prefixo + detalhes + f' | Diferença: {moeda(diferenca)} ({variacao})'
