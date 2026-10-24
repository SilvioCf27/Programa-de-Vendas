"""Bancos adulterados e caminhos redirecionados, somente em diretórios fictícios."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from dados_ficticios import criar_banco
from ProgramFeira import backup_drive as drive
from ProgramFeira.database import armazenamento as armazenamento
from ProgramFeira.database import entrada_backup as entrada
from ProgramFeira.recuperacao import testar_recuperacao


class SegurancaBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='feira-seguranca-')
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.banco = criar_banco(self.raiz / 'vendas.db')
        self.origem = criar_banco(self.raiz / 'origem.db')
        self.drive = self.raiz / 'Drive'
        self.drive.mkdir()
        self.fora = self.raiz / 'fora-do-Drive'
        self.fora.mkdir()

    def redirecionar(self, link, alvo):
        if os.name == 'nt':
            r = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(alvo)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        else:
            link.symlink_to(alvo, target_is_directory=True)

    def test_trigger_adulterado_nao_e_restaurado_nem_executado_no_ensaio(self):
        with closing(sqlite3.connect(self.origem)) as c, c:
            c.execute('CREATE TRIGGER adulterado AFTER INSERT ON vendas BEGIN DELETE FROM vendas WHERE id != NEW.id; END')
        antes = self.banco.read_bytes()
        for acao in (lambda: armazenamento.restaurar_backup(self.banco, self.origem), lambda: testar_recuperacao(self.origem)):
            with self.assertRaisesRegex(ValueError, 'gatilhos'):
                acao()
        self.assertEqual(self.banco.read_bytes(), antes)
        self.assertFalse((self.raiz / 'backups').exists())

    def test_banco_local_com_trigger_nao_e_publicado_no_drive(self):
        config = drive.configurar(self.banco, self.drive)
        anterior = drive.executar(self.banco, config)['arquivo'].read_bytes()
        with closing(sqlite3.connect(self.banco)) as c, c:
            c.execute('CREATE TRIGGER adulterado AFTER INSERT ON vendas BEGIN DELETE FROM vendas; END')
        with self.assertRaisesRegex(OSError, 'gatilhos'):
            drive.executar(self.banco, config)
        self.assertEqual((self.drive / drive.SUBPASTA / drive.ULTIMO).read_bytes(), anterior)

    def test_view_disfarcada_de_vendas_e_recusada(self):
        falso = self.raiz / 'view.db'
        with closing(sqlite3.connect(falso)) as c, c:
            c.execute("CREATE VIEW vendas AS SELECT 1 id,'2030-01-01' data,1 dinheiro,2 pix,3 cartao")
        antes = self.banco.read_bytes()
        with self.assertRaisesRegex(ValueError, 'consultas salvas'):
            armazenamento.restaurar_backup(self.banco, falso)
        self.assertEqual(self.banco.read_bytes(), antes)

    def test_tabela_virtual_e_recusada(self):
        with closing(sqlite3.connect(self.origem)) as c, c:
            try:
                c.execute('CREATE VIRTUAL TABLE extra USING fts5(texto)')
            except sqlite3.OperationalError:
                self.skipTest('SQLite deste ambiente não oferece FTS5 para montar o caso de teste')
        with self.assertRaisesRegex(ValueError, 'tabelas virtuais'):
            armazenamento.restaurar_backup(self.banco, self.origem)

    def test_drive_nao_publica_nem_apaga_por_link_ou_junction(self):
        destino = self.drive / drive.SUBPASTA
        self.redirecionar(destino, self.fora)
        with self.assertRaisesRegex(ValueError, 'redirecionada'):
            drive.executar(self.banco, {'pasta': str(self.drive)})
        self.assertEqual(list(self.fora.iterdir()), [])

    def test_raiz_redirecionada_nao_pode_ser_configurada(self):
        link = self.raiz / 'atalho'
        self.redirecionar(link, self.drive)
        with self.assertRaisesRegex(ValueError, 'redirecionada'):
            drive.configurar(self.banco, link)
        self.assertFalse((self.raiz / 'backup_drive.json').exists())

    def test_troca_da_pasta_durante_transporte_e_detectada_antes_de_publicar(self):
        config = drive.configurar(self.banco, self.drive)
        copiar = drive.copiar_arquivo_verificado
        def trocar(origem, destino):
            copiar(origem, destino)
            (self.drive / drive.SUBPASTA).rename(self.drive / 'pasta-anterior')
            self.redirecionar(self.drive / drive.SUBPASTA, self.fora)
        with patch.object(drive, 'copiar_arquivo_verificado', side_effect=trocar):
            with self.assertRaisesRegex(OSError, 'redirecionada'):
                drive.executar(self.banco, config)
        self.assertEqual(list(self.fora.iterdir()), [])

    def test_restauracao_e_ensaio_nao_abrem_sqlite_na_unidade_virtual(self):
        remoto = self.drive / 'backup.db'
        remoto.write_bytes(self.origem.read_bytes())
        conectar = sqlite3.connect
        def bloquear_unidade(caminho, *args, **kwargs):
            if 'Drive' in str(caminho):
                raise sqlite3.OperationalError('Unidade virtual bloqueia SQLite')
            return conectar(caminho, *args, **kwargs)
        with patch.object(sqlite3, 'connect', side_effect=bloquear_unidade):
            armazenamento.restaurar_backup(self.banco, remoto)
            self.assertTrue(testar_recuperacao(remoto)['sucesso'])

    def test_limite_de_arquivo_e_origem_aberta_preservam_banco(self):
        antes = self.banco.read_bytes()
        with patch.object(entrada, 'MAX_BACKUP_BYTES', 100):
            with self.assertRaisesRegex(ValueError, '256 MiB'):
                armazenamento.restaurar_backup(self.banco, self.origem)
        Path(str(self.origem) + '-journal').write_bytes(b'em uso')
        with self.assertRaisesRegex(ValueError, 'concluído'):
            armazenamento.restaurar_backup(self.banco, self.origem)
        self.assertEqual(self.banco.read_bytes(), antes)

    def test_arquivo_executavel_renomeado_nao_e_tratado_como_backup(self):
        falso = self.raiz / 'programa.db'
        falso.write_bytes(b'MZ' + b'arquivo ficticio' * 20)
        antes = self.banco.read_bytes()
        with self.assertRaises(sqlite3.DatabaseError):
            armazenamento.restaurar_backup(self.banco, falso)
        self.assertEqual(self.banco.read_bytes(), antes)

    def test_leitura_bloqueia_anexacao_de_arquivos_e_extensoes(self):
        with entrada.leitura_sqlite(self.origem) as c:
            self.assertEqual(c.execute('pragma trusted_schema').fetchone()[0], 0)
            with self.assertRaises(sqlite3.DatabaseError):
                c.execute('ATTACH DATABASE ? AS extra', (str(self.fora / 'extra.db'),))
            with self.assertRaises(sqlite3.DatabaseError):
                c.execute("SELECT load_extension('extensao-ficticia')")
        self.assertFalse((self.fora / 'extra.db').exists())

    def test_analise_custosa_pode_ser_interrompida(self):
        with closing(sqlite3.connect(self.origem)) as c, c:
            c.execute('create table extra(valor integer)')
            c.executemany('insert into extra values(?)', ((i,) for i in range(30000)))
        antes = self.banco.read_bytes()
        with patch.object(entrada, 'TEMPO_ANALISE', -1):
            with self.assertRaisesRegex(sqlite3.OperationalError, 'interrupted'):
                armazenamento.restaurar_backup(self.banco, self.origem)
        self.assertEqual(self.banco.read_bytes(), antes)

    def test_runtime_antigo_nao_abre_arquivo_externo(self):
        antes = self.banco.read_bytes()
        with patch.object(sqlite3, 'sqlite_version_info', (3, 45, 1)), patch.object(sqlite3, 'connect') as conectar:
            with self.assertRaisesRegex(RuntimeError, 'SQLite 3.50.2'):
                armazenamento.restaurar_backup(self.banco, self.origem)
            conectar.assert_not_called()
        self.assertEqual(self.banco.read_bytes(), antes)
