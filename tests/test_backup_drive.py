from dados_ficticios import criar_banco
import os
from contextlib import closing
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ProgramFeira import backup_drive as d

ROOT = Path(__file__).resolve().parents[1]


class BackupDriveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.banco = self.raiz / 'dados/vendas.db'
        self.banco.parent.mkdir()
        criar_banco(self.banco)
        self.drive = self.raiz / 'Drive'
        self.drive.mkdir()
        self.config = d.configurar(self.banco, self.drive)

    def test_copia_verificada_inclui_tabelas_financeiras_e_restaura(self):
        with closing(sqlite3.connect(self.banco)) as c, c:
            c.execute('CREATE TABLE financeiro_teste (valor INTEGER)')
            c.execute('INSERT INTO financeiro_teste VALUES (12345)')
        resultado = d.executar(self.banco, self.config)
        with closing(sqlite3.connect(resultado['arquivo'])) as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(c.execute('SELECT count(*) FROM vendas').fetchone()[0], 9)
            self.assertEqual(c.execute('SELECT valor FROM financeiro_teste').fetchone()[0], 12345)
        from ProgramFeira.database.armazenamento import restaurar_backup
        with closing(sqlite3.connect(self.banco)) as c, c:
            c.execute('DELETE FROM vendas')
        restaurar_backup(self.banco, resultado['arquivo'])
        with closing(sqlite3.connect(self.banco)) as c, c:
            self.assertEqual(c.execute('SELECT count(*) FROM vendas').fetchone()[0], 9)
        self.assertTrue(resultado['local'].exists())
        self.assertTrue(d.carregar_config(self.banco.parent)['ultimo_backup'])

    def test_retencao_preserva_outros_arquivos_e_substitui_ultimo(self):
        destino = self.drive / d.SUBPASTA
        destino.mkdir()
        estranho = destino / 'nao-apagar.db'
        estranho.write_bytes(b'outros dados')
        for i in range(9):
            with closing(sqlite3.connect(self.banco)) as c, c:
                c.execute("UPDATE vendas SET dinheiro=? WHERE id=(SELECT min(id) FROM vendas)", (i,))
            resultado = d.executar(self.banco, self.config)
        versoes = [p for p in destino.iterdir() if d.VERSAO.fullmatch(p.name)]
        self.assertEqual(len(versoes), 7)
        self.assertEqual(estranho.read_bytes(), b'outros dados')
        with closing(sqlite3.connect(resultado['arquivo'])) as c:
            self.assertEqual(c.execute('SELECT dinheiro FROM vendas ORDER BY id LIMIT 1').fetchone()[0], 8)
        self.assertFalse(list(destino.glob('*.tmp')))

    def test_pasta_desconectada_nao_e_recriada_e_mantem_copia_local(self):
        self.drive.rmdir()
        with self.assertRaises(ValueError):
            d.executar(self.banco, self.config)
        self.assertFalse(self.drive.exists())
        self.assertTrue(list((self.banco.parent / 'backups').glob('*antes-drive*.db')))

    def test_falha_na_copia_preserva_ultimo_e_versoes(self):
        resultado = d.executar(self.banco, self.config)
        antes = resultado['arquivo'].read_bytes()
        copiar_arquivo = d.copiar_arquivo_verificado
        contador = [0]
        def falhar_na_segunda(origem, destino):
            contador[0] += 1
            if contador[0] == 2:
                raise OSError('disco cheio')
            return copiar_arquivo(origem, destino)
        with patch.object(d, 'copiar_arquivo_verificado', side_effect=falhar_na_segunda):
            with self.assertRaises(OSError):
                d.executar(self.banco, self.config)
        self.assertEqual(resultado['arquivo'].read_bytes(), antes)
        self.assertFalse(list(resultado['arquivo'].parent.glob('*.tmp')))

    def test_falha_backup_local_impede_publicacao(self):
        with patch.object(d, 'criar_backup', side_effect=OSError('backup indisponível')):
            with self.assertRaises(OSError):
                d.executar(self.banco, self.config)
        self.assertFalse((self.drive / d.SUBPASTA).exists())

    def test_configuracao_independente_do_tema_e_desativacao(self):
        from ProgramFeira.preferencias import salvar_tema, carregar_tema
        salvar_tema(self.banco.parent, 'claro')
        d.executar(self.banco, self.config)
        d.desativar(self.banco)
        self.assertEqual(d.carregar_config(self.banco.parent), {})
        self.assertEqual(carregar_tema(self.banco.parent), 'claro')
        self.assertTrue((self.drive / d.SUBPASTA / d.ULTIMO).exists())
        with self.assertRaises(ValueError):
            d.configurar(self.banco, '')

    def test_configuracao_corrompida_avisa(self):
        (self.banco.parent / 'backup_drive.json').write_text('{inválido', encoding='utf-8')
        with self.assertRaises(ValueError):
            d.carregar_config(self.banco.parent)

    def test_falha_na_substituicao_preserva_arquivo_e_nao_poda(self):
        resultado = d.executar(self.banco, self.config)
        antes = resultado['arquivo'].read_bytes()
        substituir = os.replace
        def falhar(origem, destino):
            if Path(destino).name == d.ULTIMO:
                raise PermissionError('arquivo em uso')
            return substituir(origem, destino)
        with patch.object(d.os, 'replace', side_effect=falhar):
            with self.assertRaises(OSError):
                d.executar(self.banco, self.config)
        self.assertEqual(resultado['arquivo'].read_bytes(), antes)
        self.assertFalse(list(resultado['arquivo'].parent.glob('*.tmp')))

    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'), 'Sem sessão gráfica')
    def test_fluxo_grafico_copia_e_fechamento_com_falha(self):
        script = r'''
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from ProgramFeira import backup_drive as d
from ProgramFeira.interface.painel_backup import BackupDrive
root = tk.Tk()
banco = Path(__import__('sys').argv[1])
controlador = BackupDrive(root, banco)
def aguardar():
    limite = time.monotonic() + 5
    while controlador.ocupado and time.monotonic() < limite:
        root.update()
        time.sleep(.01)
    assert not controlador.ocupado
popup = controlador.configurar()
root.update(); assert popup.winfo_viewable(); popup.destroy()
with patch('ProgramFeira.interface.painel_backup.messagebox.showinfo') as info:
    controlador.iniciar()
    aguardar()
    info.assert_called_once()
config = d.carregar_config(banco.parent)
assert Path(config['ultimo_arquivo']).exists()
d.salvar_config(banco.parent, {'pasta': str(banco.parent / 'pasta-ausente')})
with patch('ProgramFeira.interface.painel_backup.messagebox.askyesno', return_value=False) as pergunta:
    controlador.fechar()
    aguardar()
    pergunta.assert_called_once()
assert root.winfo_exists()
d.configurar(banco, Path(config['pasta']))
controlador.fechar()
# Aguarda até a cópia terminar e a janela ser destruída.
aguardar()
assert not controlador.ocupado
'''
        resultado = subprocess.run([sys.executable, '-c', script, str(self.banco)], cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, timeout=15)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_snapshot_inclui_transacao_confirmada_em_wal(self):
        conexao = sqlite3.connect(self.banco)
        self.addCleanup(conexao.close)
        conexao.execute('PRAGMA journal_mode=WAL')
        conexao.execute("INSERT INTO vendas (data,dinheiro,pix,cartao) VALUES ('2030-01-01',1,2,3)")
        conexao.commit()
        resultado = d.executar(self.banco, self.config)
        with closing(sqlite3.connect(resultado['arquivo'])) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM vendas').fetchone()[0], 10)

    def test_erro_de_retencao_nao_invalida_copia_publicada(self):
        for _ in range(7):
            d.executar(self.banco, self.config)
        apagar = Path.unlink
        def falhar_em_versoes(caminho, *args, **kwargs):
            if d.VERSAO.fullmatch(caminho.name):
                raise PermissionError('versão bloqueada pelo sincronizador')
            return apagar(caminho, *args, **kwargs)
        with patch.object(Path, 'unlink', falhar_em_versoes):
            resultado = d.executar(self.banco, self.config)
        self.assertTrue(resultado['arquivo'].exists())
        self.assertTrue(resultado['avisos'])


    def test_drive_que_rejeita_operacoes_sqlite_aceita_transporte_binario(self):
        conectar = sqlite3.connect
        def unidade_virtual(caminho, *args, **kwargs):
            if 'Drive' in str(caminho):
                raise sqlite3.OperationalError('database or disk is full')
            return conectar(caminho, *args, **kwargs)
        with patch.object(sqlite3, 'connect', side_effect=unidade_virtual):
            resultado = d.executar(self.banco, self.config)
        self.assertEqual(d._hash_arquivo(resultado['arquivo']), d._hash_arquivo(resultado['local']))

    def test_hash_divergente_nao_substitui_copia_anterior(self):
        resultado = d.executar(self.banco, self.config)
        antes = resultado['arquivo'].read_bytes()
        with patch.object(d, '_hash_arquivo', return_value=b'incorreto'):
            with self.assertRaises(OSError) as erro:
                d.executar(self.banco, self.config)
        self.assertIn('SHA-256', str(erro.exception))
        self.assertIn('Backup local preservado', str(erro.exception))
        self.assertEqual(resultado['arquivo'].read_bytes(), antes)
        self.assertFalse(list(resultado['arquivo'].parent.glob('*.tmp')))

    def test_diagnostico_identifica_falha_local(self):
        with patch.object(d, 'criar_backup', side_effect=sqlite3.OperationalError('database or disk is full')):
            with self.assertRaises(OSError) as erro:
                d.executar(self.banco, self.config)
        self.assertIn('backup local', str(erro.exception))
        self.assertIn('database or disk is full', str(erro.exception))
        self.assertFalse((self.drive / d.SUBPASTA).exists())

    def test_selecionar_subpasta_existente_nao_cria_subpasta_duplicada(self):
        pasta = self.drive / d.SUBPASTA
        pasta.mkdir()
        config = d.configurar(self.banco, pasta)
        resultado = d.executar(self.banco, config)
        self.assertEqual(resultado['arquivo'].parent, pasta.resolve())
        self.assertFalse((pasta / d.SUBPASTA).exists())
