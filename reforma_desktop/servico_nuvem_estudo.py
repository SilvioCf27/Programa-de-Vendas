"""Serviço fictício local. Nunca encaminha requisições ao Supabase.

Exercita o cliente e o protocolo existentes; não é servidor de produção nem
substitui testes reais de autorização, RLS e concorrência no Supabase.
"""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
from uuid import uuid4
from ProgramFeira import nuvem, migracao_nuvem as migracao

URL = 'https://estudo-qt.supabase.co'
USUARIO = '11111111-1111-4111-8111-111111111111'
EMAIL = 'estudo@example.invalid'


class ClienteEstudo(nuvem.ClienteNuvem):
    def __init__(self, pasta):
        super().__init__(URL, 'sb_publishable_somente_estudo')
        self.arquivo = Path(pasta) / 'servico-nuvem-estudo.json'
        self.lock = threading.RLock()
        self.indisponivel = False
        self.perder_resposta = False

    def ler(self):
        try:
            dados = json.loads(self.arquivo.read_text(encoding='utf-8'))
            if dados['modo'] != 'somente-estudo' or set(dados['dados']) != set(migracao.TABELAS):
                raise ValueError()
            return dados
        except FileNotFoundError:
            return dict(modo='somente-estudo', dados={t: {} for t in migracao.TABELAS}, recibos={})
        except (OSError, ValueError, KeyError, TypeError):
            raise nuvem.ErroNuvem('O serviço fictício local não pôde ser lido. Nenhum dado foi enviado a um serviço real.') from None

    def gravar(self, estado):
        fd, nome = tempfile.mkstemp(dir=self.arquivo.parent, prefix='.nuvem-estudo-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(estado, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(nome, self.arquivo)
        finally:
            Path(nome).unlink(missing_ok=True)

    @staticmethod
    def corpo(tabela, r):
        return {k: v for k, v in r.items() if k != 'versao' and (k != 'id' or tabela == 'financeiro_lancamentos')}

    def _post(self, caminho, dados, token=None):
        if self.indisponivel:
            raise nuvem.ErroTemporario('Serviço fictício indisponível. Dados locais preservados.')
        if caminho.startswith('/auth/v1/token?grant_type='):
            if caminho not in ('/auth/v1/token?grant_type=password', '/auth/v1/token?grant_type=refresh_token'):
                raise nuvem.ErroNuvem('Operação não disponível no estudo.')
            return dict(access_token='acesso-ficticio', refresh_token='renovavel-ficticio', expires_in=3600, user=dict(id=USUARIO, email=EMAIL))
        if caminho == '/rest/v1/rpc/usuario_autorizado':
            return token == 'acesso-ficticio'
        if token != 'acesso-ficticio':
            raise nuvem.SessaoExpirada('Reconecte a sessão fictícia do estudo.')
        if caminho == '/rest/v1/rpc/consultar_fechamentos':
            return dict(versao=0, historico=[])
        with self.lock:
            estado = self.ler()
            if caminho == '/rest/v1/rpc/migrar_desktop_v2':
                resposta = self.migrar_local(estado, dados['dados'], dados['aplicar'])
            elif caminho == '/rest/v1/rpc/sincronizar_desktop_v2':
                resposta = self.sincronizar_local(estado, dados['alteracoes'], dados['operacao_id'])
            else:
                raise nuvem.ErroNuvem('Operação bloqueada no serviço fictício. Não há encaminhamento para a rede.')
            return resposta

    def migrar_local(self, estado, dados, aplicar):
        novos, anteriores = {}, {}
        for tabela in migracao.TABELAS:
            chave = 'data' if tabela == 'vendas' else 'ano' if tabela == 'financeiro_taxas_anuais' else 'id'
            mapa = {r[chave]: r for r in dados[tabela]}
            atuais = [self.corpo(tabela, r) for r in estado['dados'][tabela].values()]
            if any(mapa.get(r[chave]) != r for r in atuais):
                raise nuvem.ErroNuvem('Há dados divergentes ou extras no serviço fictício. Migração interrompida.')
            anteriores[tabela] = atuais
            presentes = {r[chave] for r in atuais}
            novos[tabela] = sum(r[chave] not in presentes for r in dados[tabela])
            if aplicar:
                for r in dados[tabela]:
                    if r[chave] not in presentes:
                        i = r.get('id') or str(uuid4())
                        estado['dados'][tabela][i] = dict(r, id=i, versao=1)
        if aplicar:
            self.gravar(estado)
        return dict(aplicado=aplicar, novos=novos, dados=copy.deepcopy(dados if aplicar else anteriores))

    def sincronizar_local(self, estado, alteracoes, operacao):
        repetida = operacao in estado['recibos']
        if operacao and not repetida:
            for op in alteracoes:
                tabela = estado['dados'][op['tabela']]
                atual = tabela.get(op['id'])
                if (atual['versao'] if atual else None) != op['versao']:
                    raise nuvem.ConflitoSincronizacao('Versão fictícia alterada. Confira novamente os registros.')
                if op['acao'] == 'excluir':
                    del tabela[op['id']]
                else:
                    corpo = dict(op['dados'])
                    if op['tabela'] == 'financeiro_lancamentos':
                        corpo.setdefault('data_compra', None)
                    tabela[op['id']] = dict(corpo, id=op['id'], versao=atual['versao'] + 1 if atual else 1)
            estado['recibos'][operacao] = alteracoes
            self.gravar(estado)
            if self.perder_resposta:
                self.perder_resposta = False
                raise nuvem.ErroTemporario('Resposta fictícia perdida após confirmação; tente novamente para confirmar o mesmo lote.')
        elif repetida and estado['recibos'][operacao] != alteracoes:
            raise nuvem.ErroNuvem('Recibo fictício divergente. Operação interrompida.')
        return dict(protocolo=2, usuario_id=USUARIO, operacao_id=operacao, repetida=repetida,
                    dados={t: list(copy.deepcopy(v).values()) for t, v in estado['dados'].items()})

    def simular_venda_externa(self):
        with self.lock:
            estado = self.ler()
            vendas = list(estado['dados']['vendas'].values())
            if not vendas:
                raise nuvem.ErroNuvem('Transfira os exemplos antes de simular uma alteração externa.')
            r = max(vendas, key=lambda r: r['data'])
            r['pix_centavos'] += 100
            r['versao'] += 1
            self.gravar(estado)
            return r['data']
