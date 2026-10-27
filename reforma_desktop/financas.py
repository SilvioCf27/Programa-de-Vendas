"""Adaptador financeiro Qt sem toolkit; núcleo e esquema existentes preservados."""
import calendar
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, timedelta

from ProgramFeira import financeiro as f
from ProgramFeira.database import banco


@dataclass(frozen=True)
class ConsultaFinanceira:
    tipo: str
    referencia: date

    def limites(self):
        return f.limites(self.tipo, self.referencia.isoformat())


def semanas_do_mes(ano, mes):
    primeira = date(ano, mes, 1)
    segunda = primeira - timedelta(days=primeira.weekday())
    ultima = date(ano, mes, calendar.monthrange(ano, mes)[1])
    resultado = []
    while segunda <= ultima:
        resultado.append((segunda, segunda + timedelta(days=6)))
        segunda += timedelta(days=7)
    return resultado


class ServicoFinanceiro:
    def __init__(self):
        f.inicializar()

    def consultar(self, consulta):
        inicio, fim = consulta.limites()
        linhas, anuais = f.listar_lancamentos(inicio, fim), f.listar_taxas_anuais()
        resumo = f.resumir(banco.listar_vendas(inicio, fim), linhas, anuais, inicio, fim)
        return dict(consulta=consulta, intervalo=(inicio, fim), linhas=linhas, anuais=anuais,
                    resumo=resumo, semanas=f.semanas(linhas))

    def compra(self, identificador):
        return f.compra_do_lancamento(identificador)

    def salvar_compra(self, tipo, data, descricao, valor, meio, categoria, parcelas=1, anterior=None, data_compra=None):
        f.salvar_lancamento(tipo, data, descricao, valor, meio, categoria, parcelas,
                           anterior['id'] if anterior else None, anterior['registros'] if anterior else None,
                           data_compra=data_compra)

    def excluir(self, esperados):
        if not esperados:
            return
        if len({r['id'] for r in esperados}) != len(esperados):
            raise ValueError('Seleção duplicada.')
        banco.criar_backup()
        with closing(banco.conectar()) as c, c:
            c.execute('BEGIN IMMEDIATE')
            c.row_factory = sqlite3.Row
            for esperado in esperados:
                r = c.execute('SELECT * FROM financeiro_lancamentos WHERE id=?', (esperado['id'],)).fetchone()
                if r is None or dict(r) != esperado:
                    raise ValueError('Um lançamento mudou desde a seleção. Nada foi excluído; consulte novamente.')
            c.executemany('DELETE FROM financeiro_lancamentos WHERE id=?', [(r['id'],) for r in esperados])

    def semana_taxas(self, inicio):
        inicio, fim = f.limites('Semana', inicio)
        return dict(intervalo=(inicio, fim), registros=[r for r in f.listar_lancamentos(inicio, fim) if r['tipo'] == 'taxa'],
                    anuais=[r for r in f.listar_taxas_anuais() if r['inicio'] <= fim and r['fim'] >= inicio])

    def salvar_taxas(self, inicio, valores, esperado):
        if self.semana_taxas(inicio) != esperado:
            raise ValueError('As taxas ou sua cobertura histórica mudaram. Recarregue a semana antes de salvar.')
        return f.salvar_taxas_semana(inicio, valores)

    def salvar_anual(self, ano, inicio, fim, valor, natureza, observacao, esperado=None):
        atual = next((r for r in f.listar_taxas_anuais() if r['ano'] == ano), None)
        if atual != esperado:
            raise ValueError('Já existe um histórico neste ano ou ele mudou. Abra o histórico atualizado para editar.')
        f.salvar_taxa_anual(ano, inicio, fim, valor, natureza, observacao)

    def excluir_anual(self, esperado):
        banco.criar_backup()
        with closing(banco.conectar()) as c, c:
            c.execute('BEGIN IMMEDIATE')
            c.row_factory = sqlite3.Row
            atual = c.execute('SELECT * FROM financeiro_taxas_anuais WHERE ano=?', (esperado['ano'],)).fetchone()
            if atual is None or dict(atual) != esperado:
                raise ValueError('O histórico mudou. Nada foi excluído; abra a lista atualizada.')
            c.execute('DELETE FROM financeiro_taxas_anuais WHERE ano=?', (esperado['ano'],))
