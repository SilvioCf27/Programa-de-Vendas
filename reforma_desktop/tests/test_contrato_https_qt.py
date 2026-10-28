"""Qt + ClienteNuvem não sobrescrito + HTTPS local; sem conta ou SQL remoto."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
import sys
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'reforma_desktop/tests'))
import test_configuracoes_qt as fixtures
from servidor_https import ServidorContrato,URL,CHAVE,HOST
from ProgramFeira import nuvem,financeiro,fechamento,sincronizacao,sessao_windows
from ProgramFeira.database import banco
from reforma_desktop.aplicacao import Janela
from reforma_desktop.servico_nuvem_estudo import ClienteEstudo
from PySide6 import QtCore as Q, QtWidgets as W

RPC='/rest/v1/rpc/'


class ContratoHttpsTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.ConfiguracoesTests.setUpClass.__func__)

    def setUp(self):
        fixtures.ConfiguracoesTests.setUp(self)
        self.servidor=ServidorContrato(self.pasta)
        rota=self.servidor.rotear();rota.start();self.addCleanup(rota.stop)
        self.addCleanup(self.servidor.fechar)
        self.cliente=self.servidor.cliente()
        self.assertIs(type(self.cliente),nuvem.ClienteNuvem)
        self.assertIs(type(self.cliente)._post,nuvem.ClienteNuvem._post)

    def esperar(self,n):
        fim=time.monotonic()+10
        while n.ocupado and time.monotonic()<fim:
            self.app.processEvents();time.sleep(.005)
        self.assertFalse(n.ocupado,n.status)
        self.app.processEvents()

    def janela(self):
        j=Janela(self.servico,self.pasta,cliente_nuvem=self.cliente)
        self.addCleanup(j.deleteLater);self.addCleanup(j.close)
        self.addCleanup(j.nuvem.agendador.parar);self.addCleanup(self.esperar,j.nuvem)
        j.show();self.app.processEvents()
        return j

    def vincular(self,j):
        n=j.nuvem;n.conectar();self.esperar(n);self.assertIsNotNone(n.sessao,n.status)
        n.conferir();self.esperar(n);self.assertIsNotNone(n.preparacao,n.status)
        n.transferir();self.esperar(n);n.sincronizar();self.esperar(n)
        self.assertTrue(n.vinculado,n.status);n.agendador.parar()
        return n

    def test_transferencia_e_sincronizacao_tls_nas_duas_direcoes(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j=self.janela();n=self.vincular(j)
        self.servico.salvar('2026-10-25','5','6','7')
        n.sincronizar();self.esperar(n)
        self.servidor.modelo.simular_venda_externa()
        j.mes.setCurrentIndex(9)  # seletor pendente preservado ao receber
        n.sincronizar();self.esperar(n)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-25')[3],7)
        self.assertEqual(j.mes.currentIndex(),9)
        self.assertIn('recebidas: 1',n.status)
        self.assertTrue(list((self.pasta/'backups').glob('*.db')))
        self.assertTrue(self.servidor.requisicoes)
        self.assertTrue(all(r['tls'] in ('TLSv1.2','TLSv1.3') and r['apikey']==CHAVE for r in self.servidor.requisicoes))
        self.assertTrue(all(r['authorization']=='Bearer acesso-ficticio' for r in self.servidor.requisicoes if r['caminho'].startswith(RPC)))
        self.assertEqual(set(self.servidor.conexoes),{(HOST,443)})

    def test_login_nao_autorizado_nao_cria_sessao_nem_transfere(self):
        j=self.janela();self.servidor.autorizado=False
        j.nuvem.conectar();self.esperar(j.nuvem)
        self.assertIsNone(j.nuvem.sessao)
        self.assertIn('não está autorizada',j.nuvem.status)
        self.assertFalse(j.nuvem.vinculado)
        self.assertEqual([r['caminho'] for r in self.servidor.requisicoes],['/auth/v1/token?grant_type=password',RPC+'usuario_autorizado'])

    def test_renovacao_e_persistencia_usam_o_projeto_do_cliente(self):
        j=self.janela();n=self.vincular(j)
        n.sessao=replace(n.sessao,expira_em=1)
        n.cliente._ultima_sessao=None
        with patch.object(sessao_windows,'salvar',wraps=sessao_windows.salvar) as salvar:
            n.sincronizar();self.esperar(n)
            self.assertTrue(salvar.called)
            self.assertTrue(all(c.args[1]==URL for c in salvar.call_args_list))
        self.assertIn('/auth/v1/token?grant_type=refresh_token',[r['caminho'] for r in self.servidor.requisicoes])
        self.assertGreater(n.sessao.expira_em,time.time())
        with patch.object(sessao_windows,'carregar',return_value=None) as carregar:n.restaurar_sessao()
        carregar.assert_called_once_with(self.pasta,URL)

    def test_resposta_perdida_reenvia_o_mesmo_recibo_sem_duplicar(self):
        self.servico.salvar('2026-10-23','10','20','30')
        n=self.vincular(self.janela())
        self.servico.salvar('2026-10-25','1','2','3')
        self.servidor.modelo.perder_resposta=True
        n.sincronizar();self.esperar(n)
        self.assertIn('temporariamente',n.status)
        def lotes():return [r['corpo'] for r in self.servidor.requisicoes if r['caminho']==RPC+'sincronizar_desktop_v2' and r['corpo']['operacao_id']]
        pendente=lotes()[-1]
        n.sincronizar();self.esperar(n)
        self.assertEqual(lotes()[-1],pendente)
        self.assertEqual(len(self.servidor.modelo.ler()['dados']['vendas']),2)
        self.assertIn('concluída',n.status)

    def test_503_json_invalido_e_redirecionamento_preservam_dados(self):
        self.servico.salvar('2026-10-23','10','20','30')
        n=self.vincular(self.janela())
        antes=banco.listar_vendas()
        for status,corpo,headers in [(503,{'message':'SEGREDO-HTTP-NAO-EXIBIR'},{}),(200,b'{invalido',{}),(302,{}, {'Location':'https://destino-proibido.invalid/roubo'})]:
            with self.subTest(status=status):
                quantidade=len(self.servidor.conexoes)
                primeira=len(self.servidor.requisicoes)
                self.servidor.falhar(RPC+'sincronizar_desktop_v2',status,corpo,headers)
                n.sincronizar();self.esperar(n)
                self.assertEqual(banco.listar_vendas(),antes)
                self.assertNotIn('SEGREDO',n.status);self.assertNotIn('roubo',n.status)
                self.assertEqual(len(self.servidor.conexoes),quantidade+2)
                self.assertEqual([r['caminho'] for r in self.servidor.requisicoes[primeira:]],[RPC+'consultar_fechamentos',RPC+'sincronizar_desktop_v2'])
                self.assertTrue(n.janela.isEnabled())
        n.sincronizar();self.esperar(n);self.assertIn('concluída',n.status)

    def test_401_na_renovacao_pausa_sem_enviar_lote(self):
        n=self.vincular(self.janela());n.sessao=replace(n.sessao,expira_em=1)
        n.cliente._ultima_sessao=None
        inicio=len(self.servidor.requisicoes)
        self.servidor.falhar('/auth/v1/token?grant_type=refresh_token',401)
        n.sincronizar();self.esperar(n)
        self.assertTrue(n.agendador.pausado)
        self.assertEqual([r['caminho'] for r in self.servidor.requisicoes[inicio:]],['/auth/v1/token?grant_type=refresh_token'])
        self.assertNotIn('SEGREDO',n.status)

    def test_fechamento_tls_concorrencia_preserva_parcelas(self):
        financeiro.inicializar()
        financeiro.salvar_lancamento('despesa','2090-10-09','Compra fictícia','100','Cartão de crédito','Outros',3,data_compra='2090-10-09')
        n=self.vincular(self.janela());antes=financeiro.listar_lancamentos('0001-01-01','9999-12-31')
        config=[];n.consultar_fechamento(config.append);self.esperar(n)
        self.assertEqual(config[-1]['versao'],0)
        n.salvar_fechamento(0,'2090-11-01',15,config.append);self.esperar(n)
        self.assertEqual(config[-1]['versao'],1)
        self.assertEqual(fechamento.periodo(2026,9),('2026-09-10','2026-10-09'))
        n.salvar_fechamento(0,'2090-12-01',20,config.append);self.esperar(n)
        self.assertIn('mudou',n.status)
        self.assertEqual(fechamento.estado()['versao'],1)
        self.assertEqual(financeiro.listar_lancamentos('0001-01-01','9999-12-31'),antes)

    def test_consulta_tls_em_espera_mantem_interface_e_adia_edicao(self):
        j=self.janela();n=self.vincular(j)
        self.servidor.bloquear=RPC+'sincronizar_desktop_v2'
        n.automaticamente()
        fim=time.monotonic()+5
        while not self.servidor.iniciada.is_set() and time.monotonic()<fim:
            self.app.processEvents();time.sleep(.005)
        self.assertTrue(self.servidor.iniciada.is_set())
        vistos=[];Q.QTimer.singleShot(0,lambda:vistos.append(True));self.app.processEvents()
        self.assertTrue(vistos);self.assertTrue(j.isEnabled())
        form=j.abrir_formulario();self.app.processEvents()
        self.servidor.liberar.set();self.esperar(n)
        self.assertTrue(form.isVisible());self.assertFalse(n.recebendo)
        form.reject()

    def test_entrada_padrao_continua_sem_cliente_http(self):
        j=Janela(self.servico,self.pasta)
        self.addCleanup(j.deleteLater);self.addCleanup(j.close)
        self.assertIs(type(j.nuvem.cliente),ClienteEstudo)
        self.assertEqual(self.servidor.requisicoes,[])

    def test_conflito_tls_exige_escolha_e_reconfere_versoes(self):
        self.servico.salvar('2026-10-23','10','20','30')
        n=self.vincular(self.janela());venda=banco.buscar_venda_por_data('2026-10-23')
        self.servico.salvar('2026-10-23','10','40','30',venda)
        self.servidor.modelo.simular_venda_externa()
        n.sincronizar();self.esperar(n)
        self.assertTrue(n.agendador.pausado)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],40)
        n.conferir_conflitos();self.esperar(n)
        revisao=n.revisao;self.assertEqual(len(revisao['conflitos']),1)
        r=revisao['conflitos'][0];escolhas={r['tabela']+':'+r['id']:'nuvem'}
        self.servidor.modelo.simular_venda_externa()
        n.sincronizar(revisao,escolhas);self.esperar(n)
        self.assertIn('mudaram desde a revisão',n.status)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],40)
        n.conferir_conflitos();self.esperar(n)
        r=n.revisao['conflitos'][0]
        n.sincronizar(n.revisao,{r['tabela']+':'+r['id']:'nuvem'});self.esperar(n)
        self.assertEqual(banco.buscar_venda_por_data('2026-10-23')[3],22)

    def test_pfs01_http_pausa_sem_substituir_dados_locais(self):
        self.servico.salvar('2026-10-23','10','20','30')
        n=self.vincular(self.janela());antes=banco.listar_vendas()
        self.servidor.falhar(RPC+'sincronizar_desktop_v2',409,{'code':'PFS01','message':'SEGREDO'})
        n.sincronizar();self.esperar(n)
        self.assertTrue(n.agendador.pausado)
        self.assertEqual(banco.listar_vendas(),antes)
        self.assertNotIn('SEGREDO',n.status)
        n.sincronizar();self.esperar(n);self.assertIn('concluída',n.status)

    def test_sql006_ausente_nao_envia_data_compra_ao_legado(self):
        financeiro.inicializar()
        financeiro.salvar_lancamento('despesa','2026-10-09','Compra fictícia','100','Cartão de crédito','Outros',3,data_compra='2026-10-09')
        n=self.janela().nuvem;n.conectar();self.esperar(n)
        self.servidor.falhar(RPC+'migrar_desktop_v2',404,{'code':'PGRST202'})
        n.conferir();self.esperar(n)
        self.assertIsNone(n.preparacao)
        self.assertIn('006_datas_compras',n.status)
        self.assertNotIn(RPC+'migrar_desktop',[r['caminho'] for r in self.servidor.requisicoes])
        self.assertEqual(len(financeiro.listar_lancamentos('0001-01-01','9999-12-31')),3)
        self.assertFalse(self.servidor.modelo.arquivo.exists())

    @unittest.skipUnless(sessao_windows.DISPONIVEL,'DPAPI nativa requer Windows')
    def test_reabertura_dpapi_renova_sem_pedir_login_novamente(self):
        from ProgramFeira import automacao_nuvem
        n=self.vincular(self.janela());n.agendador.parar()
        arquivo=self.pasta/sessao_windows.NOME
        self.assertTrue(arquivo.exists())
        self.assertNotIn(b'renovavel-ficticio',arquivo.read_bytes())
        automacao_nuvem.salvar_preferencia(self.pasta,False)
        inicio=len(self.servidor.requisicoes)
        outro=Janela(self.servico,self.pasta,cliente_nuvem=self.servidor.cliente())
        self.addCleanup(outro.deleteLater);self.addCleanup(outro.close)
        self.addCleanup(self.esperar,outro.nuvem)
        self.assertIsNotNone(outro.nuvem.sessao,outro.nuvem.status)
        outro.nuvem.sincronizar();self.esperar(outro.nuvem)
        paths=[r['caminho'] for r in self.servidor.requisicoes[inicio:]]
        self.assertIn('/auth/v1/token?grant_type=refresh_token',paths)
        self.assertNotIn('/auth/v1/token?grant_type=password',paths)
        self.assertIn('concluída',outro.nuvem.status)

    def test_certificado_sem_confianca_e_recusado_antes_de_enviar_credenciais(self):
        import ssl
        self.assertTrue(self.servidor.contexto_cliente.check_hostname)
        self.assertEqual(self.servidor.contexto_cliente.verify_mode,ssl.CERT_REQUIRED)
        j=self.janela();j.nuvem.cliente=self.servidor.cliente(confiar=False)
        j.nuvem.conectar();self.esperar(j.nuvem)
        self.assertIsNone(j.nuvem.sessao)
        self.assertEqual(self.servidor.requisicoes,[])
        self.assertEqual(self.servidor.conexoes,[(HOST,443)])
        self.assertIn('Não foi possível conectar',j.nuvem.status)

    def test_guarda_de_saida_detecta_redirect_se_handler_for_removido(self):
        # Controle negativo: o teste normal deve falhar se o bloqueio do
        # cliente desaparecer; a guarda não pode esconder essa tentativa.
        from urllib import request
        cliente=self.servidor.cliente()
        cliente._abrir=request.build_opener(request.ProxyHandler({}),request.HTTPSHandler(context=self.servidor.contexto_cliente)).open
        self.servidor.falhar(RPC+'sincronizar_desktop_v2',302,{}, {'Location':'https://destino-proibido.invalid/roubo'})
        with self.assertRaisesRegex(AssertionError,'Saída externa proibida'):
            cliente._post(RPC+'sincronizar_desktop_v2',{},'acesso-ficticio')
        self.assertEqual(self.servidor.conexoes,[(HOST,443),('destino-proibido.invalid',443)])
        self.assertEqual(len(self.servidor.requisicoes),1)
