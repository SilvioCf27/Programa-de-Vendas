"""Totais brutos em até 12 meses/fechamentos consecutivos da seleção aplicada."""
from ProgramFeira.database.banco import converter_data_salva
from ProgramFeira.resumos import calcular_indicadores


def evolucao(vendas, tipo='Mês'):
    grupos = {}
    for venda in vendas:
        dia = converter_data_salva(venda[1])
        if dia is None:
            continue
        ano, mes = dia.year, dia.month
        if tipo == 'Fechamento' and dia.day <= 9:
            mes -= 1
            if not mes:
                ano, mes = ano - 1, 12
        grupos.setdefault((ano, mes), []).append(venda)
    if not grupos:
        return []
    ano, mes = max(grupos)
    primeiro = min(grupos)
    resultado = []
    for _ in range(12):
        if (ano, mes) < primeiro:
            break
        resultado.insert(0, dict(rotulo=f'{mes:02d}/{ano}', **calcular_indicadores(grupos.get((ano, mes), []))))
        mes -= 1
        if not mes:
            ano, mes = ano - 1, 12
    return resultado
