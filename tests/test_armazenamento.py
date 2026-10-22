from dados_ficticios import criar_banco
from contextlib import closing
import hashlib
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ProgramFeira.database import armazenamento as a

ROOT = Path(__file__).resolve().parents[1]


class ArmazenamentoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = criar_banco(self.root / 'origem.db')
        self.dest = self.root / 'dados/vendas.db'

    def count(self, path):
        c = sqlite3.connect(path)
        try:
            return c.execute('SELECT count(*) FROM vendas').fetchone()[0]
        finally:
            c.close()

    def test_migracao_preserva_origem_e_nao_substitui_dados_locais(self):
        original = hashlib.sha256(self.source.read_bytes()).digest()
        a.preparar_banco(self.dest, self.source)
        self.assertEqual(self.count(self.dest), 9)
        backups = list((self.dest.parent / 'backups').glob('*.db'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(self.count(backups[0]), 9)
        c = sqlite3.connect(self.dest)
        c.execute("INSERT INTO vendas(data) VALUES ('2030-01-01')")
        c.commit()
        c.close()
        a.preparar_banco(self.dest, self.source)
        self.assertEqual(self.count(self.dest), 10)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), original)

    def test_backup_restauracao_e_preservacao_do_estado_anterior(self):
        a.preparar_banco(self.dest, self.source)
        backup = a.criar_backup(self.dest)
        c = sqlite3.connect(self.dest)
        c.execute('DELETE FROM vendas')
        c.commit()
        c.close()
        anterior = a.restaurar_backup(self.dest, backup)
        self.assertEqual(self.count(self.dest), 9)
        self.assertEqual(self.count(anterior), 0)
        self.assertEqual(self.count(backup), 9)

    def test_arquivo_invalido_nao_altera_banco(self):
        a.preparar_banco(self.dest, self.source)
        before = self.dest.read_bytes()
        invalid = self.root / 'invalido.db'
        invalid.write_bytes(b'arquivo invalido')
        with self.assertRaises(sqlite3.DatabaseError):
            a.restaurar_backup(self.dest, invalid)
        self.assertEqual(self.dest.read_bytes(), before)

    def test_backup_existente_nunca_e_sobrescrito(self):
        dest = self.root / 'protegido.db'
        dest.write_bytes(b'preservar')
        with self.assertRaises(FileExistsError):
            a.copiar_verificado(self.source, dest)
        self.assertEqual(dest.read_bytes(), b'preservar')

    def test_cadastro_edicao_exclusao_tem_backup_e_falha_impede_gravacao(self):
        a.preparar_banco(self.dest, self.source)
        spec = importlib.util.spec_from_file_location('banco_local', ROOT / 'ProgramFeira/database/banco.py')
        b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(b)
        b.CAMINHO_BANCO = self.dest
        b.cadastrar_venda('2030-01-01', 1, 2, 3)
        row = b.buscar_venda_por_data('2030-01-01')
        b.atualizar_venda(row[0], '2030-01-01', 4, 5, 6)
        b.excluir_venda(row[0])
        for reason in ('antes-cadastro', 'antes-edicao', 'antes-exclusao'):
            self.assertEqual(len(list((self.dest.parent / 'backups').glob(f'*{reason}*.db'))), 1)
        with patch.object(b, 'backup_arquivo', side_effect=OSError('disco indisponível')):
            with self.assertRaises(OSError):
                b.cadastrar_venda('2030-01-02', 1, 2, 3)
        self.assertIsNone(b.buscar_venda_por_data('2030-01-02'))

    def test_dias_zerados_permanecem_na_contagem(self):
        a.preparar_banco(self.dest, self.source)
        c = sqlite3.connect(self.dest)
        try:
            self.assertEqual(c.execute('SELECT count(*) FROM vendas').fetchone()[0], 9)
            self.assertGreater(c.execute('SELECT count(*) FROM vendas WHERE dinheiro=0 AND pix=0 AND cartao=0').fetchone()[0], 0)
        finally:
            c.close()

    def test_local_windows_e_linux(self):
        with patch.object(a.sys, 'platform', 'win32'), patch.dict(a.os.environ, {'LOCALAPPDATA': str(self.root)}, clear=True):
            self.assertEqual(a.pasta_dados(), self.root / 'ProgramFeira')
        with patch.object(a.sys, 'platform', 'linux'), patch.dict(a.os.environ, {'XDG_DATA_HOME': str(self.root)}, clear=True):
            self.assertEqual(a.pasta_dados(), self.root / 'ProgramFeira')


class RecuperacaoTests(unittest.TestCase):
    def test_ensaio_recupera_financas_e_metadados_sem_tocar_na_origem(self):
        from ProgramFeira.recuperacao import testar_recuperacao
        with tempfile.TemporaryDirectory() as pasta:
            origem = criar_banco(Path(pasta) / 'backup.db')
            with closing(sqlite3.connect(origem)) as c, c:
                c.executescript("CREATE TABLE financeiro_lancamentos(id INTEGER, valor_centavos INTEGER); INSERT INTO financeiro_lancamentos VALUES(1,12345); CREATE TABLE financeiro_taxas_anuais(ano INTEGER, valor_centavos INTEGER); INSERT INTO financeiro_taxas_anuais VALUES(2030,456); CREATE TABLE nuvem_sync_estado(pendente TEXT); INSERT INTO nuvem_sync_estado VALUES('lote pendente ficticio');")
            antes = origem.read_bytes()
            resultado = testar_recuperacao(origem)
            self.assertTrue(resultado['sucesso'])
            self.assertEqual(resultado['tabelas']['vendas'], 9)
            self.assertEqual(resultado['tabelas']['financeiro_lancamentos'], 1)
            self.assertEqual(resultado['tabelas']['financeiro_taxas_anuais'], 1)
            self.assertEqual(resultado['tabelas']['nuvem_sync_estado'], 1)
            self.assertEqual(origem.read_bytes(), antes)

    def test_arquivo_invalido_e_banco_em_uso_sao_recusados(self):
        from ProgramFeira.recuperacao import testar_recuperacao
        with tempfile.TemporaryDirectory() as pasta:
            origem = Path(pasta) / 'invalido.db'
            origem.write_bytes(b'invalido')
            with self.assertRaises(sqlite3.DatabaseError):
                testar_recuperacao(origem)
            origem = criar_banco(Path(pasta) / 'backup.db')
            Path(str(origem) + '-wal').write_bytes(b'em uso')
            with self.assertRaises(ValueError):
                testar_recuperacao(origem)
