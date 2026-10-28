"""Preservação offline: dados e credenciais somente em pastas fictícias."""
from contextlib import closing
from pathlib import Path
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from ProgramFeira import financeiro,nuvem
from ProgramFeira import sessao_windows,sincronizacao
from ProgramFeira.database import banco
from ProgramFeira.recuperacao import _conteudo
from reforma_desktop.ambiente import MARCADOR,CONTEUDO
from reforma_desktop import perfil_validacao as perfil

URL='https://validacao-separada.supabase.co'
ANTIGA='https://origem-ficticia.supabase.co'
CHAVE='sb_publishable_somente_testes'


class PerfilTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.raiz=Path(temp.name);self.origem=self.raiz/'origem';self.origem.mkdir()
        self.destino=self.raiz/'destino'
        p=patch.dict(os.environ,{'PROGRAMFEIRA_DATA_DIR':str(self.raiz/'pessoal')});p.start();self.addCleanup(p.stop)
        p=patch.object(banco,'CAMINHO_BANCO',self.origem/'vendas.db');p.start();self.addCleanup(p.stop)
        banco.criar_tabela();financeiro.inicializar()
        (self.origem/MARCADOR).write_text(CONTEUDO,encoding='utf-8')
        banco.cadastrar_venda('2026-10-23',10,20,30)
        financeiro.salvar_lancamento('despesa','2026-10-09','Compra fictícia','100','Cartão de crédito','Outros',3,data_compra='2026-10-09')
        self.config('preferencias.json',{'tema':'aurora'})
        self.config('inicio.json',{'periodo':'Todas as vendas'})
        self.config('nuvem.json',{'url':ANTIGA,'chave_publica':CHAVE})
        self.config('sincronizacao.json',{'automatica':True})
        self.config('atualizacoes.json',{'consultar':True})
        self.config('backup_drive.json',{'pasta':'G:/Meu Drive/exemplo-ficticio'})

    def config(self,nome,dados):
        (self.origem/nome).write_text(json.dumps(dados,ensure_ascii=False),encoding='utf-8')

    def preparar(self):return perfil.preparar(self.origem,self.destino,URL,CHAVE)

    def test_preserva_bytes_dados_e_configuracoes_sem_ativar_servicos(self):
        (self.origem/sessao_windows.NOME).write_bytes(b'credencial-opaca-ficticia')
        antes=_conteudo(self.origem/'vendas.db')
        configs=perfil.ler_configuracoes(self.origem)
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Rede proibida')):
            p=self.preparar();m=perfil.conferir(p);c=perfil.cliente_preparado(p)
        self.assertEqual(c.url,URL);self.assertIsNone(c._ultima_sessao)
        self.assertEqual(_conteudo(p/'preservados/vendas.db'),antes)
        self.assertEqual(_conteudo(self.origem/'vendas.db'),antes)
        self.assertEqual(perfil.ler_configuracoes(self.origem),configs)
        for nome,dados in configs.items():self.assertEqual((p/'preservados'/nome).read_bytes(),dados)
        ativo=p/'aplicacao'
        self.assertFalse((ativo/'vendas.db').exists());self.assertFalse((ativo/sessao_windows.NOME).exists())
        self.assertEqual(json.loads((ativo/'sincronizacao.json').read_text()),{'automatica':False})
        self.assertEqual(json.loads((ativo/'atualizacoes.json').read_text()),{'consultar':False})
        self.assertEqual(json.loads((ativo/'backup_drive.json').read_text()),{})
        self.assertEqual((ativo/'preferencias.json').read_bytes(),configs['preferencias.json'])
        self.assertEqual(m['tabelas']['vendas'],1)

    def test_destino_existente_nao_e_sobrescrito(self):
        self.destino.mkdir();f=self.destino/'guardar.txt';f.write_text('preservar')
        with self.assertRaisesRegex(ValueError,'já existe'):self.preparar()
        self.assertEqual(f.read_text(),'preservar')

    def test_pasta_pessoal_ou_pastas_sobrepostas_sao_recusadas(self):
        for destino in [self.raiz/'pessoal',self.origem,self.origem/'sub',self.raiz]:
            with self.subTest(destino=destino),self.assertRaises(ValueError):
                perfil.preparar(self.origem,destino,URL,CHAVE)

    def test_origem_sem_marcador_e_projeto_igual_sao_recusados(self):
        with self.assertRaisesRegex(ValueError,'diferente'):perfil.preparar(self.origem,self.destino,ANTIGA,CHAVE)
        (self.origem/MARCADOR).unlink()
        with self.assertRaisesRegex(ValueError,'marcada'):self.preparar()
        self.assertFalse(self.destino.exists())

    def test_configuracao_invalida_interrompe_sem_publicar(self):
        (self.origem/'preferencias.json').write_text('{SEGREDO')
        with self.assertRaisesRegex(ValueError,'Configuração inválida') as erro:self.preparar()
        self.assertNotIn('SEGREDO',str(erro.exception));self.assertFalse(self.destino.exists())

    def test_tamper_e_arquivo_extra_impedem_criar_cliente(self):
        p=self.preparar();ativo=p/'aplicacao'
        (ativo/'preferencias.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'verificação'):perfil.cliente_preparado(p)
        (ativo/'preferencias.json').write_bytes((p/'preservados/preferencias.json').read_bytes())
        (ativo/sessao_windows.NOME).write_bytes(b'nao-ativar')
        with self.assertRaisesRegex(ValueError,'alterado'):perfil.cliente_preparado(p)

    def test_mudanca_durante_copia_interrompe_sem_apagar_a_origem(self):
        original=perfil.copiar_verificado
        def copiar(*args):
            r=original(*args);self.config('preferencias.json',{'tema':'areia'});return r
        with patch.object(perfil,'copiar_verificado',copiar),self.assertRaisesRegex(ValueError,'mudou'):self.preparar()
        self.assertFalse(self.destino.exists())
        self.assertEqual(json.loads((self.origem/'preferencias.json').read_text())['tema'],'areia')
        self.assertEqual(len(banco.listar_vendas()),1)

    def test_vinculo_do_banco_tambem_impede_mesmo_projeto(self):
        (self.origem/'nuvem.json').unlink()
        with closing(sqlite3.connect(self.origem/'vendas.db')) as c,c:
            sincronizacao._estrutura(c)
            c.execute('INSERT INTO nuvem_sync_estado VALUES(1,?,?,NULL)',(URL,'11111111-1111-4111-8111-111111111111'))
        with self.assertRaisesRegex(ValueError,'vínculo'):self.preparar()
        self.assertFalse(self.destino.exists())

    def test_snapshot_inclui_wal_confirmado(self):
        with closing(sqlite3.connect(self.origem/'vendas.db')) as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute("INSERT INTO vendas(data,dinheiro,pix,cartao) VALUES('2026-10-25',1,2,3)");c.commit()
            p=self.preparar()
            self.assertEqual(perfil.conferir(p)['tabelas']['vendas'],2)

    def test_links_em_configuracao_sao_recusados(self):
        arquivo=self.origem/'preferencias.json';fora=self.raiz/'fora.json';fora.write_bytes(arquivo.read_bytes());arquivo.unlink()
        try:arquivo.symlink_to(fora)
        except OSError:self.skipTest('Criação de link não disponível neste Windows')
        with self.assertRaisesRegex(ValueError,'redirecionada'):self.preparar()
        self.assertFalse(self.destino.exists())

    def test_perfil_incompleto_e_chave_secreta_sao_recusados(self):
        with self.assertRaises(ValueError):perfil.preparar(self.origem,self.destino,URL,'service_role_ficticia')
        p=self.preparar();(p/perfil.MARCA_PERFIL).unlink()
        with self.assertRaisesRegex(ValueError,'incompleto'):perfil.cliente_preparado(p)

    @unittest.skipUnless(sessao_windows.DISPONIVEL,'DPAPI nativa requer Windows')
    def test_sessao_dpapi_original_permanece_recuperavel_so_no_arquivo_preservado(self):
        s=nuvem.Sessao('11111111-1111-4111-8111-111111111111','teste@example.invalid','token-ficticio','refresh-ficticio',1)
        sessao_windows.salvar(self.origem,ANTIGA,s)
        p=self.preparar()
        self.assertEqual(sessao_windows.carregar(p/'preservados',ANTIGA).refresh_token,'refresh-ficticio')
        self.assertIsNone(sessao_windows.carregar(p/'aplicacao',URL))
        self.assertEqual(sessao_windows.carregar(self.origem,ANTIGA).refresh_token,'refresh-ficticio')
