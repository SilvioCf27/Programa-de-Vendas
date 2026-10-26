"""Preferências visuais independentes do banco de vendas."""
import json
import os
from pathlib import Path
import tempfile


def carregar_periodo_inicial(pasta):
    from ProgramFeira.semanas import PERIODOS_INICIAIS
    try:
        valor = json.loads((Path(pasta) / 'inicio.json').read_text(encoding='utf-8')).get('periodo')
        return valor if valor in PERIODOS_INICIAIS else 'Fechamento atual'
    except (OSError, ValueError, AttributeError):
        return 'Fechamento atual'


def salvar_periodo_inicial(pasta, periodo):
    from ProgramFeira.semanas import PERIODOS_INICIAIS
    if periodo not in PERIODOS_INICIAIS:
        raise ValueError('Período inicial inválido.')
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=pasta, prefix='.inicio-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as arquivo:
            json.dump({'periodo': periodo}, arquivo, ensure_ascii=False)
        os.replace(temporario, pasta / 'inicio.json')
    finally:
        Path(temporario).unlink(missing_ok=True)


def carregar_tema(pasta):
    try:
        valor = json.loads((Path(pasta) / 'preferencias.json').read_text(encoding='utf-8')).get('tema')
        return valor if valor in ('claro', 'escuro', 'grafite', 'areia', 'aurora') else 'escuro'
    except (OSError, ValueError, AttributeError):
        return 'escuro'


def salvar_tema(pasta, tema):
    if tema not in ('claro', 'escuro', 'grafite', 'areia', 'aurora'):
        raise ValueError('Tema inválido')
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=pasta, prefix='.preferencias-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as arquivo:
            json.dump({'tema': tema}, arquivo)
        os.replace(temporario, pasta / 'preferencias.json')
    finally:
        Path(temporario).unlink(missing_ok=True)
