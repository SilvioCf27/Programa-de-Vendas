"""Configuração pública e autenticação no Supabase, sem acessar o SQLite."""
import base64
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib import error, request


class ErroNuvem(ValueError):
    """Mensagem segura para exibição, sem respostas ou credenciais do serviço."""


class ErroTemporario(ErroNuvem):
    """Rede ou serviço indisponível: permite uma nova tentativa com intervalo."""


class SessaoExpirada(ErroNuvem):
    """Exige um novo login; não deve gerar tentativas automáticas repetidas."""


class LoteRecusado(ErroNuvem):
    """O servidor cancelou a transação inteira; o lote pode ser replanejado."""


class ConflitoSincronizacao(LoteRecusado):
    """O servidor recusou integralmente um lote por mudança concorrente."""


def validar_config(url, chave):
    if not isinstance(url, str) or not isinstance(chave, str):
        raise ErroNuvem('Informe a URL e a chave pública do projeto.')
    url, chave = url.strip().rstrip('/'), chave.strip()
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', url):
        raise ErroNuvem('Use a Project URL HTTPS do Supabase, terminada em .supabase.co.')
    publica = bool(re.fullmatch(r'sb_publishable_[A-Za-z0-9_-]+', chave))
    if not publica:
        try:
            partes = chave.split('.')
            if len(partes) != 3:
                raise ValueError()
            payload = partes[1] + '=' * (-len(partes[1]) % 4)
            publica = json.loads(base64.urlsafe_b64decode(payload)).get('role') == 'anon'
        except (ValueError, TypeError, AttributeError):
            publica = False
    if not publica:
        raise ErroNuvem('Use a chave pública Publishable ou anon. Não use chaves secretas ou service_role.')
    return {'url': url, 'chave_publica': chave}


def carregar_config(pasta):
    caminho = Path(pasta) / 'nuvem.json'
    try:
        dados = json.loads(caminho.read_text(encoding='utf-8'))
        return validar_config(dados['url'], dados['chave_publica'])
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, KeyError, TypeError):
        raise ErroNuvem('Não foi possível ler a configuração da nuvem. Preencha a URL e a chave pública novamente.') from None


def salvar_config(pasta, url, chave):
    dados = validar_config(url, chave)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=pasta, prefix='.nuvem-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False)
        os.replace(temporario, pasta / 'nuvem.json')
    finally:
        Path(temporario).unlink(missing_ok=True)
    return dados


class _SemRedirecionamento(request.HTTPRedirectHandler):
    # Não encaminha senha, apikey ou token para outro endereço.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Sessao:
    usuario_id: str
    email: str
    token: str = field(repr=False)
    refresh_token: str = field(default='', repr=False)
    expira_em: float = field(default=0, repr=False)


class ClienteNuvem:
    def __init__(self, url, chave):
        config = validar_config(url, chave)
        self.url = config['url']
        self.chave = config['chave_publica']
        self._ultima_sessao = None
        self._abrir = request.build_opener(_SemRedirecionamento()).open

    def _post(self, caminho, dados, token=None):
        requisicao = request.Request(
            self.url + caminho,
            data=json.dumps(dados).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'apikey': self.chave,
                     **({'Authorization': 'Bearer ' + token} if token else {})},
            method='POST',
        )
        try:
            with self._abrir(requisicao, timeout=20) as resposta:
                return json.loads(resposta.read(1_000_001))
        except error.HTTPError as erro:
            codigo = None
            detalhe = {}
            try:
                if erro.fp is not None:
                    corpo = json.loads(erro.read(4096))
                    codigo = corpo.get('code')
                    try:
                        detalhe = json.loads(corpo.get('details') or '{}')
                    except (ValueError, TypeError):
                        pass
            except (OSError, ValueError, AttributeError):
                pass
            if codigo == 'PFS01':
                raise ConflitoSincronizacao('A sincronização encontrou uma alteração concorrente ou uma operação inválida. Nenhum lote novo foi aplicado. Clique em Sincronizar agora para conferir novamente.') from None
            if codigo == 'PFS02':
                raise LoteRecusado('A nuvem recusou a operação de sincronização. O banco local foi preservado.') from None
            if codigo == 'PFM01':
                referencia = ''
                if isinstance(detalhe, dict) and detalhe.get('tabela') in ('vendas', 'financeiro_lancamentos', 'financeiro_taxas_anuais') and re.fullmatch(r'[0-9a-f-]{1,40}', str(detalhe.get('chave', ''))):
                    referencia = f" Tabela: {detalhe['tabela']}; registro: {detalhe['chave']}."
                raise ErroNuvem('Há dados divergentes ou extras na nuvem.' + referencia + ' Nada foi substituído; migração interrompida.') from None
            if codigo == 'PFM02':
                raise ErroNuvem('A nuvem recusou o formato dos dados. Migração interrompida.') from None
            if codigo == 'PGRST202':
                script = '004_sincronizacao.sql' if caminho.endswith('/sincronizar_desktop') else '003_migracao_desktop.sql'
                raise ErroNuvem(f'Instale o SQL {script} no Supabase antes de continuar.') from None
            if codigo in ('23505', '23514', '23502', '22P02', '22007', '22008'):
                tipo = LoteRecusado if caminho.endswith('/sincronizar_desktop') else ErroNuvem
                raise tipo('A nuvem recusou um valor, uma data, uma duplicidade ou uma sobreposição de taxas. A transferência inteira foi cancelada.') from None
            if erro.code == 401 or (caminho.endswith('grant_type=refresh_token') and erro.code in (400, 403)):
                raise SessaoExpirada('Entre novamente em Conexão com a nuvem para retomar a sincronização.') from None
            if erro.code == 429 or erro.code >= 500:
                raise ErroTemporario('A nuvem está temporariamente indisponível. Os dados continuam salvos no computador.') from None
            if erro.code in (400, 401, 403):
                mensagem = 'Acesso recusado. Confira URL, chave pública, e-mail, senha e a autorização da conta.'
            else:
                mensagem = 'O serviço não concluiu a conexão. Tente novamente mais tarde.'
            raise ErroNuvem(mensagem) from None
        except (OSError, ValueError):
            raise ErroTemporario('Não foi possível conectar ao Supabase. Os dados continuam salvos neste computador.') from None

    def entrar(self, email, senha):
        email = email.strip()
        if not email or not senha:
            raise ErroNuvem('Informe seu e-mail e sua senha de acesso ao aplicativo.')
        dados = self._post('/auth/v1/token?grant_type=password', {'email': email, 'password': senha})
        try:
            token = dados['access_token']
            usuario_id = dados['user']['id']
            endereco = dados['user'].get('email') or email
            if not all(isinstance(v, str) and v for v in (token, usuario_id, endereco)):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise ErroNuvem('O serviço retornou uma sessão inválida. Tente entrar novamente.') from None
        if self._post('/rest/v1/rpc/usuario_autorizado', {}, token) is not True:
            raise ErroNuvem('Esta conta não está autorizada neste projeto. Confira o proprietário configurado no Supabase.')
        self._ultima_sessao = self._sessao(dados, usuario_id, endereco, token)
        return self._ultima_sessao

    def migrar(self, sessao, dados, aplicar=False):
        return self._post('/rest/v1/rpc/migrar_desktop', {'dados': dados, 'aplicar': aplicar}, sessao.token)

    def sincronizar(self, sessao, alteracoes=None, operacao_id=None):
        return self._post('/rest/v1/rpc/sincronizar_desktop', {
            'alteracoes': [] if alteracoes is None else alteracoes,
            'operacao_id': operacao_id,
        }, sessao.token)

    @staticmethod
    def _sessao(dados, usuario_id, email, token):
        refresh = dados.get('refresh_token', '')
        expiracao = dados.get('expires_in', 3600)
        if not isinstance(refresh, str) or type(expiracao) not in (int, float) or not 0 < expiracao <= 86400:
            raise ErroNuvem('O serviço retornou uma sessão inválida.')
        return Sessao(usuario_id, email, token, refresh, time.time() + expiracao)

    def garantir_sessao(self, sessao):
        # Preserva a rotação do refresh token mesmo quando a consulta seguinte
        # falha. Nada deste cache é persistido em disco.
        if self._ultima_sessao and self._ultima_sessao.usuario_id == sessao.usuario_id and self._ultima_sessao.expira_em > sessao.expira_em:
            sessao = self._ultima_sessao
        if not sessao.expira_em or sessao.expira_em > time.time() + 60:
            return sessao
        if not sessao.refresh_token:
            raise SessaoExpirada('Entre novamente em Conexão com a nuvem para retomar a sincronização.')
        dados = self._post('/auth/v1/token?grant_type=refresh_token', {'refresh_token': sessao.refresh_token})
        try:
            token, usuario = dados['access_token'], dados['user']
            if usuario['id'] != sessao.usuario_id or not isinstance(token, str) or not token:
                raise ValueError()
            nova = self._sessao(dados, usuario['id'], usuario.get('email') or sessao.email, token)
        except (ValueError, KeyError, TypeError):
            raise SessaoExpirada('A sessão não pôde ser renovada. Entre novamente na mesma conta.') from None
        self._ultima_sessao = nova
        # Cada RPC de sincronização verifica a autorização novamente no banco.
        return nova
