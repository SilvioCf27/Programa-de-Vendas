"""Persistência da sessão: proteção, vínculo ao projeto e recuperação sem senha."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ProgramFeira import sessao_windows as armazenamento
from ProgramFeira.nuvem import Sessao, ErroNuvem


class SessaoWindowsTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.url = 'https://projeto-ficticio.supabase.co'
        self.sessao = Sessao('usuario-ficticio', 'teste@example.invalid', 'acesso-ficticio', 'renovavel-ficticio', 123)

    def test_persistencia_opaca_sem_senha_nem_token_de_acesso(self):
        # Substitui somente o provedor de proteção; o teste nativo abaixo usa DPAPI.
        def proteger(dados, modo):
            return b'protegido:' + dados[::-1] if modo else dados[len(b'protegido:'):][::-1]
        with patch.object(armazenamento, 'DISPONIVEL', True), patch.object(armazenamento, '_converter', side_effect=proteger):
            armazenamento.salvar(self.pasta.name, self.url, self.sessao)
            caminho = Path(self.pasta.name) / armazenamento.NOME
            corpo = caminho.read_bytes()
            self.assertNotIn(b'renovavel-ficticio', corpo)
            self.assertNotIn(b'acesso-ficticio', corpo)
            restaurada = armazenamento.carregar(self.pasta.name, self.url)
            self.assertEqual(restaurada.refresh_token, self.sessao.refresh_token)
            self.assertEqual(restaurada.usuario_id, self.sessao.usuario_id)
            self.assertEqual(restaurada.token, '')
            self.assertEqual(restaurada.expira_em, 1)
            with self.assertRaises(ErroNuvem):
                armazenamento.carregar(self.pasta.name, 'https://outro.supabase.co')
            caminho.write_bytes(b'arquivo danificado')
            with self.assertRaises(ErroNuvem):
                armazenamento.carregar(self.pasta.name, self.url)
            armazenamento.remover(self.pasta.name)
            self.assertIsNone(armazenamento.carregar(self.pasta.name, self.url))
            self.assertEqual(list(Path(self.pasta.name).iterdir()), [])

    def test_sistema_sem_protetor_nao_salva_credencial(self):
        with patch.object(armazenamento, 'DISPONIVEL', False):
            armazenamento.salvar(self.pasta.name, self.url, self.sessao)
            self.assertIsNone(armazenamento.carregar(self.pasta.name, self.url))
        self.assertEqual(list(Path(self.pasta.name).iterdir()), [])

    def test_falha_ao_proteger_nao_substitui_sessao_anterior(self):
        caminho = Path(self.pasta.name) / armazenamento.NOME
        caminho.write_bytes(b'copia-anterior')
        with patch.object(armazenamento, 'DISPONIVEL', True), patch.object(armazenamento, '_converter', side_effect=OSError('indisponivel')):
            with self.assertRaises(OSError):
                armazenamento.salvar(self.pasta.name, self.url, self.sessao)
        self.assertEqual(caminho.read_bytes(), b'copia-anterior')

    @unittest.skipUnless(armazenamento.DISPONIVEL, 'DPAPI nativa requer Windows')
    def test_dpapi_nativa_recupera_e_recusa_corrupcao(self):
        armazenamento.salvar(self.pasta.name, self.url, self.sessao)
        corpo = (Path(self.pasta.name) / armazenamento.NOME).read_bytes()
        self.assertNotIn(self.sessao.refresh_token.encode(), corpo)
        self.assertEqual(armazenamento.carregar(self.pasta.name, self.url).refresh_token, self.sessao.refresh_token)
        (Path(self.pasta.name) / armazenamento.NOME).write_bytes(corpo[:-12])
        with self.assertRaises(ErroNuvem):
            armazenamento.carregar(self.pasta.name, self.url)
