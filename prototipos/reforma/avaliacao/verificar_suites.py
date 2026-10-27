"""Executa testes existentes em diretório de dados temporário e registra evidência."""

import argparse
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]

p = argparse.ArgumentParser()
p.add_argument("--suite", choices=["tests", "prototipos/reforma"], required=True)
p.add_argument("--saida", required=True)
args = p.parse_args()
with tempfile.TemporaryDirectory(prefix="feira-suite-tecnica-") as temp:
    os.environ["PROGRAMFEIRA_DATA_DIR"] = temp
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / args.suite), pattern="test_*.py"
    )
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    d = dict(
        suite=args.suite,
        plataforma=sys.platform,
        python=platform.python_version(),
        sqlite=sqlite3.sqlite_version,
        executados=resultado.testsRun,
        aprovados=resultado.testsRun
        - len(resultado.failures)
        - len(resultado.errors)
        - len(resultado.skipped),
        falhas=[dict(teste=str(t), erro=erro) for t, erro in resultado.failures],
        erros=[dict(teste=str(t), erro=erro) for t, erro in resultado.errors],
        ignorados=[dict(teste=str(t), motivo=m) for t, m in resultado.skipped],
        sucesso=resultado.wasSuccessful(),
        dados="Diretório temporário descartado; sem contas configuradas.",
    )
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
    )
sys.exit(0 if d["sucesso"] else 1)
