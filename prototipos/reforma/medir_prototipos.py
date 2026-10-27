"""Três execuções de cada estudo, em processos novos, sem captura na medição."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
resultados = []
with tempfile.TemporaryDirectory(prefix="feira-estudo-medicoes-") as tmp:
    for script in ("tkinter_demo.py", "pyside_demo.py"):
        for repeticao in range(1, 4):
            saida = Path(tmp) / "resultado.json"
            env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / script),
                    "--testar",
                    "--relatorio",
                    str(saida),
                ],
                env=env,
                check=True,
                timeout=30,
            )
            r = json.loads(saida.read_text())
            r["repeticao"] = repeticao
            resultados.append(r)
r = dict(
    data_utc=datetime.now(timezone.utc).isoformat(),
    python=sys.version.split()[0],
    plataforma=platform.system() + " " + platform.machine(),
    dimensoes=[1440, 960],
    escala_estudo="96 DPI; não valida escalas do Windows",
    fonte="Segoe UI no Windows; DejaVu Sans no Linux",
    observacao="Inicialização até primeira exibição, antes dos testes e capturas. Exclui o início do processo Python. RSS antes dos testes. Protótipos não têm a lógica inteira nem rede/banco; não comparar como substitutos do programa completo.",
    resultados=resultados,
)
(ROOT / "PROTOTIPOS_MEDICOES.json").write_text(
    json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Medições dos estudos gravadas.")
