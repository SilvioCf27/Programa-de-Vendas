"""Adaptador sem toolkit: regras e persistência permanecem no núcleo existente."""
from calendar import monthrange
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import math

from ProgramFeira import fechamento
from ProgramFeira.database import banco
from ProgramFeira.resumos import calcular_indicadores, periodo_anterior, descrever_comparacao
from ProgramFeira.semanas import semana_atual
from ProgramFeira.exportacao import montar_relatorio


@dataclass(frozen=True)
class Consulta:
    ano: int | None = None
    mes: int | None = None
    fechamento: bool = False
    dias: tuple = ()

    def limites(self):
        if self.mes is not None and self.ano is None:
            raise ValueError('Selecione o ano para consultar um mês.')
        if self.fechamento and self.mes is None:
            raise ValueError('Selecione mês e ano para consultar o fechamento.')
        if any(type(d) is not int or not 0 <= d <= 6 for d in self.dias):
            raise ValueError('Dia da semana inválido.')
        if self.ano is None:
            return None, None
        if self.mes is None:
            return date(self.ano, 1, 1).isoformat(), date(self.ano, 12, 31).isoformat()
        if self.fechamento:
            return fechamento.periodo(self.ano, self.mes)
        return date(self.ano, self.mes, 1).isoformat(), date(self.ano, self.mes, monthrange(self.ano, self.mes)[1]).isoformat()

    @property
    def tipo(self):
        return 'Período de fechamento' if self.fechamento else 'Mês' if self.mes else 'Ano' if self.ano else 'Todas as vendas'

    def descricao(self):
        a, b = self.limites()
        recorte = f'{date.fromisoformat(a):%d/%m/%Y} a {date.fromisoformat(b):%d/%m/%Y}' if a else 'Todas as vendas'
        return recorte + (' · dias: ' + ', '.join(str(d + 1) for d in self.dias) if self.dias else '')


def valor(texto):
    # Mesmo formato aceito pelo cadastro estável, com recusa explícita de NaN/inf.
    texto = str(texto).strip().replace('R$', '').replace(' ', '')
    if not texto:
        return Decimal('0')
    if ',' in texto and '.' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    else:
        texto = texto.replace(',', '.')
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        raise ValueError('Informe um valor monetário válido.') from None
    if not numero.is_finite() or numero < 0 or not math.isfinite(float(numero)):
        raise ValueError('Os valores devem ser finitos e não negativos.')
    try:
        centavos = numero.quantize(Decimal('.01'))
    except InvalidOperation:
        raise ValueError('Valor fora do limite de precisão monetária.') from None
    if numero != centavos:
        raise ValueError('Use no máximo duas casas decimais.')
    if Decimal(str(float(numero))) != numero:
        raise ValueError('Valor fora do limite de precisão do banco atual.')
    return numero


class ServicoVendas:
    def __init__(self, hoje=date.today):
        self.hoje = hoje
        banco.criar_tabela()
        fechamento.carregar(banco.CAMINHO_BANCO)

    def consultar(self, consulta):
        inicio, fim = consulta.limites()
        linhas = banco.listar_vendas(inicio, fim, consulta.dias)
        indicadores = calcular_indicadores(linhas)
        anterior = periodo_anterior(consulta.tipo, inicio, fim)
        anteriores = calcular_indicadores(banco.listar_vendas(*anterior, consulta.dias)) if anterior else calcular_indicadores([])
        comparacao = descrever_comparacao(indicadores, anteriores, anterior)
        return dict(linhas=linhas, indicadores=indicadores, comparacao=comparacao,
                    semana=semana_atual(banco.listar_vendas(), self.hoje()),
                    relatorio=montar_relatorio(linhas, consulta.descricao(), comparacao))

    def salvar(self, data, dinheiro, pix, cartao, esperado=None):
        dia = date.fromisoformat(data).isoformat()
        pagamentos = tuple(float(valor(v)) for v in (dinheiro, pix, cartao))
        existente = banco.buscar_venda_por_data(dia)
        if existente and (esperado is None or existente[0] != esperado[0]):
            raise ValueError('Já existe uma venda nesta data. Abra essa venda para editar.')
        if esperado is None:
            banco.cadastrar_venda(dia, *pagamentos)
        else:
            if banco.buscar_venda_por_id(esperado[0]) != esperado:
                raise ValueError('A venda mudou desde a abertura do formulário. Reabra antes de editar.')
            banco.atualizar_venda(esperado[0], dia, *pagamentos)

    def excluir(self, esperados):
        if not esperados:
            return
        if len({r[0] for r in esperados}) != len(esperados):
            raise ValueError('Seleção duplicada.')
        # Um backup verificado e uma transação para o lote. Triggers existentes
        # continuam sendo executados, sem reimplementar protocolo de sincronização.
        banco.criar_backup()
        with closing(banco.conectar()) as conexao, conexao:
            conexao.execute('BEGIN IMMEDIATE')
            for esperado in esperados:
                atual = conexao.execute('SELECT id,data,dinheiro,pix,cartao FROM vendas WHERE id=?', (esperado[0],)).fetchone()
                if atual != esperado:
                    raise ValueError('Uma venda mudou desde a seleção. Nada foi excluído; aplique a consulta novamente.')
            conexao.executemany('DELETE FROM vendas WHERE id=?', [(r[0],) for r in esperados])
