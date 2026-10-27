"""Orquestra processos novos e alterna ferramentas para reduzir viés de ordem."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--saida", required=True)
    p.add_argument("--repeticoes", type=int, default=5)
    p.add_argument("--volumes", nargs="+", type=int, default=[224, 5000])
    p.add_argument("--uia", action="store_true")
    args = p.parse_args()
    todos = []
    with tempfile.TemporaryDirectory(prefix="feira-comparacao-") as temp:
        for n in args.volumes:
            for rep in range(args.repeticoes):
                ferramentas = ["tk", "qt"] if rep % 2 == 0 else ["qt", "tk"]
                for ferramenta in ferramentas:
                    path = Path(temp) / "resultado.json"
                    cmd = [
                        sys.executable,
                        str(ROOT / f"entrada_{ferramenta}.py"),
                        "--volume",
                        str(n),
                        "--saida",
                        str(path),
                    ]
                    env = {**os.environ}
                    if sys.platform != "win32":
                        env["QT_QPA_PLATFORM"] = "offscreen"
                    inicio = time.perf_counter()
                    r = subprocess.run(
                        cmd, env=env, capture_output=True, text=True, timeout=120
                    )
                    if r.returncode:
                        raise RuntimeError(f"{ferramenta} falhou: " + r.stderr[-4000:])
                    d = json.loads(path.read_text(encoding="utf-8"))
                    d["repeticao"] = rep + 1
                    d["processo_total_ms"] = round(
                        (time.perf_counter() - inicio) * 1000, 3
                    )
                    todos.append(d)
                    print(
                        f"{platform.system()} volume {n} repetição {rep+1} {ferramenta}: concluído",
                        flush=True,
                    )
                par = todos[-2:]
                assert par[0]["sha_dados"] == par[1]["sha_dados"]
                assert par[0]["total_centavos"] == par[1]["total_centavos"]
                assert all(x["teclado"]["selecao"] for x in par)
        probes = []
        if args.uia:
            for ferramenta in ("tk", "qt"):
                path = Path(temp) / "uia.json"
                r = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / f"entrada_{ferramenta}.py"),
                        "--volume",
                        "224",
                        "--ciclos",
                        "1",
                        "--uia",
                        "--saida",
                        str(path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                probes.append(
                    json.loads(path.read_text(encoding="utf-8"))
                    if r.returncode == 0
                    else dict(ferramenta=ferramenta, erro=r.stderr[-2000:])
                )
    result = dict(
        data_utc=datetime.now(timezone.utc).isoformat(),
        commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        plataforma=platform.platform(),
        python=platform.python_version(),
        metodo="Mesmo SQLite temporário gerado deterministicamente; mesmas consultas, tabelas e paginação de 50; subprocessos novos alternados. Ensaio técnico, não implementação nem comparação do aplicativo inteiro.",
        repeticoes=args.repeticoes,
        resultados=todos,
        probes_uia=probes,
    )
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
