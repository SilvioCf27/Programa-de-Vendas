"""Cópias SQLite na pasta sincronizada pelo Google Drive para computador.

Confirma a gravação local. A sincronização remota pertence ao cliente do Drive.
"""
import hashlib
import shutil
import sqlite3
import json
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from ProgramFeira.database.armazenamento import criar_backup
from ProgramFeira.database.seguranca_arquivos import sem_redirecionamentos
from ProgramFeira.database.entrada_backup import conferir_backup_local

SUBPASTA = 'Gestao-da-Feira-Backups'
ULTIMO = 'gestao-da-feira-ultimo.db'
VERSAO = re.compile(r'gestao-da-feira-\d{8}T\d{12}Z-[0-9a-f]{8}\.db')
RETENCAO = 7


def carregar_config(pasta):
    arquivo = Path(pasta) / 'backup_drive.json'
    try:
        if not arquivo.exists():
            return {}
        dados = json.loads(arquivo.read_text(encoding='utf-8'))
        if not isinstance(dados, dict) or not isinstance(dados.get('pasta', ''), str):
            raise ValueError('formato inválido')
        return dados
    except (OSError, ValueError) as erro:
        raise ValueError('Não foi possível ler a configuração do backup. Abra Configurações → Backup no Google Drive para reconfigurar.') from erro


def salvar_config(pasta, dados):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    fd, nome = tempfile.mkstemp(dir=pasta, prefix='.backup-drive-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(nome, pasta / 'backup_drive.json')
    finally:
        Path(nome).unlink(missing_ok=True)


def validar_pasta(pasta, banco):
    if not str(pasta).strip():
        raise ValueError('Escolha uma pasta do Google Drive disponível neste computador.')
    raiz = sem_redirecionamentos(pasta)
    if not raiz.is_dir():
        raise ValueError('A pasta selecionada não está disponível. Verifique o Google Drive para computador.')
    destino = raiz if raiz.name == SUBPASTA else raiz / SUBPASTA
    sem_redirecionamentos(destino)
    if destino.resolve() == Path(banco).resolve().parent:
        raise ValueError('A pasta de backup não pode ser a pasta do banco em uso.')
    return destino


def configurar(banco, pasta):
    banco = Path(banco)
    validar_pasta(pasta, banco)
    dados = {'pasta': str(Path(pasta).expanduser().resolve())}
    salvar_config(banco.parent, dados)
    return dados


def desativar(banco):
    salvar_config(Path(banco).parent, {})


def _hash_arquivo(caminho):
    resumo = hashlib.sha256()
    with Path(caminho).open('rb') as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b''):
            resumo.update(bloco)
    return resumo.digest()


def copiar_arquivo_verificado(origem, destino):
    """Transporta um snapshot já íntegro, sem operações SQLite no Drive virtual."""
    resumo = hashlib.sha256()
    with Path(origem).open('rb') as entrada, Path(destino).open('xb') as saida:
        for bloco in iter(lambda: entrada.read(1024 * 1024), b''):
            saida.write(bloco)
            resumo.update(bloco)
        saida.flush()
        os.fsync(saida.fileno())
    if _hash_arquivo(destino) != resumo.digest():
        raise ValueError('A verificação SHA-256 da cópia falhou; arquivo não publicado.')


def _espaco(pasta):
    try:
        return f'{shutil.disk_usage(pasta).free / (1024 ** 3):.2f} GB livres'
    except OSError:
        return 'espaço disponível não pôde ser consultado'


def executar(banco, dados):
    banco = Path(banco)
    if not dados.get('pasta'):
        raise ValueError('O backup no Drive ainda não está configurado.')
    # SQLite trabalha somente no armazenamento local. Unidades virtuais podem
    # rejeitar suas escritas aleatórias/travas mesmo com espaço disponível.
    try:
        local = criar_backup(banco, 'antes-drive')
        conferir_backup_local(local)
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as erro:
        raise OSError(f'Etapa: criar e verificar o backup local.\nPasta: {banco.parent}\n{_espaco(banco.parent)}\nErro original: {erro}') from erro
    destino = validar_pasta(dados['pasta'], banco)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    versao = destino / f'gestao-da-feira-{stamp}-{uuid4().hex[:8]}.db'
    temporario = destino / f'.gestao-da-feira-{uuid4().hex}.tmp'
    avisos = []
    etapa = 'criar a pasta de destino'
    try:
        destino.mkdir(exist_ok=True)
        def conferir_destino():
            if validar_pasta(dados['pasta'], banco) != destino:
                raise ValueError('A pasta de backup mudou durante a cópia.')
            for arquivo in (temporario, versao, destino / ULTIMO):
                sem_redirecionamentos(arquivo)
        conferir_destino()
        etapa = 'copiar e conferir a versão datada na pasta do Drive'
        copiar_arquivo_verificado(local, temporario)
        conferir_destino()
        os.replace(temporario, versao)
        etapa = 'copiar e conferir o arquivo mais recente na pasta do Drive'
        copiar_arquivo_verificado(local, temporario)
        etapa = 'substituir o arquivo mais recente na pasta do Drive'
        conferir_destino()
        os.replace(temporario, destino / ULTIMO)
    except (OSError, ValueError) as erro:
        raise OSError(f'Etapa: {etapa}.\nDestino: {destino}\nBackup local preservado: {local}\nDisco local: {_espaco(banco.parent)}\nUnidade de destino: {_espaco(destino.parent)}\nErro original: {erro}') from erro
    finally:
        try:
            sem_redirecionamentos(temporario)
            temporario.unlink(missing_ok=True)
        except (OSError, ValueError) as erro:
            avisos.append(f'Não foi possível remover o arquivo temporário: {erro}')
    # Limpa somente versões reconhecidas deste recurso, depois da publicação.
    try:
        conferir_destino()
        versoes = sorted((p for p in destino.iterdir() if VERSAO.fullmatch(p.name) and p.is_file()), key=lambda p: p.name, reverse=True)
        for antigo in versoes[RETENCAO:]:
            try:
                conferir_destino()
                sem_redirecionamentos(antigo)
                antigo.unlink()
            except (OSError, ValueError) as erro:
                avisos.append(f'Não foi possível remover a versão antiga {antigo.name}: {erro}')
    except (OSError, ValueError) as erro:
        avisos.append(f'Cópia criada, mas não foi possível listar as versões antigas: {erro}')
    atualizado = dict(dados, ultimo_backup=datetime.now(timezone.utc).isoformat(), ultimo_arquivo=str(destino / ULTIMO))
    try:
        salvar_config(banco.parent, atualizado)
    except OSError as erro:
        avisos.append(f'Cópia criada, mas o horário não pôde ser salvo nas preferências: {erro}')
    return {'arquivo': destino / ULTIMO, 'local': local, 'avisos': avisos}
