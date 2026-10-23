"""Períodos e comparação independente, sem alterar os filtros de Vendas."""
import calendar
from datetime import date, datetime
from decimal import Decimal
from ProgramFeira.resumos import calcular_indicadores


def fechamento_do_mes(ano, mes, dia=None):
    from ProgramFeira import fechamento
    regras = None if dia is None else [{'vigencia': '0001-01-01', 'dia': dia}]
    return fechamento.periodo(ano, mes, regras)


def interpretar_data(texto):
    try:
        return datetime.strptime(texto.strip(), '%d/%m/%Y').date()
    except ValueError as erro:
        raise ValueError('Informe uma data válida no formato DD/MM/AAAA.') from erro


def limites_comparacao(tipo, ano, mes, inicio='', fim=''):
    if tipo in ('Data', 'Intervalo'):
        primeira = interpretar_data(inicio)
        ultima = primeira if tipo == 'Data' else interpretar_data(fim)
        if primeira > ultima:
            raise ValueError('A data inicial não pode ser posterior à final.')
        return primeira.isoformat(), ultima.isoformat()
    ano, mes = int(ano), int(mes)
    if tipo == 'Mês':
        return date(ano, mes, 1).isoformat(), date(ano, mes, calendar.monthrange(ano, mes)[1]).isoformat()
    if tipo == 'Fechamento':
        return fechamento_do_mes(ano, mes)
    raise ValueError('Escolha Data, Mês, Fechamento ou Intervalo.')


def comparar_registros(vendas_a, vendas_b):
    a, b = calcular_indicadores(vendas_a), calcular_indicadores(vendas_b)
    if not a['quantidade'] or not b['quantidade']:
        variacao = None
        motivo = 'Sem registros em um dos períodos: não há base para calcular a variação.'
    elif a['total'] == 0:
        variacao = None
        motivo = 'O total de A é zero: a variação percentual não pode ser calculada.'
    else:
        variacao = (b['total'] - a['total']) * 100 / a['total']
        motivo = ''
    pagamentos_a = tuple(sum((Decimal(str(v[i])) for v in vendas_a), Decimal(0)) for i in (2, 3, 4))
    pagamentos_b = tuple(sum((Decimal(str(v[i])) for v in vendas_b), Decimal(0)) for i in (2, 3, 4))
    return {'a': a, 'b': b, 'pagamentos_a': pagamentos_a, 'pagamentos_b': pagamentos_b,
            'diferenca': b['total'] - a['total'], 'variacao': variacao, 'motivo': motivo}
