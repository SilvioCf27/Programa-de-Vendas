"""Leitura defensiva de backups. Integridade não comprova a autoria do arquivo."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
import sqlite3
import tempfile
import time
from ProgramFeira.database.seguranca_arquivos import sem_redirecionamentos

MAX_BACKUP_BYTES = 256 * 1024 * 1024
TEMPO_ANALISE = 10
MIN_SQLITE = (3, 50, 2)


def _em_uso(caminho):
    return any(Path(str(caminho) + s).exists() for s in ('-wal', '-shm', '-journal'))


def _hash_limitado(caminho):
    digest = hashlib.sha256()
    quantidade = 0
    with Path(caminho).open('rb') as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b''):
            quantidade += len(bloco)
            if quantidade > MAX_BACKUP_BYTES:
                raise ValueError('O backup excede o limite de análise de 256 MiB.')
            digest.update(bloco)
    return digest.digest()


@contextmanager
def leitura_sqlite(caminho):
    if sqlite3.sqlite_version_info < MIN_SQLITE:
        raise RuntimeError('Para analisar backups com segurança, atualize o executável ou use Python com SQLite 3.50.2 ou mais recente. O banco atual foi preservado.')
    conexao = sqlite3.connect(Path(caminho).resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
    try:
        conexao.execute('PRAGMA trusted_schema=OFF')
        conexao.execute('PRAGMA query_only=ON')
        # Não registra funções externas nem habilita extensões SQLite.
        conexao.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 16 * 1024 * 1024)
        conexao.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 256 * 1024)
        limite = time.monotonic() + TEMPO_ANALISE
        conexao.set_progress_handler(lambda: int(time.monotonic() > limite), 1000)
        def autorizar(acao, primeiro, segundo, banco, origem):
            if acao in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
                return sqlite3.SQLITE_DENY
            if acao == sqlite3.SQLITE_FUNCTION and str(segundo).lower() in ('load_extension', 'readfile', 'writefile'):
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        conexao.set_authorizer(autorizar)
        yield conexao
    finally:
        conexao.close()


def validar_estrutura(conexao):
    objetos = conexao.execute('SELECT type,name,sql FROM sqlite_master').fetchall()
    for tipo, nome, sql in objetos:
        sem_comentarios = re.sub(r'/\*.*?\*/|--[^\r\n]*', ' ', sql or '', flags=re.S)
        if tipo in ('view', 'trigger') or re.match(r'\s*CREATE\s+VIRTUAL\s+TABLE\b', sem_comentarios, flags=re.I):
            raise ValueError('Backup recusado: contém gatilhos, consultas salvas ou tabelas virtuais que não fazem parte do programa. Nenhum dado foi restaurado.')
    if not any(tipo == 'table' and nome == 'vendas' for tipo, nome, _ in objetos):
        raise ValueError('O backup precisa conter uma tabela de vendas normal e compatível.')
    from ProgramFeira.database.armazenamento import validar
    validar(conexao)


def conferir_backup_local(caminho):
    with leitura_sqlite(caminho) as conexao:
        validar_estrutura(conexao)


@contextmanager
def abrir_backup_externo(origem):
    origem = sem_redirecionamentos(origem)
    if not origem.is_file():
        raise ValueError('Selecione um arquivo de backup regular.')
    if origem.stat().st_size > MAX_BACKUP_BYTES:
        raise ValueError('O backup excede o limite de análise de 256 MiB.')
    if _em_uso(origem):
        raise ValueError('Selecione um backup concluído, sem arquivos auxiliares de um banco aberto.')
    with tempfile.TemporaryDirectory(prefix='feira-leitura-backup-') as pasta:
        local = Path(pasta) / 'backup.db'
        digest = hashlib.sha256()
        quantidade = 0
        # SQLite nunca abre o arquivo na unidade virtual do Drive.
        with origem.open('rb') as entrada, local.open('xb') as saida:
            if entrada.read(16) != b'SQLite format 3\x00':
                raise sqlite3.DatabaseError('O arquivo não é um backup SQLite compatível.')
            entrada.seek(0)
            for bloco in iter(lambda: entrada.read(1024 * 1024), b''):
                quantidade += len(bloco)
                if quantidade > MAX_BACKUP_BYTES:
                    raise ValueError('O backup excede o limite de análise de 256 MiB.')
                digest.update(bloco)
                saida.write(bloco)
        sem_redirecionamentos(origem)
        if _em_uso(origem) or _hash_limitado(origem) != digest.digest() or _hash_limitado(local) != digest.digest():
            raise ValueError('O arquivo mudou durante a leitura. Aguarde a sincronização terminar e tente novamente.')
        conferir_backup_local(local)
        yield local
