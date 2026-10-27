"""Suítes isoladas da Etapa 4 com relatório legível e dados temporários."""
import argparse
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite', choices=['reforma_desktop/tests', 'tests', 'prototipos/reforma'], default='reforma_desktop/tests')
    p.add_argument('--saida', type=Path, required=True)
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix='feira-validacao-qt-') as pasta:
        os.environ['PROGRAMFEIRA_DATA_DIR'] = pasta
        sys.path.insert(0, str(ROOT))
        suite = unittest.defaultTestLoader.discover(str(ROOT / args.suite), pattern='test_*.py')
        r = unittest.TextTestRunner(verbosity=2).run(suite)
        resultado = dict(suite=args.suite, plataforma=platform.platform(), python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                         executados=r.testsRun, aprovados=r.testsRun - len(r.failures) - len(r.errors) - len(r.skipped),
                         falhas=[dict(teste=str(t), erro=e) for t, e in r.failures],
                         erros=[dict(teste=str(t), erro=e) for t, e in r.errors],
                         ignorados=[dict(teste=str(t), motivo=e) for t, e in r.skipped], sucesso=r.wasSuccessful(),
                         dados='Somente diretórios temporários. Sem conta, nuvem ou banco pessoal.')
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if resultado['sucesso'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
