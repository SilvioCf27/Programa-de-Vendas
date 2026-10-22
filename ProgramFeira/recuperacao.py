"""Ensaio de restauração em pasta temporária; não altera o banco em uso."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from ProgramFeira.database.armazenamento import copiar_verificado, restaurar_backup, validar


def _hash_arquivo(caminho):
    resumo = hashlib.sha256()
    with Path(caminho).open('rb') as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b''):
            resumo.update(bloco)
    return resumo.hexdigest()


def _conteudo(caminho):
    with closing(sqlite3.connect(Path(caminho).resolve().as_uri() + '?mode=ro', uri=True)) as c:
        validar(c)
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
    if any(Path(str(origem) + sufixo).exists() for sufixo in ('-wal', '-shm', '-journal')):
        raise ValueError('Selecione uma cópia de backup concluída, não um banco aberto em outro programa.')
    assinatura = _hash_arquivo(origem)
    with tempfile.TemporaryDirectory(prefix='feira-recuperacao-') as pasta:
        # Drive virtual recebe apenas leitura de arquivo comum. SQLite só acessa a cópia local.
        local = Path(pasta) / 'backup.db'
        shutil.copyfile(origem, local)
        em_uso = any(Path(str(origem) + sufixo).exists() for sufixo in ('-wal', '-shm', '-journal'))
        if em_uso or _hash_arquivo(local) != assinatura or _hash_arquivo(origem) != assinatura:
            raise ValueError('O arquivo mudou durante a leitura. Aguarde a cópia/sincronização terminar e tente novamente.')
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
