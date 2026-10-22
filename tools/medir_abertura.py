"""Mede a primeira exibição e uma nova consulta usando somente dados fictícios."""
import argparse
from contextlib import closing
from datetime import date, timedelta
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def medir(registros):
    with tempfile.TemporaryDirectory(prefix='feira-desempenho-') as pasta:
        os.environ['PROGRAMFEIRA_DATA_DIR'] = pasta
        banco = Path(pasta) / 'vendas.db'
        shutil.copy2(ROOT / 'ProgramFeira/assets/banco_inicial.db', banco)
        with closing(sqlite3.connect(banco)) as conexao, conexao:
            conexao.executemany('INSERT INTO vendas(data,dinheiro,pix,cartao) VALUES (?,?,?,?)',
                ((str(date(2020, 1, 1) + timedelta(days=i)), 80, 30, 40) for i in range(registros)))
        sys.path.insert(0, str(ROOT))
        import tkinter as tk
        inicio = time.perf_counter()
        with patch.object(tk.Tk, 'mainloop'):
            import ProgramFeira.main as app
        try:
            app.janela.update()
            abertura = time.perf_counter() - inicio
            inicio = time.perf_counter()
            app.atualizar_tabela()
            app.janela.update()
            consulta = time.perf_counter() - inicio
        finally:
            app.janela.destroy()
    return {'registros_ficticios': registros, 'primeira_exibicao_s': round(abertura, 3),
            'nova_consulta_s': round(consulta, 3)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registros', type=int, default=224)
    args = parser.parse_args()
    if not 0 <= args.registros <= 20000:
        parser.error('Use entre 0 e 20000 registros.')
    print(json.dumps(medir(args.registros), ensure_ascii=False))
