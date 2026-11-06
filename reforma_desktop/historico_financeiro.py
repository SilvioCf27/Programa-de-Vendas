"""Projeção local da lista; não muda datas persistidas nem cálculos financeiros."""
from datetime import date
from unicodedata import normalize
from ProgramFeira.resumos import moeda
from decimal import Decimal
DIAS = ('segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo')


def data_da_compra(r):
    return r.get('data_compra') or (r['data'] if r['tipo'] == 'despesa' and r['meio'] != 'Cartão de crédito' else None)


def normalizar(s):
    return ''.join(c for c in normalize('NFD', str(s)) if not '\u0300' <= c <= '\u036f').lower().strip()


def historico_financeiro(registros, busca=''):
    termo = normalizar(busca)
    def corresponde(r):
        datas = [d for d in (data_da_compra(r), r['data']) if d]
        valor = Decimal(r['valor_centavos']) / 100
        textos = [r['descricao'], r['meio'], r['categoria'], 'taxa das vendas no cartão' if r['tipo'] == 'taxa' else 'despesa',
                  f"parcela {r['parcela']}/{r['parcelas']}" if r['parcelas'] > 1 else '', moeda(valor), f'{valor:.2f}', f'{valor:.2f}'.replace('.', ',')]
        for d in datas:
            data = date.fromisoformat(d)
            textos.extend((d, data.strftime('%d/%m/%Y'), DIAS[data.weekday()]))
        return termo in normalizar(' '.join(textos))
    # ID somente desempata; nunca é usado como data de cadastro/compra.
    linhas = sorted((r for r in registros if corresponde(r)), key=lambda r: str(r['id']))
    return sorted(linhas, key=lambda r: (data_da_compra(r) or (r['data'] if r['tipo'] == 'taxa' else ''), r['data']), reverse=True)
