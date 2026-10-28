"""Preparação offline de compatibilidade; nunca ativa conta ou pasta pessoal."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from ProgramFeira import nuvem
from ProgramFeira.database.armazenamento import copiar_verificado, pasta_dados
from ProgramFeira.database.seguranca_arquivos import sem_redirecionamentos
from ProgramFeira.recuperacao import _conteudo, testar_recuperacao
from reforma_desktop.ambiente import MARCADOR, CONTEUDO

ARQUIVOS=('preferencias.json','inicio.json','nuvem.json','backup_drive.json','sincronizacao.json','atualizacoes.json','sessao-nuvem.dpapi')
MARCA_PERFIL='.gestao-feira-perfil-validacao'


def hash_bytes(dados):return hashlib.sha256(dados).hexdigest()


def pasta_segura(caminho):
    p=sem_redirecionamentos(caminho).resolve()
    pessoal=pasta_dados().resolve()
    if p==pessoal or pessoal in p.parents or p in pessoal.parents:
        raise ValueError('Use uma pasta separada dos dados do programa em uso.')
    return p


def ler_configuracoes(origem):
    resultado={}
    for nome in ARQUIVOS:
        p=sem_redirecionamentos(origem/nome)
        if not p.exists():continue
        if not p.is_file() or p.stat().st_size>65536:
            raise ValueError('Arquivo de configuração inválido: '+nome)
        dados=p.read_bytes()
        if nome.endswith('.json'):
            try:
                d=json.loads(dados)
                if not isinstance(d,dict):raise ValueError()
                if nome=='preferencias.json' and d.get('tema') not in ('claro','escuro','grafite','areia','aurora'):raise ValueError()
                if nome=='inicio.json' and d.get('periodo') not in ('Mês atual','Ano atual','Fechamento atual','Todas as vendas'):raise ValueError()
                if nome=='sincronizacao.json' and type(d.get('automatica')) is not bool:raise ValueError()
                if nome=='atualizacoes.json' and type(d.get('consultar')) is not bool:raise ValueError()
                if nome=='backup_drive.json' and not isinstance(d.get('pasta',''),str):raise ValueError()
                if nome=='nuvem.json':nuvem.validar_config(d['url'],d['chave_publica'])
            except (ValueError,TypeError,KeyError):
                raise ValueError('Configuração inválida: '+nome) from None
        resultado[nome]=dados
    return resultado


def escrever_json(p,dados):
    with p.open('x',encoding='utf-8') as f:json.dump(dados,f,ensure_ascii=False,indent=2)


def preparar(origem,destino,url,chave):
    config=nuvem.validar_config(url,chave)
    origem,destino=pasta_segura(origem),pasta_segura(destino)
    if origem==destino or origem in destino.parents or destino in origem.parents:
        raise ValueError('Origem e destino devem ser pastas independentes.')
    if destino.exists():raise ValueError('O destino já existe. Escolha uma pasta nova.')
    marcador=sem_redirecionamentos(origem/MARCADOR)
    if not marcador.is_file() or marcador.read_text(encoding='utf-8')!=CONTEUDO:
        raise ValueError('A origem deve ser uma pasta marcada do estudo, sem dados pessoais.')
    arquivos=ler_configuracoes(origem)
    if 'nuvem.json' in arquivos and json.loads(arquivos['nuvem.json'])['url'].strip().rstrip('/')==config['url']:
        raise ValueError('Use um projeto de teste diferente do projeto de origem.')
    banco=sem_redirecionamentos(origem/'vendas.db')
    antes=_conteudo(banco)
    with closing(sqlite3.connect(banco.as_uri()+'?mode=ro',uri=True)) as c:
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='nuvem_sync_estado'").fetchone():
            if c.execute('SELECT 1 FROM nuvem_sync_estado WHERE projeto=?',(config['url'],)).fetchone():
                raise ValueError('O projeto de teste coincide com o vínculo do banco de origem.')
    destino.parent.mkdir(parents=True,exist_ok=True)
    destino.mkdir(mode=0o700)  # reserva exclusiva: nunca sobrescreve pasta existente
    try:
        with tempfile.TemporaryDirectory(prefix='.preparando-',dir=destino) as temp:
            perfil=Path(temp)/'perfil';perfil.mkdir()
            originais=perfil/'preservados';originais.mkdir()
            copiar_verificado(banco,originais/'vendas.db')
            # O snapshot pode herdar WAL. Finaliza só a cópia antes do ensaio
            # de recuperação, que exige um backup sem arquivos auxiliares.
            with closing(sqlite3.connect(originais/'vendas.db')) as c:
                if c.execute('PRAGMA journal_mode=DELETE').fetchone()[0]!='delete':
                    raise ValueError('Não foi possível finalizar o snapshot local.')
            recuperacao=testar_recuperacao(originais/'vendas.db')
            if _conteudo(originais/'vendas.db')!=antes:raise ValueError('O banco mudou durante a cópia. Feche o estudo e tente novamente.')
            for nome,dados in arquivos.items():
                with (originais/nome).open('xb') as f:f.write(dados)
            ativo=perfil/'aplicacao';ativo.mkdir()
            (ativo/MARCADOR).write_text(CONTEUDO,encoding='utf-8')
            for nome in ('preferencias.json','inicio.json'):
                if nome in arquivos:(ativo/nome).write_bytes(arquivos[nome])
            escrever_json(ativo/'nuvem.json',config)
            escrever_json(ativo/'sincronizacao.json',{'automatica':False})
            escrever_json(ativo/'atualizacoes.json',{'consultar':False})
            escrever_json(ativo/'backup_drive.json',{})
            hashes={p.name:hash_bytes(p.read_bytes()) for p in originais.iterdir()}
            if any(hash_bytes((originais/n).read_bytes())!=hash_bytes(d) for n,d in arquivos.items()):raise ValueError('A cópia das configurações não confere.')
            ativos={p.name:hash_bytes(p.read_bytes()) for p in ativo.iterdir()}
            escrever_json(perfil/'manifesto.json',dict(protocolo=1,preservados=hashes,ativos=ativos,tabelas=recuperacao['tabelas'],assinatura=antes['assinatura']))
            if ler_configuracoes(origem)!=arquivos or _conteudo(banco)!=antes:
                raise ValueError('A origem mudou durante a preparação. Feche o estudo e tente novamente.')
            (perfil/MARCA_PERFIL).write_text('1\n',encoding='ascii')
            os.rename(perfil,destino/'perfil')
        return destino/'perfil'
    except BaseException:
        # Só remove a reserva vazia; nunca apaga conteúdo que não publicou.
        try:destino.rmdir()
        except OSError:pass
        raise


def conferir(perfil):
    perfil=pasta_segura(perfil)
    marca=sem_redirecionamentos(perfil/MARCA_PERFIL)
    if not marca.is_file() or marca.read_text(encoding='ascii')!='1\n':raise ValueError('Perfil de validação incompleto.')
    manifesto=json.loads(sem_redirecionamentos(perfil/'manifesto.json').read_text(encoding='utf-8'))
    if manifesto.get('protocolo')!=1:raise ValueError('Protocolo do perfil inválido.')
    preservados=manifesto.get('preservados',{})
    ativos=manifesto.get('ativos',{})
    obrigatorios={MARCADOR,'nuvem.json','sincronizacao.json','atualizacoes.json','backup_drive.json'}
    if not isinstance(preservados,dict) or not isinstance(ativos,dict) or 'vendas.db' not in preservados or not set(preservados)<=set(ARQUIVOS)|{'vendas.db'} or not obrigatorios<=set(ativos) or not set(ativos)<=obrigatorios|{'preferencias.json','inicio.json'}:
        raise ValueError('Estrutura do manifesto inválida.')
    for grupo,chave in [('preservados','preservados'),('aplicacao','ativos')]:
        pasta=sem_redirecionamentos(perfil/grupo)
        esperados=manifesto[chave]
        if set(p.name for p in pasta.iterdir())!=set(esperados):raise ValueError('Conteúdo do perfil foi alterado.')
        for nome,digest in esperados.items():
            if Path(nome).name!=nome:raise ValueError('Nome inválido no manifesto.')
            p=sem_redirecionamentos(pasta/nome)
            if hash_bytes(p.read_bytes())!=digest:raise ValueError('A verificação do perfil falhou.')
    ativo=perfil/'aplicacao'
    for nome,esperado in [('sincronizacao.json',{'automatica':False}),('atualizacoes.json',{'consultar':False}),('backup_drive.json',{})]:
        if json.loads((ativo/nome).read_text(encoding='utf-8'))!=esperado:
            raise ValueError('As automações do perfil devem permanecer desativadas.')
    return manifesto


def cliente_preparado(perfil):
    conferir(perfil)
    ativo=Path(perfil)/'aplicacao'
    config=nuvem.carregar_config(ativo)
    # Construir o cliente não autentica, não restaura sessão e não faz requisição.
    return nuvem.ClienteNuvem(config['url'],config['chave_publica'])
