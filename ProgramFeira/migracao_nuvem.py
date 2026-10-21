"""Migração inicial por snapshot verificado; não é sincronização contínua."""
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4, uuid5
from ProgramFeira.database.armazenamento import criar_backup
from ProgramFeira.nuvem import ErroNuvem

TABELAS = ('vendas', 'financeiro_lancamentos', 'financeiro_taxas_anuais')


def _data(valor):
    if not isinstance(valor, str):
        raise ErroNuvem('Há uma data inválida no banco local. Corrija antes de migrar.')
    for formato in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            pass
    raise ErroNuvem('Há uma data inválida no banco local. Corrija antes de migrar.')


def _inteiro(valor, minimo=0, maximo=99999999999):
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite() or numero != numero.to_integral_value() or not minimo <= numero <= maximo:
            raise ValueError()
        return int(numero)
    except (ValueError, InvalidOperation):
        raise ErroNuvem('Há um valor monetário ou número de parcela inválido no banco local.') from None


def _centavos(valor):
    try:
        return _inteiro(Decimal(str(valor)) * 100)
    except (InvalidOperation, ValueError):
        raise ErroNuvem('Há um valor de venda inválido ou com mais de duas casas decimais. Nada foi arredondado.') from None


def _texto(valor, limite=None):
    if not isinstance(valor, str) or not valor.strip() or (limite is not None and len(valor) > limite):
        raise ErroNuvem('Há uma descrição ou identificação inválida no financeiro local.')
    return valor


def extrair(conexao, usuario_id):
    """Valida todos os dados; nunca ignora linhas inválidas ou arredonda valores."""
    try:
        namespace = UUID(usuario_id)
        conexao.row_factory = sqlite3.Row
        dados = {t: [] for t in TABELAS}
        datas = set()
        for r in conexao.execute('select * from vendas order by id'):
            dia = _data(r['data'])
            if dia in datas:
                raise ErroNuvem('Há vendas com a mesma data após a conversão. Migração interrompida.')
            datas.add(dia)
            dados['vendas'].append(dict(data=dia, **{campo + '_centavos': _centavos(r[campo]) for campo in ('dinheiro', 'pix', 'cartao')}))
        grupos, taxas = set(), set()
        for r in conexao.execute('select * from financeiro_lancamentos order by id'):
            linha = {k: r[k] for k in ('tipo', 'descricao', 'meio', 'categoria', 'grupo')}
            linha['id'] = str(uuid5(namespace, 'desktop:financeiro_lancamentos:' + str(_inteiro(r['id'], 1, 9223372036854775807))))
            linha['data'] = _data(r['data'])
            linha['valor_centavos'] = _inteiro(r['valor_centavos'], 1)
            linha['parcela'] = _inteiro(r['parcela'], 1, 120)
            linha['parcelas'] = _inteiro(r['parcelas'], 1, 120)
            _texto(linha['descricao'], 200)
            if linha['tipo'] not in ('despesa', 'taxa') or linha['meio'] not in ('Dinheiro', 'Pix', 'Cartão de crédito', 'Outro') or linha['categoria'] not in ('Casa', 'Feira', 'Outros', 'Compromisso inicial'):
                raise ErroNuvem('Há tipo, meio ou categoria inválidos no financeiro local.')
            if linha['parcela'] > linha['parcelas']:
                raise ErroNuvem('Há numeração inválida de parcelas no banco local.')
            if linha['parcelas'] == 1:
                if linha['grupo'] is not None:
                    raise ErroNuvem('Há um grupo de parcelas inconsistente no banco local.')
            else:
                _texto(linha['grupo'], 100)
                if linha['tipo'] != 'despesa' or linha['meio'] != 'Cartão de crédito':
                    raise ErroNuvem('Há parcelamento incompatível com o tipo ou meio de pagamento local.')
                chave = (linha['grupo'], linha['parcela'])
                if chave in grupos:
                    raise ErroNuvem('Há parcelas duplicadas no banco local.')
                grupos.add(chave)
            if linha['tipo'] == 'taxa':
                if linha['data'] in taxas:
                    raise ErroNuvem('Há taxas diárias duplicadas no banco local.')
                taxas.add(linha['data'])
            dados['financeiro_lancamentos'].append(linha)
        anos = set()
        for r in conexao.execute('select * from financeiro_taxas_anuais order by ano'):
            ano = _inteiro(r['ano'], 1, 9999)
            inicio, fim = _data(r['inicio']), _data(r['fim'])
            if ano in anos or int(inicio[:4]) != ano or int(fim[:4]) != ano or inicio > fim:
                raise ErroNuvem('Há um intervalo de taxa anual inválido no banco local.')
            if any(inicio <= dia <= fim for dia in taxas):
                raise ErroNuvem('Há taxas diárias e anuais sobrepostas no banco local. Corrija antes de migrar.')
            anos.add(ano)
            if r['natureza'] not in ('Confirmada', 'Estimada') or not isinstance(r['observacao'], str):
                raise ErroNuvem('Há uma classificação de taxa anual inválida no banco local.')
            dados['financeiro_taxas_anuais'].append(dict(ano=ano, inicio=inicio, fim=fim, valor_centavos=_inteiro(r['valor_centavos'], 1), natureza=r['natureza'], observacao=r['observacao']))
        return dados
    except (sqlite3.Error, KeyError, IndexError, ValueError) as erro:
        if isinstance(erro, ErroNuvem):
            raise
        raise ErroNuvem('O banco local não tem uma estrutura financeira compatível. Atualize o programa antes de migrar.') from None


def assinatura(dados):
    conteudo = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(conteudo.encode('utf-8')).hexdigest()


def resumo(dados):
    vendas = dados['vendas']
    canais = {k: sum(r[k] for r in vendas) for k in ('dinheiro_centavos', 'pix_centavos', 'cartao_centavos')}
    lancamentos = dados['financeiro_lancamentos']
    anos = sorted({int(r['data'][:4]) for r in vendas})
    return dict(
        registros={t: len(dados[t]) for t in TABELAS},
        vendas_por_ano={str(ano): sum(r['data'].startswith(str(ano) + '-') for r in vendas) for ano in anos},
        dias_zerados=sum(not any(r[k] for k in canais) for r in vendas),
        **canais,
        total_centavos=sum(canais.values()),
        despesas_centavos=sum(r['valor_centavos'] for r in lancamentos if r['tipo'] == 'despesa'),
        taxas_diarias_centavos=sum(r['valor_centavos'] for r in lancamentos if r['tipo'] == 'taxa'),
        taxas_anuais_centavos=sum(r['valor_centavos'] for r in dados['financeiro_taxas_anuais']),
    )


def conferir_resposta(dados, resposta, aplicar):
    try:
        if resposta['aplicado'] is not aplicar or set(resposta['dados']) != set(TABELAS) or set(resposta['novos']) != set(TABELAS):
            raise ValueError()
        for tabela in TABELAS:
            locais, remotos = dados[tabela], resposta['dados'][tabela]
            if not isinstance(remotos, list):
                raise ValueError()
            novo = resposta['novos'][tabela]
            if type(novo) is not int or not 0 <= novo <= len(locais):
                raise ValueError()
            campo = {'vendas': 'data', 'financeiro_lancamentos': 'id', 'financeiro_taxas_anuais': 'ano'}[tabela]
            mapa = {r[campo]: r for r in locais}
            if len({r[campo] for r in remotos}) != len(remotos) or any(mapa.get(r[campo]) != r for r in remotos):
                raise ValueError()
            if aplicar:
                if len(locais) != len(remotos):
                    raise ValueError()
            elif len(locais) - len(remotos) != novo:
                raise ValueError()
        return resposta
    except (KeyError, TypeError, ValueError):
        raise ErroNuvem('A resposta da nuvem não corresponde aos registros locais. Operação não confirmada; confira antes de repetir.') from None


def _gravar_relatorio(caminho, dados):
    # O relatório contém contagens e totais, nunca senha, chave ou token.
    temporario = caminho.with_name('.relatorio-' + uuid4().hex + '.json')
    try:
        temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding='utf-8')
        temporario.replace(caminho)
    finally:
        temporario.unlink(missing_ok=True)


def preparar(banco, cliente, sessao):
    banco = Path(banco)
    backup = criar_backup(banco, 'antes-migracao-nuvem')
    with closing(sqlite3.connect(backup.resolve().as_uri() + '?mode=ro', uri=True)) as conexao:
        dados = extrair(conexao, sessao.usuario_id)
    pasta = banco.parent / 'migracoes-nuvem'
    pasta.mkdir(exist_ok=True)
    caminho = pasta / ('conferencia-' + uuid4().hex + '.json')
    relatorio = dict(
        estado='conferencia_iniciada',
        data_utc=datetime.now(timezone.utc).isoformat(),
        backup=str(backup),
        backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
        dados_sha256=assinatura(dados),
        resumo=resumo(dados),
    )
    _gravar_relatorio(caminho, relatorio)
    try:
        resposta = conferir_resposta(dados, cliente.migrar(sessao, dados, False), False)
    except ErroNuvem as erro:
        relatorio.update(estado='conferencia_interrompida', motivo=str(erro))
        _gravar_relatorio(caminho, relatorio)
        raise ErroNuvem(f'{erro}\nBackup preservado: {backup}\nRelatório: {caminho}') from None
    relatorio.update(estado='conferido_sem_transferencia', novos=resposta['novos'])
    _gravar_relatorio(caminho, relatorio)
    return dict(dados=dados, banco=banco, cliente=cliente, sessao=sessao, relatorio=relatorio, caminho=caminho)


def transferir(preparacao):
    p = preparacao
    relatorio = p['relatorio']
    if relatorio['estado'] != 'conferido_sem_transferencia':
        raise ErroNuvem('Faça uma nova conferência antes de tentar a transferência.')
    backup = Path(relatorio['backup'])
    if hashlib.sha256(backup.read_bytes()).hexdigest() != relatorio['backup_sha256']:
        raise ErroNuvem('O backup foi alterado. Faça uma nova conferência antes de migrar.')
    # Impede alterações locais por outra instância durante o envio. Nenhum
    # registro SQLite é modificado por esta transação.
    with closing(sqlite3.connect(p['banco'].resolve().as_uri() + '?mode=rw', uri=True, timeout=5)) as conexao:
        conexao.execute('BEGIN IMMEDIATE')
        try:
            atuais = extrair(conexao, p['sessao'].usuario_id)
            if assinatura(atuais) != relatorio['dados_sha256'] or assinatura(p['dados']) != relatorio['dados_sha256']:
                raise ErroNuvem('O banco local mudou após a conferência. Confira novamente antes de transferir.')
            relatorio['estado'] = 'envio_iniciado_resultado_a_confirmar'
            _gravar_relatorio(p['caminho'], relatorio)
            resposta = conferir_resposta(p['dados'], p['cliente'].migrar(p['sessao'], p['dados'], True), True)
            relatorio.update(estado='transferido_e_validado', concluido_utc=datetime.now(timezone.utc).isoformat(), inseridos=resposta['novos'], resumo_nuvem=resumo(resposta['dados']))
            _gravar_relatorio(p['caminho'], relatorio)
            return relatorio
        finally:
            conexao.rollback()
