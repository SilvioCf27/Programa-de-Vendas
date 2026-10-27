"""Recuperação e transporte Qt em diretórios fictícios, sem conta Drive."""
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'reforma_desktop/tests'))
import test_configuracoes_qt as fixtures
from ProgramFeira.database import banco
from ProgramFeira import backup_drive
from PySide6 import QtWidgets as W
from reforma_desktop.operacoes_backup import configurar_drive, copiar_drive, PASTA_ESTUDO


# Reutiliza somente a fixture, sem repetir seus oito testes.
class RecuperacaoTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.ConfiguracoesTests.setUpClass.__func__)
    setUp = fixtures.ConfiguracoesTests.setUp
    janela = fixtures.ConfiguracoesTests.janela
    def esperar(self, c):
        limite = time.monotonic() + 15
        while c.operacao is not None and time.monotonic() < limite:
            self.app.processEvents()
            time.sleep(.005)
        self.assertIsNone(c.operacao)

    def test_verificar_nao_substitui_e_restaurar_preserva_anterior(self):
        self.servico.salvar('2026-10-23', '10', '20', '30')
        copia = banco.criar_backup()
        self.servico.salvar('2026-10-25', '5', '0', '0')
        j = self.janela()
        c = j.configuracoes()
        antes = banco.CAMINHO_BANCO.read_bytes()
        with patch.object(c, 'arquivo_backup', return_value=str(copia)):
            c.verificar()
            self.esperar(c)
            self.assertIn('Banco em uso preservado', c.status.text())
            self.assertEqual(banco.CAMINHO_BANCO.read_bytes(), antes)
            with patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.Yes):
                c.restaurar()
        self.esperar(c)
        self.assertEqual(len(banco.listar_vendas()), 1)
        self.assertTrue(c.reiniciar)
        self.assertTrue(c.isEnabled())
        self.assertFalse(j.relogio.isActive())
        self.assertTrue(list((self.pasta/'backups').glob('*antes-restauracao*.db')))
        c.reject()
        self.assertFalse(j.isVisible())

    def test_cancelar_restauracao_nao_modifica_nem_cria_copia(self):
        c = self.janela().configuracoes()
        with patch.object(c, 'arquivo_backup', return_value='nao-usar.db'), patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.No), patch.object(banco, 'restaurar_backup') as restaurar:
            c.restaurar()
            restaurar.assert_not_called()
        self.assertIsNone(c.operacao)
        c.close()

    def test_backup_invalido_preserva_dados_e_retoma_timer(self):
        j = self.janela()
        c = j.configuracoes()
        ruim = self.pasta/'ruim.db'
        ruim.write_text('Não é SQLite', encoding='utf-8')
        antes = banco.CAMINHO_BANCO.read_bytes()
        with patch.object(c, 'arquivo_backup', return_value=str(ruim)), patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.Yes):
            c.restaurar()
        self.esperar(c)
        self.assertIn('não concluída', c.status.text())
        self.assertEqual(banco.CAMINHO_BANCO.read_bytes(), antes)
        self.assertTrue(j.relogio.isActive())
        self.assertFalse(c.reiniciar)
        c.close()

    def test_drive_separa_estudo_do_conjunto_de_producao(self):
        raiz = self.pasta/'drive-ficticio'
        raiz.mkdir()
        producao = raiz/backup_drive.SUBPASTA
        producao.mkdir()
        sentinela = producao/backup_drive.ULTIMO
        sentinela.write_bytes(b'Nao alterar')
        configurar_drive(banco.CAMINHO_BANCO, raiz)
        r = copiar_drive(banco.CAMINHO_BANCO)
        self.assertEqual(sentinela.read_bytes(), b'Nao alterar')
        self.assertIn(PASTA_ESTUDO, str(r['arquivo']))
        self.assertEqual(Path(r['arquivo']).read_bytes(), Path(r['local']).read_bytes())
        c = self.janela().configuracoes()
        c.drive()
        self.esperar(c)
        self.assertIn('Confira o envio', c.status.text())
        c.desativar_drive()
        self.assertEqual(backup_drive.carregar_config(self.pasta), {})
        self.assertTrue(Path(r['arquivo']).exists())
        c.close()

    def test_operacao_lenta_nao_bloqueia_eventos_ou_permite_fechar(self):
        import threading
        from PySide6 import QtCore as Q
        liberar = threading.Event()
        c = self.janela().configuracoes()
        recebido = []
        c.executar(lambda: liberar.wait(5), recebido.append)
        self.addCleanup(liberar.set)
        Q.QTimer.singleShot(0, lambda: recebido.append('interface ativa'))
        self.app.processEvents()
        c.reject()
        self.assertTrue(c.isVisible())
        self.assertIn('interface ativa', recebido)
        liberar.set()
        self.esperar(c)
        self.assertIn(True, recebido)
        c.close()

    def esperar_fechamento(self, j):
        limite = time.monotonic() + 15
        while getattr(j, '_backup_fechamento', None) is not None and time.monotonic() < limite:
            self.app.processEvents()
            time.sleep(.005)
        self.assertIsNone(getattr(j, '_backup_fechamento', None))
        self.app.processEvents()

    def test_fechar_com_drive_copia_antes_de_encerrar(self):
        j = self.janela()
        raiz = self.pasta/'drive-ficticio'
        raiz.mkdir()
        configurar_drive(banco.CAMINHO_BANCO, raiz)
        j.close()
        self.assertTrue(j.isVisible())
        self.esperar_fechamento(j)
        self.assertFalse(j.isVisible())
        dados = backup_drive.carregar_config(self.pasta)
        self.assertTrue(Path(dados['ultimo_arquivo']).is_file())

    def test_falha_no_backup_ao_fechar_permite_continuar(self):
        j = self.janela()
        raiz = self.pasta/'drive-ficticio'
        raiz.mkdir()
        configurar_drive(banco.CAMINHO_BANCO, raiz)
        with patch('reforma_desktop.operacoes_backup.copiar_drive', side_effect=OSError('Sem acesso')), patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.No):
            j.close()
            self.esperar_fechamento(j)
        self.assertTrue(j.isVisible())
        self.assertTrue(j.relogio.isActive())
        backup_drive.desativar(banco.CAMINHO_BANCO)

    def test_captura_com_drive_configurado_nao_inicia_thread_ao_sair(self):
        import subprocess
        from reforma_desktop.ambiente import MARCADOR, CONTEUDO
        (self.pasta/MARCADOR).write_text(CONTEUDO, encoding='utf-8')
        raiz = self.pasta/'drive-ficticio'
        raiz.mkdir()
        dados = configurar_drive(banco.CAMINHO_BANCO, raiz)
        captura = self.pasta/'captura.png'
        r = subprocess.run([sys.executable, str(ROOT/'executar_reforma.py'), '--pasta-estudo', str(self.pasta), '--captura', str(captura)], cwd=ROOT, capture_output=True, text=True, timeout=45)
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertTrue(captura.is_file())
        self.assertFalse((Path(dados['pasta'])/backup_drive.SUBPASTA).exists())

    def test_drive_recusa_configuracao_do_programa_estavel(self):
        backup_drive.salvar_config(self.pasta, {'pasta':str(self.pasta)})
        with self.assertRaisesRegex(ValueError, 'própria'):
            copiar_drive(banco.CAMINHO_BANCO)

