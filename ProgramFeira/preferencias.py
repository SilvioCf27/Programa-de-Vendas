"""Preferências visuais independentes do banco de vendas."""
import json
import os
from pathlib import Path
import tempfile


def carregar_tema(pasta):
    try:
        valor = json.loads((Path(pasta) / 'preferencias.json').read_text(encoding='utf-8')).get('tema')
        return valor if valor in ('claro', 'escuro') else 'escuro'
    except (OSError, ValueError, AttributeError):
        return 'escuro'


def salvar_tema(pasta, tema):
    if tema not in ('claro', 'escuro'):
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
