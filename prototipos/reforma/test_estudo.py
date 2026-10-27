"""Verificações do estudo; não fazem parte dos testes do executável estável."""

import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from modelo import consultar, indicadores_vendas, resumo_semanal_vendas

ROOT = Path(__file__).resolve().parent


class ModeloTests(unittest.TestCase):
    def test_totais_e_periodos_ficticios_coerentes(self):
        r = consultar()
        self.assertEqual(len(r["linhas"]), 12)
        self.assertEqual(r["saldo"], 66970)
        self.assertEqual(r["despesas"], 132000)
        self.assertEqual(r["taxas"], 1680)
        self.assertEqual(r["bruto"], 200650)
        self.assertEqual(r["saldo"], r["bruto"] - r["taxas"] - r["despesas"])
        self.assertEqual(len(consultar("Semana")["linhas"]), 5)
        self.assertEqual(len(consultar("Mês")["linhas"]), 9)
        self.assertEqual(indicadores_vendas()[0][1], "R$ 2.006,50")
        self.assertEqual(len(resumo_semanal_vendas()), 4)

    def test_demos_nao_importam_programa_banco_ou_rede(self):
        for nome in ("modelo.py", "tkinter_demo.py", "pyside_demo.py"):
            tree = ast.parse((ROOT / nome).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                nomes = []
                if isinstance(node, ast.Import):
                    nomes = [n.name for n in node.names]
                if isinstance(node, ast.ImportFrom):
                    nomes = [node.module or ""]
                self.assertFalse(
                    any(
                        n.startswith(
                            (
                                "ProgramFeira",
                                "sqlite3",
                                "urllib",
                                "requests",
                                "socket",
                                "http",
                            )
                        )
                        for n in nomes
                    ),
                    (nome, nomes),
                )

    def executar(self, arquivo, env):
        with tempfile.TemporaryDirectory() as tmp:
            rel = Path(tmp) / "relatorio.json"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / arquivo),
                    "--testar",
                    "--relatorio",
                    str(rel),
                ],
                env={**os.environ, **env},
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            dados = json.loads(rel.read_text(encoding="utf-8"))
            self.assertEqual(dados["linhas"], 12)
            self.assertGreaterEqual(dados["linhas_visiveis"], 5)
            self.assertGreater(dados["abertura_ms"], 0)

    @unittest.skipUnless(
        os.environ.get("DISPLAY") or sys.platform == "win32",
        "Tk precisa de sessão gráfica",
    )
    def test_navegacao_tk_preserva_selecao_e_consulta(self):
        self.executar("tkinter_demo.py", {})

    @unittest.skipUnless(
        importlib.util.find_spec("PySide6"), "PySide6 é opcional no estudo"
    )
    def test_navegacao_qt_preserva_selecao_e_consulta(self):
        self.executar("pyside_demo.py", {"QT_QPA_PLATFORM": "offscreen"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
