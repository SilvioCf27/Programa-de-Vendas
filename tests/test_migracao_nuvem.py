"""Snapshots e barreiras locais da transferência; dados inteiramente fictícios."""
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock
from ProgramFeira import migracao_nuvem as m
from ProgramFeira.nuvem import ErroNuvem, Sessao

USUARIO = '11111111-1111-4111-8111-111111111111'


class MigracaoTests(unittest.TestCase):
    def setUp(self):
        self.temporaria = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporaria.cleanup)
        self.banco = Path(self.temporaria.name) / 'vendas.db'
        with closing(sqlite3.connect(self.banco)) as c, c:
            c.executescript('''
                create table vendas (id integer primary key, data text, dinheiro real, pix real, cartao real);
                insert into vendas values (1,'2030-01-01',1.01,2.02,3.03),(2,'02/01/2030',10,0,0),(3,'2030-01-03',0,0,0);
                create table financeiro_lancamentos(id integer primary key, tipo text, data text, descricao text, valor_centavos integer, meio text, categoria text, grupo text, parcela integer, parcelas integer);
                insert into financeiro_lancamentos values (1,'despesa','2030-02-09','Compra fictícia',12345,'Cartão de crédito','Casa','grupo-ficticio',1,2), (2,'despesa','2030-03-09','Compra fictícia',12345,'Cartão de crédito','Casa','grupo-ficticio',2,2), (3,'taxa','2030-02-15','Taxa fictícia',123,'Outro','Feira',null,1,1);
                create table financeiro_taxas_anuais(ano integer primary key, inicio text, fim text, valor_centavos integer, natureza text, observacao text);
                insert into financeiro_taxas_anuais values(2030,'2030-01-01','2030-01-31',500,'Estimada','Observação fictícia');
            ''')
        self.sessao = Sessao(USUARIO, 'teste@example.invalid', 'token-nao-gravar')
        self.cliente = Mock()
        self.cliente.migrar.side_effect = self.responder

    @staticmethod
    def responder(sessao, dados, aplicar):
        return dict(aplicado=aplicar, novos={t: len(dados[t]) for t in m.TABELAS}, dados=copy.deepcopy(dados) if aplicar else {t: [] for t in m.TABELAS})

    def alterar(self, sql):
        with closing(sqlite3.connect(self.banco)) as c, c:
            c.execute(sql)

    def preparar(self):
        return m.preparar(self.banco, self.cliente, self.sessao)

    def test_backup_conferencia_transferencia_e_relatorio_sem_mudar_sqlite(self):
        original = hashlib.sha256(self.banco.read_bytes()).hexdigest()
        p = self.preparar()
        self.assertTrue(Path(p['relatorio']['backup']).exists())
        self.assertEqual(p['relatorio']['resumo']['registros'], dict(vendas=3, financeiro_lancamentos=3, financeiro_taxas_anuais=1))
        self.assertEqual(p['relatorio']['resumo']['dias_zerados'], 1)
        self.assertEqual(p['relatorio']['resumo']['total_centavos'], 1606)
        self.assertEqual(p['relatorio']['resumo']['despesas_centavos'], 24690)
        self.assertEqual(p['dados']['vendas'][1]['data'], '2030-01-02')
        self.assertEqual(self.cliente.migrar.call_args.args[2], False)
        final = m.transferir(p)
        self.assertEqual(final['estado'], 'transferido_e_validado')
        self.assertEqual(final['resumo'], final['resumo_nuvem'])
        self.assertEqual(hashlib.sha256(self.banco.read_bytes()).hexdigest(), original)
        relatorio = p['caminho'].read_text()
        self.assertNotIn('token-nao-gravar', relatorio)
        self.assertNotIn('senha', relatorio)
        with self.assertRaises(ErroNuvem):
            m.transferir(p)
        self.assertEqual(self.cliente.migrar.call_count, 2)

    def test_nova_conferencia_mantem_ids_estaveis_de_parcelas(self):
        a, b = self.preparar(), self.preparar()
        self.assertEqual(a['dados'], b['dados'])
        self.assertNotEqual(a['relatorio']['backup'], b['relatorio']['backup'])
        self.assertEqual(a['dados']['financeiro_lancamentos'][0]['parcela'], 1)
        self.assertEqual(a['dados']['financeiro_lancamentos'][1]['parcela'], 2)

    def test_mudanca_local_apos_conferencia_bloqueia_envio(self):
        p = self.preparar()
        self.alterar('update vendas set pix=99 where id=1')
        with self.assertRaisesRegex(ErroNuvem, 'mudou após'):
            m.transferir(p)
        self.assertEqual(self.cliente.migrar.call_count, 1)

    def test_backup_alterado_bloqueia_envio(self):
        p = self.preparar()
        with Path(p['relatorio']['backup']).open('ab') as arquivo:
            arquivo.write(b'alteracao-ficticia')
        with self.assertRaisesRegex(ErroNuvem, 'backup foi alterado'):
            m.transferir(p)
        self.assertEqual(self.cliente.migrar.call_count, 1)

    def test_divergencia_na_previa_nao_envia_e_preserva_backup(self):
        self.cliente.migrar.side_effect = ErroNuvem('Divergência fictícia')
        with self.assertRaises(ErroNuvem):
            self.preparar()
        self.assertEqual(len(list((self.banco.parent / 'backups').glob('*.db'))), 1)
        self.assertFalse(self.cliente.migrar.call_args.args[2])

    def test_falha_de_rede_durante_envio_fica_nao_confirmada_sem_repeticao_automatica(self):
        p = self.preparar()
        self.cliente.migrar.side_effect = ErroNuvem('Rede indisponível')
        with self.assertRaises(ErroNuvem):
            m.transferir(p)
        self.assertEqual(json.loads(p['caminho'].read_text())['estado'], 'envio_iniciado_resultado_a_confirmar')
        with self.assertRaisesRegex(ErroNuvem, 'nova conferência'):
            m.transferir(p)
        self.assertEqual(self.cliente.migrar.call_count, 2)

    def test_resposta_parcial_nao_e_considerada_sucesso(self):
        p = self.preparar()
        resposta = self.responder(self.sessao, p['dados'], True)
        resposta['dados']['vendas'].pop()
        self.cliente.migrar.side_effect = None
        self.cliente.migrar.return_value = resposta
        with self.assertRaisesRegex(ErroNuvem, 'não corresponde'):
            m.transferir(p)
        self.assertNotEqual(json.loads(p['caminho'].read_text())['estado'], 'transferido_e_validado')

    def test_datas_duplicadas_convertidas_valores_fracionados_e_taxas_sobrepostas_interrompem(self):
        casos = [
            "update vendas set data='01/01/2030' where id=2",
            'update vendas set dinheiro=1.001 where id=1',
            'update vendas set pix=-1 where id=1',
            "update vendas set data='2030-02-30' where id=1",
            "update financeiro_lancamentos set data='2030-01-15' where tipo='taxa'",
            "update financeiro_lancamentos set meio='Pix' where id=1",
        ]
        for sql in casos:
            with self.subTest(sql=sql):
                with closing(sqlite3.connect(self.banco)) as c:
                    c.execute('begin')
                    c.execute(sql)
                    with self.assertRaises(ErroNuvem):
                        m.extrair(c, USUARIO)
                    c.rollback()
        self.cliente.migrar.assert_not_called()

    def test_falha_de_backup_impede_qualquer_chamada_a_nuvem(self):
        self.banco.write_bytes(b'nao-e-sqlite')
        with self.assertRaises((ValueError, sqlite3.Error)):
            self.preparar()
        self.cliente.migrar.assert_not_called()
