"""Autenticação isolada: não usa conta real, rede ou banco de vendas."""
import base64
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from ProgramFeira import nuvem

URL = 'https://projeto-ficticio.supabase.co'
CHAVE = 'sb_publishable_apenas_teste'


def resposta(dados):
    return io.BytesIO(json.dumps(dados).encode('utf-8'))


class NuvemTests(unittest.TestCase):
    def test_config_rejeita_segredos_urls_externas_e_valores_invalidos(self):
        payload = lambda role: base64.urlsafe_b64encode(json.dumps({'role': role}).encode()).decode().rstrip('=')
        anon = 'cabecalho.' + payload('anon') + '.assinatura'
        self.assertEqual(nuvem.validar_config(URL + '/', anon)['url'], URL)
        for chave in ('sb_secret_segredo', 'cabecalho.' + payload('service_role') + '.assinatura', '', 'senha', None):
            with self.subTest(chave=chave), self.assertRaises(nuvem.ErroNuvem):
                nuvem.validar_config(URL, chave)
        for endereco in ('http://projeto.supabase.co', 'https://supabase.com/dashboard/project/abc', 'https://projeto.supabase.co.evil.invalid', 'https://usuario@projeto.supabase.co', URL + '/rest/v1', None):
            with self.subTest(url=endereco), self.assertRaises(nuvem.ErroNuvem):
                nuvem.validar_config(endereco, CHAVE)

    def test_config_salva_apenas_informacoes_publicas_sem_tocar_no_banco(self):
        with tempfile.TemporaryDirectory() as pasta:
            banco = Path(pasta) / 'vendas.db'
            banco.write_bytes(b'banco-ficticio-nao-alterar')
            self.assertEqual(nuvem.carregar_config(pasta), {})
            config = nuvem.salvar_config(pasta, URL, CHAVE)
            self.assertEqual(nuvem.carregar_config(pasta), config)
            self.assertEqual(set(json.loads((Path(pasta) / 'nuvem.json').read_text())), {'url', 'chave_publica'})
            self.assertEqual(banco.read_bytes(), b'banco-ficticio-nao-alterar')
            self.assertEqual(len(list(Path(pasta).iterdir())), 2)
            with self.assertRaises(nuvem.ErroNuvem):
                nuvem.salvar_config(pasta, URL, 'sb_secret_nao_salvar')
            self.assertEqual(nuvem.carregar_config(pasta), config)

    def test_config_corrompida_tem_erro_claro(self):
        with tempfile.TemporaryDirectory() as pasta:
            for conteudo in ('invalido', '[]', '{}', '{"url": null, "chave_publica": 123}'):
                (Path(pasta) / 'nuvem.json').write_text(conteudo)
                with self.assertRaises(nuvem.ErroNuvem):
                    nuvem.carregar_config(pasta)

    def test_login_exige_autorizacao_e_nao_envia_senha_ao_rpc(self):
        cliente = nuvem.ClienteNuvem(URL, CHAVE)
        cliente._abrir = Mock(side_effect=[resposta({'access_token': 'token-ficticio', 'user': {'id': 'usuario-ficticio', 'email': 'teste@example.invalid'}}), resposta(True)])
        sessao = cliente.entrar(' teste@example.invalid ', 'senha-ficticia')
        self.assertEqual(sessao.usuario_id, 'usuario-ficticio')
        self.assertNotIn(sessao.token, repr(sessao))
        login, rpc = cliente._abrir.call_args_list
        self.assertEqual(login.args[0].full_url, URL + '/auth/v1/token?grant_type=password')
        self.assertEqual(json.loads(login.args[0].data), {'email': 'teste@example.invalid', 'password': 'senha-ficticia'})
        self.assertEqual(rpc.args[0].full_url, URL + '/rest/v1/rpc/usuario_autorizado')
        self.assertEqual(rpc.args[0].data, b'{}')
        self.assertEqual(rpc.args[0].get_header('Authorization'), 'Bearer token-ficticio')
        self.assertEqual(login.kwargs['timeout'], 20)

    def test_conta_nao_autorizada_nao_produz_sessao(self):
        for autorizado in (False, None, 'true', 1):
            cliente = nuvem.ClienteNuvem(URL, CHAVE)
            cliente._abrir = Mock(side_effect=[resposta({'access_token': 'token', 'user': {'id': 'usuario'}}), resposta(autorizado)])
            with self.subTest(autorizado=autorizado), self.assertRaisesRegex(nuvem.ErroNuvem, 'não está autorizada'):
                cliente.entrar('teste@example.invalid', 'senha')

    def test_erros_de_rede_e_servico_nao_expoem_segredos(self):
        for erro in (URLError('token-sigiloso'), TimeoutError('senha-sigilosa'), HTTPError(URL, 401, 'segredo', {}, None), HTTPError(URL, 429, 'segredo', {}, None), HTTPError(URL, 500, 'segredo', {}, None)):
            cliente = nuvem.ClienteNuvem(URL, CHAVE)
            cliente._abrir = Mock(side_effect=erro)
            with self.subTest(erro=type(erro).__name__), self.assertRaises(nuvem.ErroNuvem) as contexto:
                cliente.entrar('teste@example.invalid', 'senha-sigilosa')
            self.assertNotIn('segredo', str(contexto.exception))
            self.assertNotIn('sigiloso', str(contexto.exception))
            self.assertNotIn('sigilosa', str(contexto.exception))

    def test_resposta_invalida_e_campos_vazios_nao_criam_sessao(self):
        for dados in ({}, None, {'access_token': '', 'user': {'id': 'usuario'}}):
            cliente = nuvem.ClienteNuvem(URL, CHAVE)
            cliente._abrir = Mock(return_value=resposta(dados))
            with self.assertRaises(nuvem.ErroNuvem):
                cliente.entrar('teste@example.invalid', 'senha')
        cliente._abrir.reset_mock()
        for email, senha in (('', 'senha'), ('teste@example.invalid', '')):
            with self.assertRaises(nuvem.ErroNuvem):
                cliente.entrar(email, senha)
        cliente._abrir.assert_not_called()

    def test_redirecionamento_nao_reenvia_credenciais(self):
        handler = nuvem._SemRedirecionamento()
        self.assertIsNone(handler.redirect_request(None, None, 307, '', {}, 'https://outro.invalid'))

    def test_falha_na_gravacao_preserva_config_anterior(self):
        with tempfile.TemporaryDirectory() as pasta:
            original = nuvem.salvar_config(pasta, URL, CHAVE)
            with patch.object(nuvem.os, 'replace', side_effect=OSError('disco')):
                with self.assertRaises(OSError):
                    nuvem.salvar_config(pasta, 'https://outro.supabase.co', CHAVE)
            self.assertEqual(nuvem.carregar_config(pasta), original)
            self.assertEqual(len(list(Path(pasta).iterdir())), 1)

    def test_migracao_envia_dados_so_ao_rpc_autenticado(self):
        cliente = nuvem.ClienteNuvem(URL, CHAVE)
        cliente._abrir = Mock(return_value=resposta({'aplicado': False}))
        sessao = nuvem.Sessao('usuario', 'teste@example.invalid', 'token-ficticio')
        cliente.migrar(sessao, {'vendas': []}, False)
        req = cliente._abrir.call_args.args[0]
        self.assertEqual(req.full_url, URL + '/rest/v1/rpc/migrar_desktop')
        self.assertEqual(json.loads(req.data), {'dados': {'vendas': []}, 'aplicar': False})
        self.assertEqual(req.get_header('Authorization'), 'Bearer token-ficticio')

    def test_erros_de_migracao_explicam_conflito_sem_exibir_resposta_bruta(self):
        for codigo, trecho in [('PFM01', 'divergentes'), ('PFM02', 'formato'), ('PGRST202', '003_migracao'), ('23505', 'cancelada')]:
            cliente = nuvem.ClienteNuvem(URL, CHAVE)
            corpo = {'code': codigo, 'message': 'senha-nao-exibir', 'details': json.dumps({'tabela': 'vendas', 'chave': '2030-01-01'})}
            cliente._abrir = Mock(side_effect=HTTPError(URL, 400, 'erro', {}, resposta(corpo)))
            with self.assertRaisesRegex(nuvem.ErroNuvem, trecho) as contexto:
                cliente.migrar(nuvem.Sessao('usuario', 'email', 'token'), {}, False)
            self.assertNotIn('senha-nao-exibir', str(contexto.exception))
            if codigo == 'PFM01':
                self.assertIn('2030-01-01', str(contexto.exception))
