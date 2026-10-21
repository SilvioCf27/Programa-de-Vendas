"""Relógio simulado verifica o agendamento sem dormir ou acessar a rede."""
from pathlib import Path
import tempfile
import unittest
from ProgramFeira.automacao_nuvem import Agendador, carregar_preferencia, salvar_preferencia
from ProgramFeira.nuvem import ErroNuvem, ErroTemporario, ConflitoSincronizacao, SessaoExpirada


class Relogio:
    def __init__(self):
        self.tarefas = {}
        self.contador = 0

    def after(self, atraso, callback):
        self.contador += 1
        self.tarefas[self.contador] = (atraso, callback)
        return self.contador

    def after_cancel(self, identificador):
        self.tarefas.pop(identificador, None)

    def disparar(self):
        identificador = next(iter(self.tarefas))
        atraso, callback = self.tarefas.pop(identificador)
        callback()
        return atraso


class AutomacaoTests(unittest.TestCase):
    def setUp(self):
        self.relogio = Relogio()
        self.ativo = self.livre = True
        self.chamadas = 0
        self.agenda = Agendador(self.relogio, lambda: self.ativo, lambda: self.livre, self.iniciar)

    def iniciar(self):
        self.chamadas += 1

    def test_primeira_consulta_intervalo_e_ausencia_de_sobreposicao(self):
        self.agenda.ativar()
        self.assertEqual(self.relogio.disparar(), 2000)
        self.assertEqual(self.chamadas, 1)
        self.agenda.agendar(1)
        self.assertFalse(self.relogio.tarefas)
        self.agenda.concluir()
        self.assertEqual(self.relogio.disparar(), 60000)
        self.assertEqual(self.chamadas, 2)

    def test_formulario_aberto_aguarda_sem_chamar_rede(self):
        self.livre = False
        self.agenda.ativar()
        self.relogio.disparar()
        self.assertEqual(self.chamadas, 0)
        self.assertEqual(self.relogio.disparar(), 5000)
        self.livre = True
        self.relogio.disparar()
        self.assertEqual(self.chamadas, 1)

    def test_rede_falha_com_intervalos_crescentes_e_retorna_ao_normal(self):
        self.agenda.ativar()
        self.relogio.disparar()
        for esperado in (60000, 120000, 240000, 300000, 300000):
            self.agenda.concluir(ErroTemporario('Sem rede'))
            self.assertEqual(self.relogio.disparar(), esperado)
        self.agenda.concluir()
        self.assertEqual(self.relogio.disparar(), 60000)

    def test_conflito_sessao_expirada_ou_erro_de_dados_pausam(self):
        for erro in (ConflitoSincronizacao('Conflito'), SessaoExpirada('Login'), ErroNuvem('Dado inválido')):
            self.agenda.ativar()
            self.relogio.disparar()
            self.agenda.concluir(erro)
            self.assertTrue(self.agenda.pausado)
            self.assertFalse(self.relogio.tarefas)
        self.agenda.ativar()
        self.assertFalse(self.agenda.pausado)
        self.assertTrue(self.relogio.tarefas)

    def test_desligar_cancelar_e_reagendar_nao_acumulam_tarefas(self):
        self.agenda.ativar()
        self.agenda.ativar()
        self.assertEqual(len(self.relogio.tarefas), 1)
        self.ativo = False
        self.relogio.disparar()
        self.assertEqual(self.chamadas, 0)
        self.agenda.parar()
        self.assertFalse(self.relogio.tarefas)

    def test_preferencia_persistida_sem_credenciais(self):
        with tempfile.TemporaryDirectory() as pasta:
            self.assertTrue(carregar_preferencia(pasta))
            salvar_preferencia(pasta, False)
            self.assertFalse(carregar_preferencia(pasta))
            salvar_preferencia(pasta, True)
            self.assertTrue(carregar_preferencia(pasta))
            self.assertEqual(list(Path(pasta).iterdir()), [Path(pasta) / 'sincronizacao.json'])
            self.assertEqual((Path(pasta) / 'sincronizacao.json').read_text(), '{"automatica": true}')
            (Path(pasta) / 'sincronizacao.json').write_text('[]')
            self.assertFalse(carregar_preferencia(pasta))
