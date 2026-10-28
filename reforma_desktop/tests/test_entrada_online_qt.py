"""Modo de validação real com GUI e HTTPS loopback, sem conta externa."""
from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_contrato_https_qt as contrato
from servidor_https import URL,CHAVE
from ProgramFeira import nuvem,sessao_windows
from ProgramFeira.database import banco
from reforma_desktop.aplicacao import Janela
from reforma_desktop import execucao_validacao as execucao,perfil_validacao as perfil
from reforma_desktop.ambiente import MARCADOR,CONTEUDO
from PySide6 import QtWidgets as W


class EntradaOnlineTests(unittest.TestCase):
    setUpClass=classmethod(contrato.ContratoHttpsTests.setUpClass.__func__)
    setUp=contrato.ContratoHttpsTests.setUp
    esperar=contrato.ContratoHttpsTests.esperar

    def janela(self):
        j=Janela(self.servico,self.pasta,cliente_nuvem=self.cliente,validacao_real=True)
        self.addCleanup(j.deleteLater);self.addCleanup(j.close)
        self.addCleanup(j.nuvem.agendador.parar);self.addCleanup(self.esperar,j.nuvem)
        j.show();self.app.processEvents()
        return j

    def login(self,j):
        p=j.conexao_nuvem();p.email.setText('validacao@example.invalid');p.senha.setText('senha-ficticia')
        p.entrar();self.esperar(j.nuvem)
        self.assertTrue(j.nuvem.sessao_verificada,j.nuvem.status)
        return p

    def test_abertura_e_login_nao_transferem_e_senha_e_limpa(self):
        j=self.janela();p=j.conexao_nuvem()
        self.assertEqual(self.servidor.requisicoes,[])
        self.assertNotIn('simular',p.botoes);self.assertTrue(p.automatico.isHidden())
        self.assertEqual(p.senha.echoMode(),W.QLineEdit.EchoMode.Password)
        p.resize(720,500);self.app.processEvents()
        scroll=p.findChild(W.QScrollArea)
        self.assertEqual(scroll.horizontalScrollBar().maximum(),0)
        self.assertTrue(scroll.verticalScrollBar().maximum()>0)
        self.login(j)
        self.assertEqual(p.senha.text(),'')
        self.assertEqual([r['caminho'] for r in self.servidor.requisicoes],['/auth/v1/token?grant_type=password',contrato.RPC+'usuario_autorizado'])
        self.assertEqual(self.servidor.requisicoes[0]['corpo']['email'],'validacao@example.invalid')
        self.assertFalse(j.nuvem.vinculado);self.assertFalse(j.nuvem.automatico)
        self.assertIn(URL,j.windowTitle())

    def test_credenciais_vazias_e_envio_direto_sao_recusados(self):
        j=self.janela();p=j.conexao_nuvem();p.entrar();self.esperar(j.nuvem)
        self.assertEqual(self.servidor.requisicoes,[])
        self.login(j);antes=len(self.servidor.requisicoes)
        j.nuvem.sincronizar();self.esperar(j.nuvem)
        j.nuvem.automaticamente()
        self.assertFalse(j.nuvem.alterar_automatico(True))
        self.assertEqual(len(self.servidor.requisicoes),antes)
        self.assertFalse(p.botoes['sincronizar'].isEnabled())

    def test_transferencia_exige_confirmacao_e_mudanca_local_nao_envia(self):
        self.servico.salvar('2026-10-23','10','20','30')
        j=self.janela();p=self.login(j);n=j.nuvem
        n.conferir();self.esperar(n);self.assertIsNotNone(n.preparacao)
        antes=len(self.servidor.requisicoes)
        with patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.No):p.transferir()
        self.assertEqual(len(self.servidor.requisicoes),antes)
        with patch.object(W.QMessageBox,'question',return_value=W.QMessageBox.StandardButton.Yes) as pergunta:p.transferir()
        self.esperar(n);self.assertIn(URL,pergunta.call_args.args[2])
        self.assertTrue(n.transferencia_confirmada)
        n.sincronizar();self.esperar(n);self.assertTrue(n.vinculado,n.status)
        antes=len(self.servidor.requisicoes)
        self.servico.salvar('2026-10-25','1','2','3');j.atualizar();self.app.processEvents()
        self.assertEqual(len(self.servidor.requisicoes),antes)
        n.sincronizar();self.esperar(n)
        self.assertEqual(len(self.servidor.modelo.ler()['dados']['vendas']),2)

    def test_retomar_sessao_e_explicito_e_reconfere_autorizacao(self):
        j=self.janela();p=self.login(j);n=j.nuvem
        n.sessao=replace(n.sessao,expira_em=1);n.cliente._ultima_sessao=None
        n.sessao_verificada=False;antes=len(self.servidor.requisicoes)
        n.conferir();self.esperar(n)
        self.assertEqual(len(self.servidor.requisicoes),antes)
        n.retomar();self.esperar(n)
        self.assertTrue(n.sessao_verificada)
        self.assertEqual([r['caminho'] for r in self.servidor.requisicoes[antes:]],['/auth/v1/token?grant_type=refresh_token',contrato.RPC+'usuario_autorizado'])
        self.servidor.autorizado=False;n.retomar();self.esperar(n)
        self.assertFalse(n.sessao_verificada)

    def test_falha_de_login_libera_campos_sem_exibir_senha(self):
        j=self.janela();p=j.conexao_nuvem()
        self.servidor.falhar('/auth/v1/token?grant_type=password',401)
        p.email.setText('teste@example.invalid');p.senha.setText('SEGREDO-NAO-EXIBIR')
        p.entrar();self.esperar(j.nuvem)
        self.assertEqual(p.senha.text(),'');self.assertTrue(p.email.isEnabled())
        self.assertNotIn('SEGREDO',p.status.toPlainText())
        self.assertFalse(j.nuvem.sessao_verificada)

    def test_atualizador_ficticio_e_restauracao_nao_sao_abertos(self):
        j=self.janela();c=j.configuracoes()
        with patch.object(W.QMessageBox,'information') as aviso:j.atualizacoes();self.assertTrue(aviso.called)
        with patch.object(W.QFileDialog,'getOpenFileName',side_effect=AssertionError('Não importar banco pessoal')):c.restaurar()
        self.assertIn('Não importa bancos',c.status.text());c.close()

    def preparar_perfil(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        raiz=Path(temp.name)
        (self.pasta/MARCADOR).write_text(CONTEUDO,encoding='utf-8')
        (self.pasta/'nuvem.json').write_text(json.dumps({'url':'https://origem-ficticia.supabase.co','chave_publica':CHAVE}))
        p=perfil.preparar(self.pasta,raiz/'perfil-novo',URL,CHAVE)
        return p,raiz/'execucao'

    def test_execucao_independente_persiste_sem_copiar_historico_ou_sessao(self):
        p,r=self.preparar_perfil();execucao.preparar(p,r)
        self.assertFalse((r/'vendas.db').exists());self.assertFalse((r/sessao_windows.NOME).exists())
        self.assertEqual(execucao.preparar(p,r),r.resolve())
        perfil.conferir(p)
        (r/'nuvem.json').write_text(json.dumps({'url':'https://outro.supabase.co','chave_publica':CHAVE}))
        with self.assertRaisesRegex(ValueError,'projeto'):execucao.preparar(p,r)

    def test_execucao_recusa_perfil_ou_pasta_existente_sem_marca(self):
        p,r=self.preparar_perfil()
        with self.assertRaises(ValueError):execucao.preparar(p,p/'aplicacao')
        r.mkdir();(r/'guardar.txt').write_text('preservar')
        with self.assertRaises(ValueError):execucao.preparar(p,r)
        self.assertEqual((r/'guardar.txt').read_text(),'preservar')

    def test_entrada_por_subprocesso_renderiza_sem_http_e_reabre(self):
        p,r=self.preparar_perfil();saida=r.parent/'captura.png'
        codigo="import sys; from unittest.mock import patch; import executar_validacao; tentativas=[]\ndef bloquear(*a,**k):\n tentativas.append(True); raise AssertionError('HTTP proibido na captura')\nwith patch('urllib.request.OpenerDirector.open',bloquear):\n retorno=executar_validacao.main()\nassert not tentativas\nraise SystemExit(retorno)"
        cmd=[sys.executable,'-c',codigo,'--perfil',str(p),'--pasta-execucao',str(r),'--captura',str(saida)]
        for _ in range(2):
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=45,cwd=Path(__file__).resolve().parents[2])
            self.assertEqual(proc.returncode,0,proc.stderr[-1000:])
        self.assertTrue(saida.exists())
        with closing(sqlite3.connect(r/'vendas.db')) as c:self.assertEqual(c.execute('SELECT count(*) FROM vendas').fetchone()[0],0)
        perfil.conferir(p)

    def test_reabertura_recusa_banco_vinculado_a_outro_projeto(self):
        p,r=self.preparar_perfil();execucao.preparar(p,r)
        with closing(sqlite3.connect(r/'vendas.db')) as c,c:
            c.execute('CREATE TABLE nuvem_sync_estado(projeto TEXT)')
            c.execute("INSERT INTO nuvem_sync_estado VALUES('https://outro.supabase.co')")
        with self.assertRaisesRegex(ValueError,'outro projeto'):execucao.preparar(p,r)

    def test_modo_online_exige_cliente_e_logout_invalida_acesso(self):
        with self.assertRaises(ValueError):Janela(self.servico,self.pasta,validacao_real=True)
        j=self.janela();self.login(j);j.nuvem.desconectar()
        self.assertFalse(j.nuvem.sessao_verificada)
        self.assertFalse(j.nuvem.transferencia_confirmada)
        self.assertIsNone(j.nuvem.sessao)

    def test_novo_login_falha_preserva_sessao_antiga_somente_para_retomada(self):
        j=self.janela();p=self.login(j);anterior=j.nuvem.sessao
        self.servidor.falhar('/auth/v1/token?grant_type=password',401)
        p.email.setText('outra@example.invalid');p.senha.setText('senha-invalida');p.entrar();self.esperar(j.nuvem)
        self.assertIs(j.nuvem.sessao,anterior)
        self.assertFalse(j.nuvem.sessao_verificada)
        self.assertIn('verificação pendente',p.conta.text())
        self.assertTrue(p.botoes['retomar'].isEnabled())
        self.assertFalse(p.botoes['conferir'].isEnabled())

    def test_fechar_principal_fecha_modal_e_libera_outras_janelas(self):
        j=self.janela();p=self.login(j)
        self.assertTrue(p.isVisible())
        self.assertTrue(j.close())
        self.assertFalse(p.isVisible())
        self.app.processEvents()
        self.assertIsNone(W.QApplication.activeModalWidget())
