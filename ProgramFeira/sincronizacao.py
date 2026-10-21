"""Sincronização por registro com base local, versões remotas e envio retomável."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4, uuid5
from ProgramFeira import migracao_nuvem as migracao
from ProgramFeira.database.armazenamento import criar_backup
from ProgramFeira.nuvem import ErroNuvem, LoteRecusado

TABELAS = migracao.TABELAS
COLUNAS = {
    'vendas': ('data', 'dinheiro_centavos', 'pix_centavos', 'cartao_centavos'),
    'financeiro_lancamentos': ('tipo', 'data', 'descricao', 'valor_centavos', 'meio', 'categoria', 'grupo', 'parcela', 'parcelas'),
    'financeiro_taxas_anuais': ('ano', 'inicio', 'fim', 'valor_centavos', 'natureza', 'observacao'),
}


def _json(valor):
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _corpo(registro):
    return None if registro is None else {k: v for k, v in registro.items() if k not in ('id', 'versao')}


def validar_snapshot(resposta, usuario_id, operacao_id=None):
    try:
        if resposta['protocolo'] != 1 or resposta['usuario_id'] != usuario_id or resposta['operacao_id'] != operacao_id or set(resposta['dados']) != set(TABELAS):
            raise ValueError()
        resultado = {}
        for tabela in TABELAS:
            resultado[tabela] = {}
            linhas = resposta['dados'][tabela]
            if not isinstance(linhas, list):
                raise ValueError()
            naturais = set()
            for r in linhas:
                if set(r) != set(COLUNAS[tabela]) | {'id', 'versao'} or str(UUID(r['id'])) != r['id']:
                    raise ValueError()
                if type(r['versao']) is not int or r['versao'] < 1 or r['id'] in resultado[tabela]:
                    raise ValueError()
                if tabela != 'financeiro_taxas_anuais':
                    if migracao._data(r['data']) != r['data']:
                        raise ValueError()
                chave = r['data'] if tabela == 'vendas' else r['ano'] if tabela == 'financeiro_taxas_anuais' else r['id']
                if chave in naturais:
                    raise ValueError()
                naturais.add(chave)
                resultado[tabela][r['id']] = r
        return resultado
    except (ValueError, TypeError, KeyError):
        raise ErroNuvem('A nuvem retornou um conjunto de dados inválido. O banco local foi preservado.') from None


def _estrutura(c):
    c.execute('''create table if not exists nuvem_sync_estado (
        singleton integer primary key check(singleton=1),
        projeto text not null, usuario_id text not null, pendente text)''')
    c.execute('''create table if not exists nuvem_sync_registros (
        tabela text not null, remoto_id text not null, local_id integer,
        base_local text not null, base_remota text not null,
        primary key(tabela,remoto_id), unique(tabela,local_id))''')


def _locais(c, usuario_id):
    dados = migracao.extrair(c, usuario_id)
    resultado = {}
    for tabela in TABELAS:
        chave = 'ano' if tabela == 'financeiro_taxas_anuais' else 'id'
        ids = [r[0] for r in c.execute(f'select {chave} from {tabela} order by {chave}')]
        resultado[tabela] = {i: _corpo(r) for i, r in zip(ids, dados[tabela])}
    return resultado


def _referencias(c):
    return [dict(tabela=r[0], remoto_id=r[1], local_id=r[2], local=json.loads(r[3]), remoto=json.loads(r[4])) for r in c.execute('select tabela,remoto_id,local_id,base_local,base_remota from nuvem_sync_registros')]


def _salvar_referencias(c, referencias):
    c.execute('delete from nuvem_sync_registros')
    c.executemany('insert into nuvem_sync_registros values(?,?,?,?,?)', [(r['tabela'], r['remoto_id'], r['local_id'], _json(r['local']), _json(r['remoto'])) for r in referencias])


def _vincular(locais, remotos, usuario_id):
    referencias = []
    for tabela in TABELAS:
        usados = set()
        for local_id, corpo in locais[tabela].items():
            if tabela == 'financeiro_lancamentos':
                identificador = str(uuid5(UUID(usuario_id), 'desktop:financeiro_lancamentos:' + str(local_id)))
                candidatos = [r for r in remotos[tabela].values() if r['id'] == identificador]
            else:
                chave = 'data' if tabela == 'vendas' else 'ano'
                candidatos = [r for r in remotos[tabela].values() if r[chave] == corpo[chave]]
            if len(candidatos) != 1 or _corpo(candidatos[0]) != corpo:
                raise ErroNuvem('O primeiro vínculo exige os mesmos dados da migração no PC e na nuvem. Há diferenças em ' + tabela + '. Nenhum dado foi substituído.')
            remoto = candidatos[0]
            usados.add(remoto['id'])
            referencias.append(dict(tabela=tabela, remoto_id=remoto['id'], local_id=local_id, local=corpo, remoto=remoto))
        if usados != set(remotos[tabela]):
            raise ErroNuvem('Há registros extras na nuvem antes do primeiro vínculo, em ' + tabela + '. Nenhum dado foi substituído.')
    return referencias


def planejar(locais, remotos, referencias):
    """Mescla mudanças independentes. Divergências no mesmo registro bloqueiam o lote."""
    refs = {(r['tabela'], r['remoto_id']): dict(r) for r in referencias}
    conflitos = []
    # Novos registros locais ganham identidade estável no próximo envio pendente.
    for tabela in TABELAS:
        vinculados = {r['local_id'] for r in referencias if r['tabela'] == tabela}
        for local_id, corpo in locais[tabela].items():
            if local_id in vinculados:
                continue
            chave = 'data' if tabela == 'vendas' else 'ano' if tabela == 'financeiro_taxas_anuais' else None
            candidatos = [r for r in remotos[tabela].values() if chave and r[chave] == corpo[chave]]
            if candidatos:
                remoto = candidatos[0]
                if (tabela, remoto['id']) in refs or _corpo(remoto) != corpo:
                    conflitos.append(f'{tabela}: {corpo.get(chave)} (cadastros diferentes)')
                    continue
                identificador = remoto['id']
            else:
                identificador = str(uuid4())
            refs[tabela, identificador] = dict(tabela=tabela, remoto_id=identificador, local_id=local_id, local=None, remoto=None)
        for identificador in remotos[tabela]:
            refs.setdefault((tabela, identificador), dict(tabela=tabela, remoto_id=identificador, local_id=None, local=None, remoto=None))
    operacoes, proximas = [], []
    for (tabela, identificador), ref in refs.items():
        local = locais[tabela].get(ref['local_id'])
        remoto = remotos[tabela].get(identificador)
        corpo_remoto = _corpo(remoto)
        if local == ref['local']:
            desejado = corpo_remoto
        elif corpo_remoto == _corpo(ref['remoto']):
            # Uma exclusão recebida antes de uma falha não deve ressuscitar em
            # silêncio se o usuário editou a cópia antiga durante a recuperação.
            if ref['local'] != _corpo(ref['remoto']) and local != corpo_remoto:
                conflitos.append(f'{tabela}: {local.get("data", local.get("ano", identificador))} (edição durante recuperação)')
                continue
            desejado = local
        elif local == corpo_remoto:
            desejado = corpo_remoto
        else:
            referencia = local or corpo_remoto or ref['local'] or _corpo(ref['remoto']) or {}
            conflitos.append(f'{tabela}: {referencia.get("data", referencia.get("ano", identificador))}')
            continue
        previsto = remoto
        if desejado != corpo_remoto:
            acao = 'excluir' if desejado is None else 'inserir' if remoto is None else 'editar'
            operacoes.append(dict(tabela=tabela, acao=acao, id=identificador, versao=remoto['versao'] if remoto else None, dados=desejado))
            previsto = None if desejado is None else dict(desejado, id=identificador, versao=remoto['versao'] + 1 if remoto else 1)
        proximas.append(dict(tabela=tabela, remoto_id=identificador, local_id=ref['local_id'], local=local, remoto=previsto))
    if conflitos:
        raise ErroNuvem('Conflitos de sincronização. Nenhum lote novo foi enviado; os dados locais foram preservados.\n' + '\n'.join(conflitos[:10]))
    return operacoes, proximas


def _aplicar(c, remotos, referencias, usuario_id):
    locais = _locais(c, usuario_id)
    refs = {(r['tabela'], r['remoto_id']): r['local_id'] for r in referencias}
    finais, alteradas = [], 0
    for tabela in TABELAS:
        chave = 'ano' if tabela == 'financeiro_taxas_anuais' else 'id'
        manter = {refs.get((tabela, i)) for i in remotos[tabela]}
        for local_id in set(locais[tabela]) - manter:
            c.execute(f'delete from {tabela} where {chave}=?', (local_id,))
            alteradas += 1
        # Primeiro atualiza os registros já existentes; depois insere os novos.
        for identificador, remoto in sorted(remotos[tabela].items(), key=lambda item: refs.get((tabela, item[0])) is None):
            corpo = _corpo(remoto)
            local_id = refs.get((tabela, identificador))
            existe = local_id in locais[tabela]
            if tabela == 'vendas':
                campos = ('data', 'dinheiro', 'pix', 'cartao')
                valores = [corpo['data'], *[corpo[k + '_centavos'] / 100 for k in ('dinheiro', 'pix', 'cartao')]]
            else:
                campos = COLUNAS[tabela]
                valores = [corpo[k] for k in campos]
            if existe:
                if locais[tabela][local_id] != corpo:
                    c.execute(f'update {tabela} set ' + ','.join(k + '=?' for k in campos) + f' where {chave}=?', (*valores, local_id))
                    alteradas += 1
            else:
                cursor = c.execute(f'insert into {tabela} (' + ','.join(campos) + ') values (' + ','.join('?' for _ in campos) + ')', valores)
                local_id = cursor.lastrowid
                alteradas += 1
            if tabela == 'financeiro_taxas_anuais':
                local_id = corpo['ano']
            finais.append(dict(tabela=tabela, remoto_id=identificador, local_id=local_id, local=corpo, remoto=remoto))
    # Verifica novamente as regras monetárias, datas, parcelas e sobreposições.
    atuais = _locais(c, usuario_id)
    for tabela in TABELAS:
        referencias_tabela = [r for r in finais if r['tabela'] == tabela]
        if len(atuais[tabela]) != len(referencias_tabela) or any(atuais[tabela].get(r['local_id']) != r['local'] for r in referencias_tabela):
            raise ErroNuvem('A conferência do banco local divergiu. Recebimento cancelado; tente sincronizar novamente.')
    _salvar_referencias(c, finais)
    return alteradas


def _assinatura_base(c):
    estado = c.execute('select projeto,usuario_id,pendente from nuvem_sync_estado where singleton=1').fetchone()
    if not estado:
        return None
    registros = [tuple(r) for r in c.execute('select tabela,remoto_id,local_id,base_local,base_remota from nuvem_sync_registros order by tabela,remoto_id')]
    return migracao.assinatura([tuple(estado), registros])


def assinatura_base(banco):
    with closing(sqlite3.connect(Path(banco).resolve().as_uri() + '?mode=ro', uri=True)) as c:
        c.execute('BEGIN')
        return _assinatura_base(c)


def _sem_mudancas(banco, cliente, sessao, resposta, base_inicial=None):
    remotos = validar_snapshot(resposta, sessao.usuario_id)
    with closing(sqlite3.connect(banco.resolve().as_uri() + '?mode=ro', uri=True)) as c:
        c.execute('BEGIN')
        if base_inicial is not None and _assinatura_base(c) != base_inicial:
            return False
        estado = c.execute('select projeto,usuario_id,pendente from nuvem_sync_estado where singleton=1').fetchone()
        if not estado or estado[0] != cliente.url or estado[1] != sessao.usuario_id or estado[2]:
            return False
        locais, referencias = _locais(c, sessao.usuario_id), _referencias(c)
        for tabela in TABELAS:
            refs = [r for r in referencias if r['tabela'] == tabela]
            if len(refs) != len(locais[tabela]) or len(refs) != len(remotos[tabela]):
                return False
            for r in refs:
                remoto = remotos[tabela].get(r['remoto_id'])
                if remoto is None or r['local_id'] not in locais[tabela] or not (r['local'] == _corpo(r['remoto']) == locais[tabela][r['local_id']] == _corpo(remoto)):
                    return False
        return True


def sincronizar(banco, cliente, sessao, snapshot_inicial=None, somente_se_mudou=False, base_inicial=None):
    banco = Path(banco)
    if somente_se_mudou and snapshot_inicial is not None and _sem_mudancas(banco, cliente, sessao, snapshot_inicial, base_inicial):
        return dict(backup=None, enviadas=0, recebidas=0, retomada=False,
                    registros={t: len(snapshot_inicial['dados'][t]) for t in TABELAS})
    backup = criar_backup(banco, 'antes-sincronizacao')
    enviadas, retomada = 0, False
    with closing(sqlite3.connect(banco.resolve().as_uri() + '?mode=rw', uri=True, timeout=5)) as c:
        try:
            c.execute('BEGIN IMMEDIATE')
            _estrutura(c)
            if base_inicial is not None and _assinatura_base(c) != base_inicial:
                snapshot_inicial = None  # Outra instância avançou a base durante a consulta.
            estado = c.execute('select projeto,usuario_id,pendente from nuvem_sync_estado where singleton=1').fetchone()
            retomada = bool(estado and estado[2])
            if estado and (estado[0] != cliente.url or estado[1] != sessao.usuario_id):
                raise ErroNuvem('Este banco já está vinculado a outra conta ou projeto. A sincronização foi bloqueada.')
            if not estado:
                remotos = validar_snapshot(cliente.sincronizar(sessao), sessao.usuario_id)
                referencias = _vincular(_locais(c, sessao.usuario_id), remotos, sessao.usuario_id)
                _salvar_referencias(c, referencias)
                c.execute('insert into nuvem_sync_estado values(1,?,?,null)', (cliente.url, sessao.usuario_id))
                c.commit()
                c.execute('BEGIN IMMEDIATE')
            # Cada tentativa reconhecida atualiza bases, nunca os valores locais
            # antes da comparação com eventuais edições feitas durante uma falha.
            for tentativa in range(4):
                pendente = c.execute('select pendente from nuvem_sync_estado where singleton=1').fetchone()[0]
                if pendente:
                    p = json.loads(pendente)
                    try:
                        resposta = cliente.sincronizar(sessao, p['alteracoes'], p['id'])
                    except LoteRecusado:
                        # A recusa SQL cancela este lote inteiro. Libera a
                        # tentativa recusada para uma nova comparação.
                        c.execute('update nuvem_sync_estado set pendente=null where singleton=1')
                        c.commit()
                        raise
                    remotos = validar_snapshot(resposta, sessao.usuario_id, p['id'])
                    _salvar_referencias(c, p['referencias'])
                    c.execute('update nuvem_sync_estado set pendente=null where singleton=1')
                    c.commit()
                    c.execute('BEGIN IMMEDIATE')
                    enviadas += len(p['alteracoes'])
                else:
                    resposta = snapshot_inicial if snapshot_inicial is not None else cliente.sincronizar(sessao)
                    snapshot_inicial = None
                    remotos = validar_snapshot(resposta, sessao.usuario_id)
                locais = _locais(c, sessao.usuario_id)
                operacoes, referencias = planejar(locais, remotos, _referencias(c))
                if not operacoes:
                    recebidas = _aplicar(c, remotos, referencias, sessao.usuario_id)
                    c.commit()
                    return dict(backup=str(backup), enviadas=enviadas, recebidas=recebidas, retomada=retomada, registros={t: len(remotos[t]) for t in TABELAS})
                p = dict(id=str(uuid4()), alteracoes=operacoes, referencias=referencias)
                c.execute('update nuvem_sync_estado set pendente=? where singleton=1', (_json(p),))
                c.commit()  # Persistido antes da chamada: uma queda não perde o lote.
                c.execute('BEGIN IMMEDIATE')
            raise ErroNuvem('Há muitas mudanças simultâneas. Os dados foram preservados; clique em Sincronizar agora novamente.')
        finally:
            c.rollback()


def vinculado(banco):
    try:
        with closing(sqlite3.connect(Path(banco).resolve().as_uri() + '?mode=ro', uri=True)) as c:
            return c.execute('select 1 from nuvem_sync_estado where singleton=1').fetchone() is not None
    except sqlite3.Error:
        return False
