"""Consultas de Análises sem toolkit; reaproveita o núcleo da versão estável."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from ProgramFeira.database import banco
from ProgramFeira.comparacao import limites_comparacao, comparar_registros
from ProgramFeira.resumos import calcular_indicadores
from ProgramFeira.semanas import agrupar_semanas
from ProgramFeira.tendencias import evolucao

DIAS = ('Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo')


def centavos(valor):
    """Somente apresentação nos componentes gráficos existentes (que usam centavos)."""
    return int((Decimal(str(valor)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def pagamentos(linhas):
    return tuple(sum((Decimal(str(v[i])) for v in linhas), Decimal(0)) for i in (2, 3, 4))


@dataclass(frozen=True)
class Periodo:
    tipo: str
    ano: int
    mes: int
    inicio: date
    fim: date

    def limites(self):
        return limites_comparacao(self.tipo, self.ano, self.mes,
                                  self.inicio.strftime('%d/%m/%Y'), self.fim.strftime('%d/%m/%Y'))


def analisar(linhas, consulta):
    # Snapshot da consulta APLICADA de Vendas, sem limitar pela busca/paginação.
    linhas = tuple(tuple(v) for v in linhas)
    inicio, fim = consulta.limites()
    por_semana, por_dia = defaultdict(list), [[] for _ in range(7)]
    for venda in linhas:
        dia = banco.converter_data_salva(venda[1])
        if dia:
            por_semana[dia - timedelta(days=dia.weekday())].append(venda)
            por_dia[dia.weekday()].append(venda)
    semanas = []
    for grupo in agrupar_semanas(linhas):
        # Semana parcial pela borda OU por recorte de dias. Não implica falta de cadastro.
        parcial = bool(consulta.dias and len(set(consulta.dias)) < 7)
        parcial |= bool(inicio and grupo['inicio'] < date.fromisoformat(inicio))
        parcial |= bool(fim and grupo['fim'] > date.fromisoformat(fim))
        semanas.append(dict(grupo, pagamentos=pagamentos(por_semana[grupo['inicio']]), parcial=parcial))
    return dict(linhas=linhas, indicadores=calcular_indicadores(linhas), pagamentos=pagamentos(linhas),
                semanas=semanas, dias=[(nome, calcular_indicadores(grupo)) for nome, grupo in zip(DIAS, por_dia)],
                consulta=consulta)


def comparar(a, b):
    # Valida AMBOS antes de fazer qualquer consulta/substituir resultados.
    limites_a, limites_b = a.limites(), b.limites()
    return comparar_limites(limites_a, limites_b)


def comparar_limites(a, b):
    vendas_a, vendas_b = banco.listar_vendas(*a), banco.listar_vendas(*b)
    return dict(comparar_registros(vendas_a, vendas_b), limites=(a, b))


def analisar_evolucao(snapshot, modo):
    if modo not in ('Mês', 'Fechamento'):
        raise ValueError('Escolha Mês ou Fechamento.')
    return evolucao(snapshot['linhas'], modo)
