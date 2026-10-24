"""Localização e cópias verificadas do banco, sem executar ações na importação."""
from contextlib import closing
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def pasta_dados():
    override = os.environ.get('PROGRAMFEIRA_DATA_DIR')
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == 'win32':
        base = os.environ.get('LOCALAPPDATA')
        return (Path(base) if base else Path.home() / 'AppData/Local') / 'ProgramFeira'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/ProgramFeira'
    base = os.environ.get('XDG_DATA_HOME')
    return (Path(base) if base else Path.home() / '.local/share') / 'ProgramFeira'


def validar(conexao):
    if conexao.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('O banco está corrompido; operação cancelada.')
    columns = {r[1] for r in conexao.execute('PRAGMA table_info(vendas)')}
    if not {'id', 'data', 'dinheiro', 'pix', 'cartao'} <= columns:
        raise ValueError('O arquivo não é um banco de vendas compatível.')
    if conexao.execute('SELECT data FROM vendas GROUP BY data HAVING count(*) > 1 LIMIT 1').fetchone():
        raise ValueError('O banco contém datas duplicadas; operação cancelada.')


def copiar_verificado(origem, destino):
    """Snapshot SQLite inclui transações confirmadas, inclusive em modo WAL."""
    origem, destino = Path(origem), Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Arquivo reservado de forma exclusiva: nunca sobrescreve um backup.
    with destino.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(origem.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            validar(src)
            with closing(sqlite3.connect(destino)) as dst:
                src.backup(dst)
                validar(dst)
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    return destino


def criar_backup(caminho, motivo='manual'):
    caminho = Path(caminho)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    destino = caminho.parent / 'backups' / f'vendas-{stamp}-{motivo}-{uuid4().hex[:8]}.db'
    return copiar_verificado(caminho, destino)


def preparar_banco(caminho, origem):
    caminho, origem = Path(caminho), Path(origem)
    if caminho.exists():
        return  # Dados locais sempre têm prioridade sobre o banco do repositório.
    caminho.parent.mkdir(parents=True, exist_ok=True)
    backup = criar_backup_para_migracao(origem, caminho.parent)
    temporario = caminho.with_name(f'.migracao-{uuid4().hex}.db')
    try:
        copiar_verificado(backup, temporario)
        try:
            # Publica apenas se o destino ainda não existir (outra instância).
            os.link(temporario, caminho)
        except FileExistsError:
            pass
    finally:
        temporario.unlink(missing_ok=True)


def criar_backup_para_migracao(origem, pasta):
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    return copiar_verificado(origem, Path(pasta) / 'backups' / f'vendas-{stamp}-migracao-{uuid4().hex[:8]}.db')


def restaurar_backup(caminho, origem):
    from ProgramFeira.database.entrada_backup import abrir_backup_externo
    caminho = Path(caminho)
    temporario = caminho.with_name(f'.restauracao-{uuid4().hex}.db')
    try:
        # Faz uma cópia local e valida a estrutura antes de tocar no banco atual.
        with abrir_backup_externo(origem) as local:
            copiar_verificado(local, temporario)
        backup_anterior = criar_backup(caminho, 'antes-restauracao')
        if any(Path(str(caminho) + suffix).exists() for suffix in ('-wal', '-shm', '-journal')):
            raise RuntimeError('Feche outras instâncias do programa antes de restaurar.')
        os.replace(temporario, caminho)
        return backup_anterior
    finally:
        temporario.unlink(missing_ok=True)
