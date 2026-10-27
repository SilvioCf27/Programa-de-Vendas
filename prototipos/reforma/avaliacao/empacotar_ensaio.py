"""Pacotes descartáveis dos ensaios. Não compila nem publica Gestão da Feira."""

import argparse
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--saida", required=True)
    args = p.parse_args()
    dest = Path(args.saida).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    reports = []
    for tool, name in [("tk", "EnsaioTk"), ("qt", "EnsaioQt")]:
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--console",
            "--name",
            name,
            "--distpath",
            str(dest / "pacotes"),
            "--workpath",
            str(dest / "build" / tool),
            "--specpath",
            str(dest / "spec"),
            "--add-data",
            str(ROOT.parent / "recursos") + os.pathsep + "recursos",
            "--exclude-module",
            "PySide6" if tool == "tk" else "tkinter",
            "--exclude-module",
            "PyQt5",
            "--exclude-module",
            "PyQt6",
            str(ROOT / f"entrada_{tool}.py"),
        ]
        inicio = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
        (dest / f"build-{tool}.log").write_text(
            r.stdout + "\n" + r.stderr, encoding="utf-8"
        )
        if r.returncode:
            raise RuntimeError(f"Empacotamento {tool} falhou; veja build-{tool}.log")
        pasta = dest / "pacotes" / name
        binary = pasta / (name + ".exe" if sys.platform == "win32" else name)
        resultado = dest / f"autoteste-{tool}.json"
        env = {**os.environ}
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        # PATH evita depender do venv para achar executáveis, DLLs ou scripts.
        if sys.platform == "win32":
            env["PATH"] = os.pathsep.join(
                [
                    str(Path(os.environ["SystemRoot"]) / "System32"),
                    os.environ["SystemRoot"],
                ]
            )
        else:
            env["PATH"] = "/usr/bin:/bin"
            env["QT_QPA_PLATFORM"] = "offscreen"
        for key in ["PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"]:
            env.pop(key, None)
        test = subprocess.run(
            [
                str(binary),
                "--volume",
                "224",
                "--ciclos",
                "5",
                "--saida",
                str(resultado),
            ],
            cwd=dest,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if test.returncode:
            raise RuntimeError(f"Pacote {tool} não abriu: " + test.stderr[-2000:])
        data = json.loads(resultado.read_text(encoding="utf-8"))
        assert (
            data["frozen"] and data["registros"] == 224 and data["teclado"]["selecao"]
        )
        files = [f for f in pasta.rglob("*") if f.is_file()]
        bytes_total = sum(f.stat().st_size for f in files)
        zip_path = Path(shutil.make_archive(str(dest / name), "zip", pasta))
        licencas = [
            str(f.relative_to(pasta))
            for f in files
            if any(w in f.name.lower() for w in ["license", "copying", "copyright"])
        ]
        reports.append(
            dict(
                ferramenta=tool,
                plataforma=sys.platform,
                build_segundos=round(time.perf_counter() - inicio, 2),
                arquivos=len(files),
                bytes_instalados=bytes_total,
                bytes_zip=zip_path.stat().st_size,
                autoteste=data,
                avisos_licenca_incluidos=licencas,
                observacao="Mesmo ensaio técnico e mesmos recursos; não é o executável final. PATH limpo, mas não é máquina física sem Python instalado.",
            )
        )
        print("Pacote de estudo validado: " + tool, flush=True)
    (dest / "EMPACOTAMENTO.json").write_text(
        json.dumps(
            dict(pacotes=reports, pyinstaller=distribution("pyinstaller").version),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
