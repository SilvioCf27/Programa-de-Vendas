"""Entrada candidata com transporte HTTPS exclusivamente fictício e local."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_contrato_https_qt as contrato
from servidor_https import URL, CHAVE
from ProgramFeira import nuvem
from ProgramFeira.database import banco
from reforma_desktop.aplicacao import Janela
from reforma_desktop.producao import cliente_configurado, SemConfiguracao
from PySide6 import QtWidgets as W


class ProducaoTests(unittest.TestCase):
    setUpClass = classmethod(contrato.ContratoHttpsTests.setUpClass.__func__)
    setUp = contrato.ContratoHttpsTests.setUp
    esperar = contrato.ContratoHttpsTests.esperar

    def janela(self):
        j = Janela(self.servico, self.pasta, cliente_nuvem=self.cliente, producao=True)
        self.addCleanup(j.deleteLater)
        self.addCleanup(j.close)
        self.addCleanup(j.atualizador.parar)
        self.addCleanup(j.nuvem.agendador.parar)
        self.addCleanup(self.esperar, j.nuvem)
        j.show(); self.app.processEvents()
        return j

    def conectar(self, j):
        n = j.nuvem
        n.conectar('teste@example.invalid', 'somente-teste')
        self.esperar(n)
        self.assertTrue(n.sessao_verificada, n.status)
        return n

    def vincular(self, j):
        n = self.conectar(j)
        n.conferir(); self.esperar(n)
        self.assertIsNotNone(n.preparacao, n.status)
        n.transferir(); self.esperar(n)
        n.sincronizar(); self.esperar(n)
        self.assertTrue(n.vinculado, n.status)
        return n

    def test_producao_nao_usa_simulacao_nem_requer_perfil_de_estudo(self):
        j = self.janela()
        self.assertTrue(j.producao)
        self.assertFalse(j.validacao_real)
        self.assertTrue(j.atualizador.real)
        self.assertEqual(self.servidor.requisicoes, [])
        painel = j.conexao_nuvem()
        self.assertNotIn('simular', painel.botoes)
        self.assertTrue(painel.automatico.isVisible())
        self.assertTrue(hasattr(painel, 'url'))
        painel.close(); self.app.processEvents()
        atualizacoes = j.atualizacoes()
        self.assertFalse(atualizacoes.cenario.isVisible())
        self.assertEqual(atualizacoes.botoes['instalar'].text(), 'Instalar e reiniciar')
        atualizacoes.close()

    def test_auto_real_so_ativa_apos_autorizacao_e_vinculo(self):
        self.servico.salvar('2026-10-23', '10', '20', '30')
        j = self.janela(); n = self.conectar(j)
        self.assertTrue(n.alterar_automatico(True))
        self.assertFalse(n.ativo())
        n.conferir(); self.esperar(n)
        n.transferir(); self.esperar(n)
        n.sincronizar(); self.esperar(n)
        self.assertTrue(n.ativo())
        self.servico.salvar('2026-10-25', '5', '6', '7')
        self.servidor.modelo.simular_venda_externa()
        n.automaticamente(); self.esperar(n)
        self.assertIn('concluída', n.status)
        self.assertNotIn('fictícia', n.status)
        n.sessao_verificada = False
        self.assertFalse(n.ativo())

    def test_sem_configuracao_nao_construi_cliente_ficticio(self):
        (self.pasta/'nuvem.json').unlink(missing_ok=True)
        c = cliente_configurado(self.pasta)
        self.assertIs(type(c), SemConfiguracao)
        self.assertEqual(c.url, '')
        self.assertEqual(self.servidor.requisicoes, [])

    def test_configuracao_invalida_ou_troca_de_projeto_preserva_vinculo(self):
        nuvem.salvar_config(self.pasta, URL, CHAVE)
        j = self.janela(); n = self.vincular(j)
        n.desconectar()
        antes = (self.pasta/'nuvem.json').read_bytes()
        with self.assertRaises(nuvem.ErroNuvem):
            n.configurar('https://outro-ficticio.supabase.co', CHAVE)
        with self.assertRaises(nuvem.ErroNuvem):
            n.configurar(URL, 'sb_secret_nao_publica')
        self.assertEqual((self.pasta/'nuvem.json').read_bytes(), antes)
        self.assertEqual(n.cliente.url, URL)

    def test_transferencia_ainda_exige_conferencia_e_confirmacao(self):
        j = self.janela(); n = self.conectar(j)
        n.sincronizar()
        self.assertFalse(n.vinculado)
        self.assertIn('confirme', n.status)
        n.conferir(); self.esperar(n)
        popup = j.conexao_nuvem()
        with patch.object(W.QMessageBox, 'question', return_value=W.QMessageBox.StandardButton.No):
            popup.transferir()
        self.assertFalse(n.transferencia_confirmada)
        self.assertFalse(n.vinculado)
        popup.close()


if __name__ == '__main__':
    unittest.main()
