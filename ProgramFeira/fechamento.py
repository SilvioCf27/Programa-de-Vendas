"""Regras de fechamento por vigência, sem reclassificar faturas já encerradas."""
import calendar
from datetime import date, timedelta

_estado = {'versao': 0, 'historico': []}


def validar(estado):
    if not isinstance(estado, dict) or not isinstance(estado.get('historico'), list) or set(estado) != {'versao', 'historico'} or type(estado['versao']) is not int or estado['versao'] < 0:
        raise ValueError('Configuração de fechamento inválida.')
    anterior = ''
    historico = []
    for regra in estado['historico']:
        if not isinstance(regra, dict) or set(regra) != {'vigencia', 'dia'} or type(regra['dia']) is not int or not 1 <= regra['dia'] <= 31:
            raise ValueError('Configuração de fechamento inválida.')
        vigencia = date.fromisoformat(regra['vigencia'])
        if vigencia.day != 1 or vigencia.isoformat() != regra['vigencia'] or regra['vigencia'] <= anterior:
            raise ValueError('Histórico de fechamentos inválido.')
        anterior = regra['vigencia']
        historico.append(dict(regra))
    return {'versao': estado['versao'], 'historico': historico}


def definir(estado):
    global _estado
    _estado = validar(estado)


def estado():
    return validar(_estado)


def dia_no_mes(ano, mes, historico=None):
    mes_iso = date(ano, mes, 1).isoformat()
    dia = 9
    for regra in _estado['historico'] if historico is None else historico:
        if regra['vigencia'] <= mes_iso:
            dia = regra['dia']
    return min(dia, calendar.monthrange(ano, mes)[1])


def periodo(ano, mes, historico=None):
    historico = _estado['historico'] if historico is None else historico
    primeira = date(ano, mes, dia_no_mes(ano, mes, historico)) + timedelta(days=1)
    proximo_ano, proximo_mes = divmod(ano * 12 + mes, 12)
    proximo_mes += 1
    ultima = date(proximo_ano, proximo_mes, dia_no_mes(proximo_ano, proximo_mes, historico))
    return primeira.isoformat(), ultima.isoformat()


def primeira_fatura(compra, historico=None):
    historico = _estado['historico'] if historico is None else historico
    dia = date.fromisoformat(compra)
    atual = dia.replace(day=dia_no_mes(dia.year, dia.month, historico))
    if dia < atual:
        return atual.isoformat()
    ano, mes = divmod(dia.year * 12 + dia.month, 12)
    mes += 1
    return date(ano, mes, dia_no_mes(ano, mes, historico)).isoformat()


def propor(estado_atual, vigencia, dia, hoje=None):
    estado_atual = validar(estado_atual)
    hoje = hoje or date.today()
    primeira = date.fromisoformat(vigencia)
    if primeira.day != 1 or primeira <= hoje.replace(day=1):
        raise ValueError('Escolha uma vigência a partir do próximo mês. Fechamentos antigos não podem ser alterados.')
    if type(dia) is not int or not 1 <= dia <= 31:
        raise ValueError('Escolha um dia entre 1 e 31.')
    historico = estado_atual['historico']
    if historico and historico[-1]['vigencia'] > vigencia:
        raise ValueError('A vigência deve ser igual ou posterior à regra mais recente.')
    historico = [r for r in historico if r['vigencia'] != vigencia] + [{'vigencia': vigencia, 'dia': dia}]
    return validar({'versao': estado_atual['versao'] + 1, 'historico': historico})


def carregar(banco):
    from contextlib import closing
    import json
    import sqlite3
    with closing(sqlite3.connect(banco)) as c:
        existe = c.execute("SELECT 1 FROM sqlite_master WHERE name='fechamento_configuracao'").fetchone()
        linha = c.execute('SELECT estado FROM fechamento_configuracao WHERE singleton=1').fetchone() if existe else None
    definir(json.loads(linha[0]) if linha else {'versao': 0, 'historico': []})
    return estado()


def guardar(banco, config, projeto, usuario):
    from contextlib import closing
    import json
    import sqlite3
    from ProgramFeira.database.armazenamento import criar_backup
    config = validar(config)
    with closing(sqlite3.connect(banco)) as c:
        vinculado = c.execute("SELECT 1 FROM sqlite_master WHERE name='nuvem_sync_estado'").fetchone()
        vinculo = c.execute('SELECT projeto,usuario_id FROM nuvem_sync_estado WHERE singleton=1').fetchone() if vinculado else None
        if vinculo and tuple(vinculo) != (projeto, usuario):
            raise ValueError('A configuração pertence a outra conta ou projeto. Os dados locais foram preservados.')
        existe = c.execute("SELECT 1 FROM sqlite_master WHERE name='fechamento_configuracao'").fetchone()
        linha = c.execute('SELECT estado,projeto,usuario FROM fechamento_configuracao WHERE singleton=1').fetchone() if existe else None
        if linha and tuple(linha[1:]) != (projeto, usuario):
            raise ValueError('O histórico local pertence a outra conta ou projeto.')
        anterior = validar(json.loads(linha[0])) if linha else {'versao': 0, 'historico': []}
    if config['versao'] < anterior['versao'] or (config['versao'] == anterior['versao'] and config != anterior):
        raise ValueError('A configuração recebida é anterior ou divergente. A regra local foi preservada.')
    if config == anterior:
        definir(config)
        return False
    criar_backup(banco, 'antes-alterar-fechamento')
    with closing(sqlite3.connect(banco)) as c, c:
        c.execute('CREATE TABLE IF NOT EXISTS fechamento_configuracao(singleton INTEGER PRIMARY KEY CHECK(singleton=1), estado TEXT NOT NULL, projeto TEXT NOT NULL, usuario TEXT NOT NULL)')
        c.execute('INSERT OR REPLACE INTO fechamento_configuracao VALUES(1,?,?,?)', (json.dumps(config), projeto, usuario))
    definir(config)
    return True
