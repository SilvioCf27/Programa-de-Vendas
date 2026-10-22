"""Registra somente versão, tipo e posições do erro, sem mensagens ou variáveis."""
from datetime import datetime
import json
from pathlib import Path
import threading
import traceback
from ProgramFeira.versao import VERSAO

_TRAVA = threading.Lock()


def registrar(erro, pasta):
    frames = traceback.extract_tb(erro.__traceback__)[-32:]
    registro = {'data': datetime.now().astimezone().isoformat(), 'versao': VERSAO, 'tipo': type(erro).__name__,
                'pilha': [{'arquivo': Path(f.filename).name, 'funcao': f.name, 'linha': f.lineno} for f in frames]}
    try:
        with _TRAVA:
            caminho = Path(pasta) / 'logs/erros.jsonl'
            caminho.parent.mkdir(parents=True, exist_ok=True)
            if caminho.exists() and caminho.stat().st_size >= 1024 * 1024:
                caminho.replace(caminho.with_suffix('.anterior.jsonl'))
            with caminho.open('a', encoding='utf-8') as arquivo:
                arquivo.write(json.dumps(registro, ensure_ascii=False) + '\n')
        return True
    except OSError:
        return False
