"""Pasta de execução separada do perfil imutável e do programa em uso."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
from reforma_desktop.perfil_validacao import conferir,pasta_segura,ARQUIVOS
from reforma_desktop.ambiente import MARCADOR,CONTEUDO
from ProgramFeira import nuvem
from ProgramFeira.database.seguranca_arquivos import sem_redirecionamentos

MARCA='.gestao-feira-execucao-validacao.json'


def preparar(perfil,pasta):
    perfil,pasta=pasta_segura(perfil),pasta_segura(pasta)
    conferir(perfil)
    if perfil==pasta or perfil in pasta.parents or pasta in perfil.parents:
        raise ValueError('A execução deve ficar separada do perfil imutável.')
    config=nuvem.carregar_config(perfil/'aplicacao')
    esperado={'protocolo':1,'perfil':str(perfil),'manifesto':hashlib.sha256((perfil/'manifesto.json').read_bytes()).hexdigest(),'url':config['url'],'chave_publica':config['chave_publica']}
    if pasta.exists():
        marca=sem_redirecionamentos(pasta/MARCA)
        if not marca.is_file() or json.loads(marca.read_text(encoding='utf-8'))!=esperado:
            raise ValueError('A pasta de execução não pertence a este perfil.')
        for nome in ARQUIVOS:
            sem_redirecionamentos(pasta/nome)
        if nuvem.carregar_config(pasta)!=config:
            raise ValueError('O projeto da execução mudou. Use uma nova preparação.')
        marcador=sem_redirecionamentos(pasta/MARCADOR)
        if not marcador.is_file() or marcador.read_text(encoding='utf-8')!=CONTEUDO:raise ValueError('Pasta de execução inválida.')
        banco=sem_redirecionamentos(pasta/'vendas.db')
        if banco.exists():
            with closing(sqlite3.connect(banco.as_uri()+'?mode=ro',uri=True)) as c:
                for tabela in ('nuvem_sync_estado','fechamento_configuracao'):
                    if c.execute('SELECT 1 FROM sqlite_master WHERE name=?',(tabela,)).fetchone():
                        if c.execute('SELECT 1 FROM '+tabela+' WHERE projeto<>?',(config['url'],)).fetchone():
                            raise ValueError('O banco pertence a outro projeto. Não foi aberto para sincronização.')
        sem_redirecionamentos(pasta/'sessao-nuvem.dpapi')
        return pasta
    pasta.parent.mkdir(parents=True,exist_ok=True)
    pasta.mkdir(mode=0o700)
    try:
        for nome in ('preferencias.json','inicio.json','nuvem.json','backup_drive.json','sincronizacao.json','atualizacoes.json',MARCADOR):
            origem=perfil/'aplicacao'/nome
            if origem.exists():
                with (pasta/nome).open('xb') as f:f.write(origem.read_bytes())
        with (pasta/MARCA).open('x',encoding='utf-8') as f:json.dump(esperado,f,ensure_ascii=False)
    except BaseException:
        # A pasta reservada é nossa; marcador só existe após copiar tudo.
        for p in pasta.iterdir():
            if p.is_file() and not p.is_symlink():p.unlink()
        pasta.rmdir()
        raise
    return pasta
