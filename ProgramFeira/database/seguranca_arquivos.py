"""Verificações locais de caminhos; não isolam um processo já comprometido."""
import os
from pathlib import Path
import stat


def sem_redirecionamentos(caminho):
    caminho = Path(os.path.abspath(Path(caminho).expanduser()))
    for parte in (*reversed(caminho.parents), caminho):
        try:
            info = parte.lstat()
        except FileNotFoundError:
            continue
        # No Windows, rejeita links/junctions, mas permite os outros tipos de
        # reparse point usados por arquivos virtuais dos clientes de nuvem.
        tag = getattr(info, 'st_reparse_tag', 0)
        if stat.S_ISLNK(info.st_mode) or (parte != Path(parte.anchor) and tag in (0xA0000003, 0xA000000C)):
            raise ValueError('O caminho contém um link ou uma pasta redirecionada. Selecione a pasta ou o arquivo real antes de continuar.')
    return caminho
