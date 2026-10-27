"""Entrada de estudo: somente pasta vazia ou criada por esta implementação."""
import os
from pathlib import Path

MARCADOR = '.gestao-feira-estudo-qt'
CONTEUDO = 'Gestão da Feira — banco fictício isolado, Etapa 4\n'


def preparar(pasta):
    # Executado antes de importar módulos que capturam o caminho do banco.
    from ProgramFeira.database.armazenamento import pasta_dados
    destino = Path(pasta).expanduser().resolve()
    pessoal = pasta_dados().resolve()
    if destino == pessoal or pessoal in destino.parents or destino in pessoal.parents:
        raise ValueError('A pasta de estudo deve ficar separada dos dados do programa estável.')
    destino.mkdir(parents=True, exist_ok=True)
    marcador = destino / MARCADOR
    if any(destino.iterdir()):
        if not marcador.is_file() or marcador.read_text(encoding='utf-8') != CONTEUDO:
            raise ValueError('Use uma pasta vazia. Não abra nem copie seu banco pessoal nesta etapa.')
    else:
        marcador.write_text(CONTEUDO, encoding='utf-8')
    os.environ['PROGRAMFEIRA_DATA_DIR'] = str(destino)
    return destino
