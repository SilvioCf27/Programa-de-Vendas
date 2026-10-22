"""Abrir a versão nova reaproveita dados, vínculo e preferências existentes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AtualizacaoTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'), 'Sem sessão gráfica')
    def test_atualizacao_preserva_vendas_financas_vinculo_e_configuracoes(self):
        codigo = r'''
import sys, os
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'tests')
from dados_ficticios import criar_banco
pasta = Path(os.environ['PROGRAMFEIRA_DATA_DIR'])
banco = criar_banco(pasta/'vendas.db')
from ProgramFeira.database.banco import criar_tabela
from ProgramFeira import financeiro as f, nuvem, sincronizacao as sync
from ProgramFeira.recuperacao import _conteudo
from test_sincronizacao import Servidor, USUARIO
criar_tabela(); f.inicializar()
f.salvar_lancamento('despesa','2030-02-10','Compra ficticia','100,00','Cartão de crédito','Feira',parcelas=3)
f.salvar_taxa_anual(2025,'2025-01-01','2025-12-31','12,34')
servidor = Servidor(banco)
sync.sincronizar(banco,servidor,nuvem.Sessao(USUARIO,'teste@example.invalid','token-ficticio'))
nuvem.salvar_config(pasta,servidor.url,'sb_publishable_apenas_teste')
(pasta/'preferencias.json').write_text('{"tema":"claro"}')
(pasta/'sincronizacao.json').write_text('{"automatica":true}')
antes = _conteudo(banco)
arquivos = {p.name:p.read_bytes() for p in pasta.glob('*.json')}
import tkinter as tk
with patch.object(tk.Tk,'mainloop'):
    import ProgramFeira.main as app
app.janela.update()
app.janela.destroy()
assert _conteudo(banco) == antes
assert {p.name:p.read_bytes() for p in pasta.glob('*.json')} == arquivos
'''
        with tempfile.TemporaryDirectory() as pasta:
            retorno = subprocess.run([sys.executable,'-c',codigo], cwd=ROOT, env={**os.environ,'PROGRAMFEIRA_DATA_DIR':pasta},capture_output=True,text=True,timeout=60)
        self.assertEqual(retorno.returncode,0,retorno.stdout+retorno.stderr)
