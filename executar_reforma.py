"""Entrada separada da Etapa 4. Nunca substitui executar.py nem abre dados pessoais."""
import argparse
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pasta-estudo', type=Path, help='Pasta vazia/separada para conservar apenas os testes.')
    parser.add_argument('--exemplo', action='store_true', help='Inclui exemplos fictícios somente se o banco estiver vazio.')
    parser.add_argument('--pagina', choices=['Vendas', 'Análises', 'Finanças'], default='Vendas', help='Tela inicial da revisão isolada.')
    parser.add_argument('--captura', type=Path, help='Salva uma captura e fecha; não entra no loop interativo.')
    args = parser.parse_args()
    temporaria = tempfile.TemporaryDirectory(prefix='gestao-feira-qt-') if args.pasta_estudo is None else None
    try:
        from reforma_desktop.ambiente import preparar
        pasta = preparar(args.pasta_estudo or temporaria.name)
        # Recursos/componentes aprovados permanecem compartilhados com a demo.
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'prototipos/reforma'))
        try:
            from reforma_desktop.aplicacao import iniciar
        except ModuleNotFoundError as erro:
            if erro.name != 'PySide6':
                raise
            print('Instale no mesmo Python: python -m pip install -r prototipos/reforma/requirements.txt', file=sys.stderr)
            return 1
        return iniciar(pasta, args.exemplo, args.captura, args.pagina)
    except (ValueError, OSError, RuntimeError) as erro:
        print(f'Não foi possível abrir o estudo: {erro}', file=sys.stderr)
        return 1
    finally:
        if temporaria:
            temporaria.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
