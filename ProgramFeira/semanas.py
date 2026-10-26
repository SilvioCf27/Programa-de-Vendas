"""Semanas civis de segunda a domingo; totais brutos, inclusive dias zerados."""
from datetime import date, timedelta
from decimal import Decimal
from ProgramFeira.database.banco import converter_data_salva
from ProgramFeira.resumos import calcular_indicadores
from ProgramFeira.fechamento import periodo

PERIODOS_INICIAIS = ('Fechamento atual', 'Mês atual', 'Ano atual', 'Todas as vendas')


def semana_atual(vendas, hoje=None):
    hoje = hoje or date.today()
    inicio = hoje - timedelta(days=hoje.weekday())
    registros = [v for v in vendas if (d := converter_data_salva(v[1])) is not None and inicio <= d <= hoje]
    return dict(inicio=inicio, fim=inicio + timedelta(days=6), ate=hoje,
                totais=tuple(sum((Decimal(str(v[i])) for v in registros), Decimal(0)) for i in (2, 3, 4)),
                **calcular_indicadores(registros))


def agrupar_semanas(vendas):
    grupos = {}
    for venda in vendas:
        dia = converter_data_salva(venda[1])
        if dia is not None:
            inicio = dia - timedelta(days=dia.weekday())
            grupos.setdefault(inicio, []).append(venda)
    return [dict(inicio=inicio, fim=inicio + timedelta(days=6), **calcular_indicadores(grupos[inicio]))
            for inicio in sorted(grupos, reverse=True)]


def selecao_inicial(preferencia, hoje=None):
    hoje = hoje or date.today()
    if preferencia not in PERIODOS_INICIAIS:
        raise ValueError('Período inicial inválido.')
    if preferencia == 'Todas as vendas':
        return None, None, False
    ano, mes = hoje.year, hoje.month
    if preferencia == 'Ano atual':
        return ano, None, False
    if preferencia == 'Fechamento atual':
        inicio, _ = periodo(ano, mes)
        if hoje < date.fromisoformat(inicio):
            anterior = hoje.replace(day=1) - timedelta(days=1)
            ano, mes = anterior.year, anterior.month
        return ano, mes, True
    return ano, mes, False
