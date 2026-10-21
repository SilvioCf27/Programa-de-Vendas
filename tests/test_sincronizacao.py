"""Cenários de duas cópias, rede interrompida e retomada, sem serviço real."""
from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from uuid import uuid4
from ProgramFeira import migracao_nuvem as migracao, sincronizacao as sync
from ProgramFeira.nuvem import Sessao, ErroNuvem, ConflitoSincronizacao

USUARIO = '11111111-1111-4111-8111-111111111111'


class Servidor:
    url = 'https://projeto-ficticio.supabase.co'

    def __init__(self, banco):
        with closing(sqlite3.connect(banco)) as c:
            dados = migracao.extrair(c, USUARIO)
        self.dados = {t: {r.get('id', str(uuid4())): dict(r, versao=1) for r in dados[t]} for t in sync.TABELAS}
        for tabela in self.dados.values():
            for identificador, r in tabela.items():
                r['id'] = identificador
        self.recibos = {}
        self.perder_resposta = False
        self.antes_envio = None
        self.chamadas = 0

    def sincronizar(self, sessao, alteracoes=None, operacao_id=None):
        self.chamadas += 1
        alteracoes = alteracoes or []
        repetida = operacao_id in self.recibos
        if operacao_id and not repetida:
            if self.antes_envio:
                self.antes_envio()
                self.antes_envio = None
            novos = copy.deepcopy(self.dados)
            for op in alteracoes:
                tabela = novos[op['tabela']]
                atual = tabela.get(op['id'])
                if (atual['versao'] if atual else None) != op['versao']:
                    raise ConflitoSincronizacao('Versão alterada')
                if op['acao'] == 'excluir':
                    del tabela[op['id']]
                else:
                    tabela[op['id']] = dict(op['dados'], id=op['id'], versao=atual['versao'] + 1 if atual else 1)
            self.dados = novos
            self.recibos[operacao_id] = copy.deepcopy(alteracoes)
            if self.perder_resposta:
                self.perder_resposta = False
                raise ErroNuvem('Resposta perdida após confirmação no servidor')
        if repetida:
            assert self.recibos[operacao_id] == alteracoes
        return dict(protocolo=1, usuario_id=sessao.usuario_id, operacao_id=operacao_id, repetida=repetida, dados={t: list(copy.deepcopy(v).values()) for t, v in self.dados.items()})

    def venda(self, dia):
        return next(r for r in self.dados['vendas'].values() if r['data'] == dia)

    def editar(self, tabela, identificador, **valores):
        self.dados[tabela][identificador].update(valores)
        self.dados[tabela][identificador]['versao'] += 1


class SincronizacaoTests(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.banco = Path(pasta.name) / 'vendas.db'
        with closing(sqlite3.connect(self.banco)) as c, c:
            c.executescript('''
                create table vendas(id integer primary key autoincrement,data text unique,dinheiro real,pix real,cartao real);
                insert into vendas(data,dinheiro,pix,cartao) values ('2030-01-01',1.01,2.02,3.03),('2030-01-02',0,0,0);
                create table financeiro_lancamentos(id integer primary key autoincrement,tipo text,data text,descricao text,valor_centavos integer,meio text,categoria text,grupo text,parcela integer,parcelas integer);
                insert into financeiro_lancamentos(tipo,data,descricao,valor_centavos,meio,categoria,grupo,parcela,parcelas) values ('despesa','2030-02-09','Despesa fictícia',12345,'Pix','Casa',null,1,1);
                create table financeiro_taxas_anuais(ano integer primary key,inicio text,fim text,valor_centavos integer,natureza text,observacao text);
                insert into financeiro_taxas_anuais values(2030,'2030-01-01','2030-01-31',500,'Estimada','');
            ''')
        self.sessao = Sessao(USUARIO, 'teste@example.invalid', 'token-ficticio')
        self.servidor = Servidor(self.banco)

    def executar(self):
        return sync.sincronizar(self.banco, self.servidor, self.sessao)

    def sql(self, sql, parametros=()):
        with closing(sqlite3.connect(self.banco)) as c, c:
            return c.execute(sql, parametros).fetchall()

    def test_vinculo_inicial_preserva_ids_e_backup_e_nao_envia_alteracoes(self):
        resultado = self.executar()
        self.assertTrue(sync.vinculado(self.banco))
        self.assertEqual(resultado['enviadas'], 0)
        self.assertEqual(resultado['recebidas'], 0)
        self.assertTrue(Path(resultado['backup']).exists())
        self.assertEqual(self.sql('select id from vendas order by id'), [(1,), (2,)])
        self.assertFalse(self.servidor.recibos)

    def test_crud_local_propagado_sem_duplicar_na_repeticao(self):
        self.executar()
        self.sql('update vendas set pix=12.34 where id=1')
        self.sql('delete from vendas where id=2')
        self.sql("insert into vendas(data,dinheiro,pix,cartao) values('2030-01-03',10,0,0)")
        r = self.executar()
        self.assertEqual(r['enviadas'], 3)
        self.assertEqual(self.servidor.venda('2030-01-01')['pix_centavos'], 1234)
        self.assertEqual(len(self.servidor.dados['vendas']), 2)
        self.assertEqual(self.executar()['enviadas'], 0)

    def test_crud_remoto_recebido_e_id_remoto_financeiro_preservado(self):
        self.executar()
        r = self.servidor.venda('2030-01-01')
        self.servidor.editar('vendas', r['id'], pix_centavos=999)
        del self.servidor.dados['vendas'][self.servidor.venda('2030-01-02')['id']]
        identificador = str(uuid4())
        self.servidor.dados['financeiro_lancamentos'][identificador] = dict(id=identificador, versao=1, tipo='despesa', data='2030-03-09', descricao='Nova fictícia', valor_centavos=100, meio='Pix', categoria='Casa', grupo=None, parcela=1, parcelas=1)
        self.assertEqual(self.executar()['recebidas'], 3)
        self.assertEqual(self.sql('select pix from vendas where id=1'), [(9.99,)])
        self.sql("update financeiro_lancamentos set valor_centavos=200 where descricao='Nova fictícia'")
        self.executar()
        self.assertEqual(self.servidor.dados['financeiro_lancamentos'][identificador]['valor_centavos'], 200)
        self.assertEqual(len(self.servidor.dados['financeiro_lancamentos']), 2)

    def test_mudancas_independentes_sao_combinadas(self):
        self.executar()
        self.sql('update vendas set dinheiro=10 where id=1')
        remota = self.servidor.venda('2030-01-02')
        self.servidor.editar('vendas', remota['id'], cartao_centavos=999)
        self.executar()
        self.assertEqual(self.sql('select dinheiro from vendas where id=1'), [(10.0,)])
        self.assertEqual(self.sql('select cartao from vendas where id=2'), [(9.99,)])
        self.assertEqual(self.servidor.venda('2030-01-01')['dinheiro_centavos'], 1000)

    def test_edicao_concorrente_interrompe_sem_sobrescrever(self):
        self.executar()
        self.sql('update vendas set pix=10 where id=1')
        r = self.servidor.venda('2030-01-01')
        self.servidor.editar('vendas', r['id'], pix_centavos=2000)
        recibos = copy.deepcopy(self.servidor.recibos)
        with self.assertRaisesRegex(ErroNuvem, 'Conflitos'):
            self.executar()
        self.assertEqual(self.sql('select pix from vendas where id=1'), [(10.0,)])
        self.assertEqual(self.servidor.venda('2030-01-01')['pix_centavos'], 2000)
        self.assertEqual(self.servidor.recibos, recibos)

    def test_exclusao_concorrente_com_edicao_nao_ressuscita_registro(self):
        self.executar()
        self.sql('update vendas set pix=10 where id=1')
        r = self.servidor.venda('2030-01-01')
        del self.servidor.dados['vendas'][r['id']]
        with self.assertRaisesRegex(ErroNuvem, 'Conflitos'):
            self.executar()
        self.assertEqual(self.sql('select count(*) from vendas'), [(2,)])
        self.assertNotIn(r['id'], self.servidor.dados['vendas'])

    def test_resposta_perdida_retomada_preserva_edicao_local_posterior(self):
        self.executar()
        self.sql('update vendas set pix=10 where id=1')
        self.servidor.perder_resposta = True
        with self.assertRaisesRegex(ErroNuvem, 'Resposta perdida'):
            self.executar()
        self.assertEqual(len(self.servidor.recibos), 1)
        self.sql('update vendas set pix=11 where id=1')
        self.executar()
        self.assertEqual(self.servidor.venda('2030-01-01')['pix_centavos'], 1100)
        self.assertEqual(self.servidor.venda('2030-01-01')['versao'], 3)
        self.assertEqual(self.sql('select pix from vendas where id=1'), [(11.0,)])
        self.assertEqual(len(self.servidor.dados['vendas']), 2)
        self.assertIsNone(self.sql('select pendente from nuvem_sync_estado')[0][0])

    def test_resposta_perdida_com_nova_edicao_nos_dois_lados_gera_conflito(self):
        self.executar()
        self.sql('update vendas set pix=10 where id=1')
        self.servidor.perder_resposta = True
        with self.assertRaises(ErroNuvem):
            self.executar()
        self.sql('update vendas set pix=11 where id=1')
        r = self.servidor.venda('2030-01-01')
        self.servidor.editar('vendas', r['id'], pix_centavos=1200)
        with self.assertRaisesRegex(ErroNuvem, 'Conflitos'):
            self.executar()
        self.assertEqual(self.sql('select pix from vendas where id=1'), [(11.0,)])
        self.assertEqual(r['pix_centavos'], 1200)

    def test_corrida_apos_leitura_descarta_somente_lote_recusado(self):
        self.executar()
        self.sql('update vendas set pix=10 where id=1')
        r = self.servidor.venda('2030-01-01')
        self.servidor.antes_envio = lambda: self.servidor.editar('vendas', r['id'], pix_centavos=1200)
        with self.assertRaises(ConflitoSincronizacao):
            self.executar()
        self.assertIsNone(self.sql('select pendente from nuvem_sync_estado')[0][0])
        with self.assertRaisesRegex(ErroNuvem, 'Conflitos'):
            self.executar()

    def test_primeiro_vinculo_com_diferencas_e_troca_de_conta_sao_bloqueados(self):
        self.sql('update vendas set pix=10 where id=1')
        with self.assertRaisesRegex(ErroNuvem, 'primeiro vínculo'):
            self.executar()
        self.assertFalse(sync.vinculado(self.banco))
        self.sql('update vendas set pix=2.02 where id=1')
        self.executar()
        chamadas = self.servidor.chamadas
        self.servidor.url = 'https://outro-projeto.supabase.co'
        with self.assertRaisesRegex(ErroNuvem, 'outra conta'):
            self.executar()
        self.assertEqual(self.servidor.chamadas, chamadas)

    def test_snapshot_incompleto_nao_remove_dados_locais(self):
        self.executar()
        original = self.servidor.sincronizar
        def incompleto(*args, **kwargs):
            resultado = original(*args, **kwargs)
            del resultado['dados']['financeiro_taxas_anuais']
            return resultado
        self.servidor.sincronizar = incompleto
        with self.assertRaisesRegex(ErroNuvem, 'inválido'):
            self.executar()
        self.assertEqual(self.sql('select count(*) from vendas'), [(2,)])
        self.assertEqual(self.sql('select count(*) from financeiro_taxas_anuais'), [(1,)])

    def test_falha_no_backup_impede_conexao(self):
        self.banco.write_bytes(b'nao-e-sqlite')
        with self.assertRaises((ValueError, sqlite3.Error)):
            self.executar()
        self.assertEqual(self.servidor.chamadas, 0)

    def test_nova_venda_igual_nos_dois_dispositivos_converge_sem_duplicar(self):
        self.executar()
        self.sql("insert into vendas(data,dinheiro,pix,cartao) values('2030-01-03',10,0,0)")
        identificador = str(uuid4())
        self.servidor.dados['vendas'][identificador] = dict(id=identificador, versao=1, data='2030-01-03', dinheiro_centavos=1000, pix_centavos=0, cartao_centavos=0)
        self.assertEqual(self.executar()['enviadas'], 0)
        self.assertEqual(self.sql('select count(*) from vendas'), [(3,)])
        self.sql("update vendas set pix=1 where data='2030-01-03'")
        self.executar()
        self.assertEqual(self.servidor.dados['vendas'][identificador]['pix_centavos'], 100)
        self.assertEqual(len(self.servidor.dados['vendas']), 3)

    def test_mudanca_de_data_e_de_ano_mantem_vinculo(self):
        self.executar()
        registro = self.servidor.venda('2030-01-01')
        self.sql("update vendas set data='2030-01-05' where id=1")
        self.executar()
        self.assertEqual(self.servidor.dados['vendas'][registro['id']]['data'], '2030-01-05')
        anual = next(iter(self.servidor.dados['financeiro_taxas_anuais'].values()))
        self.servidor.editar('financeiro_taxas_anuais', anual['id'], ano=2031, inicio='2031-01-01', fim='2031-01-31')
        self.executar()
        self.assertEqual(self.sql('select ano from financeiro_taxas_anuais'), [(2031,)])
        self.sql('update financeiro_taxas_anuais set valor_centavos=501 where ano=2031')
        self.executar()
        self.assertEqual(self.servidor.dados['financeiro_taxas_anuais'][anual['id']]['valor_centavos'], 501)

    def test_lote_pendente_nao_guarda_credenciais(self):
        self.executar()
        self.sql('update vendas set pix=10 where id=1')
        self.servidor.perder_resposta = True
        with self.assertRaises(ErroNuvem):
            self.executar()
        pendente = self.sql('select pendente from nuvem_sync_estado')[0][0]
        self.assertNotIn(self.sessao.token, pendente)
        self.assertNotIn('senha', pendente)
        self.assertTrue(json.loads(pendente)['alteracoes'])
