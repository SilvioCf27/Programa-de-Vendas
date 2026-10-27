"""Fatores de aplicação em Windows/Linux; não muda configurações do monitor."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

pasta = Path(sys.argv[1])
pasta.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parent
runs = []
with tempfile.TemporaryDirectory(prefix="feira-escalas-tecnicas-") as tmp:
    for fator in (1, 1.25, 1.5):
        for tool in ("tk", "qt"):
            path = Path(tmp) / "r.json"
            env = {**os.environ, "QT_SCALE_FACTOR": str(fator)}
            if sys.platform != "win32":
                env["QT_QPA_PLATFORM"] = "offscreen"
            r = subprocess.run(
                [
                    sys.executable,
                    str(root / f"entrada_{tool}.py"),
                    "--volume",
                    "224",
                    "--ciclos",
                    "2",
                    "--escala",
                    str(fator),
                    "--visual",
                    "--saida",
                    str(path),
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=90,
            )
            if r.returncode:
                raise RuntimeError(r.stderr[-3000:])
            d = json.loads(path.read_text(encoding="utf-8"))
            assert len(d["visual"]) == 5 and d["teclado"]["selecao"]
            runs.append(d)
(pasta / "ESCALAS_PALETAS.json").write_text(
    json.dumps(
        dict(
            plataforma=sys.platform,
            observacao="Fatores de aplicação 1/1,25/1,5; não é troca do DPI real do monitor nem teste com leitor de tela.",
            resultados=runs,
        ),
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
