"""Regras financeiras independentes da interface; valores novos em centavos."""
import calendar
import re
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from ProgramFeira.database import banco
from ProgramFeira.comparacao import fechamento_do_mes
from ProgramFeira.resumos import calcular_indicadores

MEIOS = ('Dinheiro', 'Pix', 'Cartão de crédito', 'Outro')
CATEGORIAS = ('Casa', 'Feira', 'Outros', 'Compromisso inicial')


def centavos(texto):
    texto = str(texto).strip().removeprefix('R$').strip()
    if ',' in texto:
        if not re.fullmatch(r'(?:\d+|\d{1,3}(?:\.\d{3})+),\d{1,2}', texto):
            raise ValueError('Informe o valor como 1234,56 ou 1.234,56.')
        texto = texto.replace('.', '').replace(',', '.')
    if not re.fullmatch(r'\d+(?:\.\d{1,2})?', texto):
        raise ValueError('Informe um valor positivo, com até duas casas decimais.')
    valor = int(Decimal(texto) * 100)
    if not 0 < valor <= 999_999_999_99:
        raise ValueError('O valor deve ser maior que zero e menor que um bilhão de reais.')
    return valor


def inicializar():
    with closing(banco.conectar()) as c:
        tabelas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    with closing(banco.conectar()) as c:
        colunas = {r[1] for r in c.execute('PRAGMA table_info(financeiro_taxas_anuais)')}
    if {'financeiro_lancamentos', 'financeiro_taxas_anuais'} <= tabelas and {'natureza', 'observacao'} <= colunas:
        return
    # Snapshot íntegro, anterior a qualquer alteração de estrutura.
    banco.criar_backup()
    with closing(banco.conectar()) as c, c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('''CREATE TABLE IF NOT EXISTS financeiro_lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL CHECK(tipo IN ('despesa','taxa')),
            data TEXT NOT NULL, descricao TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL CHECK(valor_centavos > 0),
            meio TEXT NOT NULL, categoria TEXT NOT NULL,
            grupo TEXT, parcela INTEGER NOT NULL DEFAULT 1,
            parcelas INTEGER NOT NULL DEFAULT 1)''')
        c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_taxa_diaria
            ON financeiro_lancamentos(data) WHERE tipo='taxa' ''')
        c.execute('''CREATE TABLE IF NOT EXISTS financeiro_taxas_anuais (
            ano INTEGER PRIMARY KEY, inicio TEXT NOT NULL, fim TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL CHECK(valor_centavos > 0),
            natureza TEXT NOT NULL DEFAULT 'Confirmada', observacao TEXT NOT NULL DEFAULT '')''')

        colunas = {r[1] for r in c.execute('PRAGMA table_info(financeiro_taxas_anuais)')}
        for nome, padrao in (('natureza', 'Confirmada'), ('observacao', '')):
            if nome not in colunas:
                c.execute(f"ALTER TABLE financeiro_taxas_anuais ADD COLUMN {nome} TEXT NOT NULL DEFAULT '{padrao}'")


def _data(texto):
    try:
        dia = date.fromisoformat(texto)
        if dia.isoformat() != texto:
            raise ValueError('Use AAAA-MM-DD.')
        return dia
    except (TypeError, ValueError) as erro:
        raise ValueError('Informe uma data válida.') from erro


def primeira_fatura(compra, fechamento=None):
    from ProgramFeira.fechamento import primeira_fatura as calcular
    regras = None if fechamento is None else [{'vigencia': '0001-01-01', 'dia': fechamento}]
    if fechamento is not None and (type(fechamento) is not int or not 1 <= fechamento <= 31):
        raise ValueError('Escolha um dia de fechamento entre 1 e 31.')
    return calcular(compra, regras)


def datas_parcelas(inicio, quantidade):
    dia = _data(inicio)
    if type(quantidade) is not int or not 1 <= quantidade <= 120:
        raise ValueError('Use de 1 a 120 parcelas.')
    resultado = []
    for i in range(quantidade):
        ano, mes = divmod(dia.year * 12 + dia.month - 1 + i, 12)
        mes += 1
        resultado.append(date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1])).isoformat())
    return resultado


def _conflito(c, inicio, fim, ignorar=None):
    return c.execute('''SELECT ano FROM financeiro_taxas_anuais
        WHERE inicio <= ? AND fim >= ? AND ano != ?''', (fim, inicio, ignorar or -1)).fetchone()


def dividir_total(total, quantidade):
    if type(quantidade) is not int or not 1 <= quantidade <= 120:
        raise ValueError('Use de 1 a 120 parcelas.')
    base, resto = divmod(total, quantidade)
    if base < 1:
        raise ValueError('O total precisa permitir pelo menos R$ 0,01 por parcela.')
    return [base + (1 if resto and i >= quantidade - resto else 0) for i in range(quantidade)]


def _compra(c, identificador):
    c.row_factory = sqlite3.Row
    linha = c.execute('SELECT * FROM financeiro_lancamentos WHERE id=?', (identificador,)).fetchone()
    if not linha:
        raise ValueError('O lançamento selecionado não existe mais.')
    r = dict(linha)
    registros = [dict(v) for v in c.execute('SELECT * FROM financeiro_lancamentos WHERE grupo=? ORDER BY parcela', (r['grupo'],))] if r['grupo'] else [r]
    n = r['parcelas']
    if len(registros) != n or [v['parcela'] for v in registros] != list(range(1, n + 1)) or any(v['parcelas'] != n or v['tipo'] != r['tipo'] for v in registros):
        raise ValueError('O histórico desta compra está incompleto ou inconsistente. Confira as parcelas ou restaure uma cópia antes de editar a compra; nada foi alterado.')
    return {**registros[0], 'valor_centavos': sum(v['valor_centavos'] for v in registros), 'registros': registros}


def compra_do_lancamento(identificador):
    with closing(banco.conectar()) as c:
        return _compra(c, identificador)


def salvar_lancamento(tipo, data, descricao, valor, meio='Outro', categoria='Outros', parcelas=1, identificador=None, esperados=None):
    _data(data)
    total = centavos(valor)
    descricao = descricao.strip()
    if tipo not in ('despesa', 'taxa') or not descricao or len(descricao) > 200:
        raise ValueError('Preencha uma descrição de até 200 caracteres.')
    if meio not in MEIOS or categoria not in CATEGORIAS:
        raise ValueError('Selecione uma forma de pagamento e uma categoria válidas.')
    try:
        parcelas = int(parcelas)
    except (TypeError, ValueError) as erro:
        raise ValueError('Informe a quantidade de parcelas.') from erro
    if not 1 <= parcelas <= 120 or (parcelas > 1 and (tipo != 'despesa' or meio != 'Cartão de crédito')):
        raise ValueError('Use de 1 a 120 parcelas, apenas para despesas no cartão.')
    valores = dividir_total(total, parcelas)
    datas = datas_parcelas(data, parcelas)
    banco.criar_backup()
    with closing(banco.conectar()) as c, c:
        c.execute('BEGIN IMMEDIATE')
        anteriores = []
        grupo = None
        if identificador is not None:
            compra = _compra(c, identificador)
            anteriores = compra['registros']
            if compra['tipo'] != tipo:
                raise ValueError('O tipo do lançamento não pode ser alterado.')
            if esperados is not None and anteriores != esperados:
                raise ValueError('A compra mudou desde que o formulário foi aberto. Feche e abra novamente antes de salvar.')
            grupo = compra['grupo']
        grupo = grupo or (uuid4().hex if parcelas > 1 else None)
        if tipo == 'taxa' and _conflito(c, data, data):
            raise ValueError('Essa data já está coberta por uma taxa anual. Não desconte a mesma taxa duas vezes.')
        try:
            for i, (vencimento, quantia) in enumerate(zip(datas, valores)):
                linha = (tipo, vencimento, descricao, quantia, meio, categoria, grupo, i + 1, parcelas)
                if i < len(anteriores):
                    c.execute('UPDATE financeiro_lancamentos SET tipo=?,data=?,descricao=?,valor_centavos=?,meio=?,categoria=?,grupo=?,parcela=?,parcelas=? WHERE id=?', (*linha, anteriores[i]['id']))
                else:
                    c.execute('INSERT INTO financeiro_lancamentos (tipo,data,descricao,valor_centavos,meio,categoria,grupo,parcela,parcelas) VALUES (?,?,?,?,?,?,?,?,?)', linha)
            for r in anteriores[parcelas:]:
                c.execute('DELETE FROM financeiro_lancamentos WHERE id=?', (r['id'],))
        except sqlite3.IntegrityError as erro:
            if tipo == 'taxa' and 'UNIQUE constraint failed' in str(erro):
                raise ValueError('Já existe uma taxa para essa data. Edite o lançamento existente.') from erro
            raise


def salvar_taxas_semana(inicio, valores):
    primeira = _data(inicio)
    if primeira.weekday() != 0:
        raise ValueError('Escolha uma semana de segunda a domingo.')
    permitidas = {(primeira + timedelta(days=i)).isoformat() for i in range(7)}
    if set(valores) - permitidas:
        raise ValueError('Há uma data fora da semana.')
    linhas = []
    for data, valor in valores.items():
        texto = str(valor).strip()
        if texto:
            quantia = 0 if re.fullmatch(r'0+(?:[.,]0{1,2})?', texto) else centavos(texto)
            linhas.append((data, quantia))
    if not linhas:
        raise ValueError('Preencha os dias em que houve desconto nas vendas.')
    banco.criar_backup()
    alterados = 0
    with closing(banco.conectar()) as c, c:
        c.execute('BEGIN IMMEDIATE')
        for data, quantia in linhas:
            anterior = c.execute("SELECT id,valor_centavos FROM financeiro_lancamentos WHERE tipo='taxa' AND data=?", (data,)).fetchone()
            if not quantia:
                if anterior:
                    raise ValueError('Para remover uma taxa existente, use Excluir no lançamento.')
                continue
            if _conflito(c, data, data):
                raise ValueError('Esta data já está incluída em um total histórico de taxas. Não registre o mesmo desconto novamente.')
            if anterior:
                if anterior[1] == quantia:
                    continue
                c.execute('UPDATE financeiro_lancamentos SET valor_centavos=? WHERE id=?', (quantia, anterior[0]))
            else:
                c.execute("""INSERT INTO financeiro_lancamentos(tipo,data,descricao,valor_centavos,meio,categoria,parcela,parcelas)
                    VALUES('taxa',?,'Taxa das vendas no cartão',?,'Outro','Feira',1,1)""", (data, quantia))
            alterados += 1
        if not alterados:
            raise ValueError('Nenhuma taxa nova ou alterada para salvar.')
    return alterados


def salvar_taxa_anual(ano, inicio, fim, valor, natureza='Confirmada', observacao=''):
    try:
        ano = int(ano)
    except (TypeError, ValueError) as erro:
        raise ValueError('Informe um ano válido.') from erro
    if natureza not in ('Confirmada', 'Estimada'):
        raise ValueError('Escolha Confirmada ou Estimada.')
    primeira, ultima = _data(inicio), _data(fim)
    quantia = centavos(valor)
    if primeira.year != ano or ultima.year != ano or primeira > ultima:
        raise ValueError('O intervalo da taxa deve estar dentro do ano informado, em ordem crescente.')
    banco.criar_backup()
    with closing(banco.conectar()) as c, c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute("SELECT id FROM financeiro_lancamentos WHERE tipo='taxa' AND data BETWEEN ? AND ? LIMIT 1", (inicio, fim)).fetchone():
            raise ValueError('Há taxas diárias nesse intervalo. Não é possível somar um ajuste anual sobre elas.')
        c.execute('''INSERT INTO financeiro_taxas_anuais (ano,inicio,fim,valor_centavos,natureza,observacao) VALUES (?,?,?,?,?,?)
            ON CONFLICT(ano) DO UPDATE SET inicio=excluded.inicio,fim=excluded.fim,valor_centavos=excluded.valor_centavos,
            natureza=excluded.natureza,observacao=excluded.observacao''',
            (ano, inicio, fim, quantia, natureza, observacao.strip()))


def excluir_lancamento(identificador, anual=False):
    tabela, coluna = ('financeiro_taxas_anuais', 'ano') if anual else ('financeiro_lancamentos', 'id')
    banco.criar_backup()
    with closing(banco.conectar()) as c, c:
        c.execute('BEGIN IMMEDIATE')
        c.execute(f'DELETE FROM {tabela} WHERE {coluna}=?', (identificador,))


def listar_lancamentos(inicio, fim):
    with closing(banco.conectar()) as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute('SELECT * FROM financeiro_lancamentos WHERE data BETWEEN ? AND ? ORDER BY data DESC,id DESC', (inicio, fim))]


def listar_taxas_anuais():
    with closing(banco.conectar()) as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute('SELECT * FROM financeiro_taxas_anuais ORDER BY ano DESC')]


def limites(tipo, referencia):
    dia = _data(referencia)
    if tipo == 'Semana':
        inicio = dia - timedelta(days=dia.weekday())
        return inicio.isoformat(), (inicio + timedelta(days=6)).isoformat()
    if tipo == 'Mês':
        return dia.replace(day=1).isoformat(), dia.replace(day=calendar.monthrange(dia.year, dia.month)[1]).isoformat()
    if tipo == 'Ano':
        return date(dia.year, 1, 1).isoformat(), date(dia.year, 12, 31).isoformat()
    if tipo == 'Fechamento':
        return fechamento_do_mes(dia.year, dia.month)
    raise ValueError('Escolha Semana, Mês, Fechamento ou Ano.')


def resumir(vendas, lancamentos, anuais, inicio, fim):
    bruto = calcular_indicadores(vendas)['total']
    despesas = sum(r['valor_centavos'] for r in lancamentos if r['tipo'] == 'despesa')
    taxas = sum(r['valor_centavos'] for r in lancamentos if r['tipo'] == 'taxa')
    parciais = []
    estimados = []
    for ajuste in anuais:
        if ajuste['inicio'] <= fim and ajuste['fim'] >= inicio:
            if ajuste.get('natureza') == 'Estimada':
                estimados.append(ajuste['ano'])
            if inicio <= ajuste['inicio'] and fim >= ajuste['fim']:
                taxas += ajuste['valor_centavos']
            else:
                parciais.append(ajuste['ano'])
    taxas, despesas = Decimal(taxas) / 100, Decimal(despesas) / 100
    liquido = bruto - taxas
    saldo = liquido - despesas
    return dict(bruto=bruto, taxas=taxas, liquido=liquido, despesas=despesas, saldo=saldo,
                falta=max(Decimal(0), -saldo), parciais=parciais, estimados=estimados)


def resumo_periodo(inicio, fim):
    return resumir(banco.listar_vendas(inicio, fim), listar_lancamentos(inicio, fim), listar_taxas_anuais(), inicio, fim)


def semanas(lancamentos):
    grupos = {}
    for r in lancamentos:
        if r['tipo'] == 'despesa':
            dia = _data(r['data'])
            segunda = dia - timedelta(days=dia.weekday())
            grupos[segunda] = grupos.get(segunda, 0) + r['valor_centavos']
    return sorted(grupos.items())
