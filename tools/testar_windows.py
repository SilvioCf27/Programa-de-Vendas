"""Publica falhas dos testes como anotações, além dos logs do Actions."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
resultado = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
falhas = [{'teste': str(teste), 'erro': erro} for teste, erro in resultado.failures + resultado.errors]
(ROOT / 'dist').mkdir(exist_ok=True)
(ROOT / 'dist/TESTES_WINDOWS.json').write_text(json.dumps({'executados': resultado.testsRun, 'falhas': falhas, 'ignorados': [str(t) for t, _ in resultado.skipped]}, ensure_ascii=False, indent=2), encoding='utf-8')
for falha in falhas:
    texto = (falha['teste'] + '\n' + falha['erro']).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error::' + texto, flush=True)
sys.exit(0 if resultado.wasSuccessful() else 1)
