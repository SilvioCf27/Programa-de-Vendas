"""Ensaio de restauração em pasta temporária; não altera o banco em uso."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from ProgramFeira.database.armazenamento import copiar_verificado, restaurar_backup
from ProgramFeira.database.entrada_backup import abrir_backup_externo, leitura_sqlite, validar_estrutura


def _hash_arquivo(caminho):
    resumo = hashlib.sha256()
    with Path(caminho).open('rb') as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b''):
            resumo.update(bloco)
    return resumo.hexdigest()


def _conteudo(caminho):
    with leitura_sqlite(caminho) as c:
        validar_estrutura(c)
        estrutura = c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        tabelas = {}
        resumo = hashlib.sha256(repr(estrutura).encode('utf-8'))
        for (nome,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            seguro = '"' + nome.replace('"', '""') + '"'
            linhas = sorted(repr(r) for r in c.execute('SELECT * FROM ' + seguro))
            tabelas[nome] = len(linhas)
            resumo.update(json.dumps([nome, linhas], ensure_ascii=False).encode('utf-8'))
        return dict(tabelas=tabelas, assinatura=resumo.hexdigest())


def testar_recuperacao(origem):
    origem = Path(origem)
    with abrir_backup_externo(origem) as local, tempfile.TemporaryDirectory(prefix='feira-recuperacao-') as pasta:
        assinatura = _hash_arquivo(local)
        esperado = _conteudo(local)
        destino = Path(pasta) / 'vendas.db'
        copiar_verificado(local, destino)
        # Simula um banco alterado e verifica a preservação dele na restauração real.
        with closing(sqlite3.connect(destino)) as c, c:
            c.execute('DELETE FROM vendas')
        anterior = _conteudo(destino)
        copia_anterior = restaurar_backup(destino, local)
        if _conteudo(copia_anterior) != anterior or _conteudo(destino) != esperado:
            raise ValueError('O ensaio de restauração não preservou todos os dados; não utilize esta cópia para recuperar o banco.')
    return dict(sucesso=True, arquivo=str(origem), sha256=assinatura, **esperado)
