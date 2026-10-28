"""Ensaio local do núcleo do atualizador. Nunca baixa ou executa um programa.

As funções do núcleo são reutilizadas com dependências privadas substituídas.
Não altera os globais do módulo funcional nem depende de ler seu código-fonte.
Os relatórios e o executável desta fixture são fictícios, não uma validação
real de binário Windows. A troca/recuperação real é pendência do empacotamento.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import FunctionType, SimpleNamespace
import zipfile
from ProgramFeira import atualizador as nucleo
from ProgramFeira.database.armazenamento import copiar_verificado

CENARIOS = {
    'normal': 'Nova versão fictícia disponível',
    'atual': 'Nenhuma versão mais recente',
    'incompleta': 'Publicação fictícia incompleta',
    'hash': 'SHA-256 incorreto',
    'candidata': 'Candidata reprovada no ensaio',
    'instalador': 'Falha ao preparar a troca',
}


def com_dependencias(funcao, **dependencias):
    contexto = dict(funcao.__globals__, **dependencias)
    copia = FunctionType(funcao.__code__, contexto, funcao.__name__, funcao.__defaults__, funcao.__closure__)
    copia.__kwdefaults__ = funcao.__kwdefaults__
    return copia


class ServicoEstudo:
    def __init__(self, banco):
        self.banco = Path(banco)
        self.cenario = 'normal'
        self.temporaria = None
        self.preparacao = None
        self.banco_ensaio = None
        self.chamadas = []
        self._preparada_cenario = None

    def limpar(self):
        if self.temporaria is not None:
            self.temporaria.cleanup()
        self.temporaria = self.preparacao = self.banco_ensaio = None
        self._preparada_cenario = None

    def relatorio(self, sucesso=True):
        return dict(versao='2.0.0', plataforma='win32', sucesso=sucesso,
                    empacotado=True, backup_seguranca=True, banco_isolado=True,
                    observacao='SOMENTE FIXTURE: nenhum binário foi executado ou validado de verdade.')

    def pacote(self):
        memoria = io.BytesIO()
        with zipfile.ZipFile(memoria, 'w') as z:
            z.writestr('GestaoDaFeira/GestaoDaFeira.exe', b'FICTICIO: NAO E UM EXECUTAVEL')
            z.writestr('GestaoDaFeira/_internal/estudo.txt', 'Somente ensaio local')
        return memoria.getvalue()

    def download_local(self, url, destino, limite):
        nucleo.url_segura(url)
        versao = 'v' + nucleo.VERSAO if self.cenario == 'atual' else 'v2.0.0'
        assets = {n: f'https://github.com/{nucleo.REPOSITORIO}/releases/download/{versao}/{n}'
                  for n in (nucleo.PACOTE, 'SHA256.txt', 'VALIDACAO_WINDOWS.json')}
        if url == nucleo.API:
            itens = [{'name': n, 'browser_download_url': u} for n,u in assets.items()]
            if self.cenario == 'incompleta':
                itens.pop()
            corpo = json.dumps(dict(tag_name=versao, draft=False, prerelease=False, assets=itens)).encode()
        elif url == assets[nucleo.PACOTE]:
            corpo = self._pacote
        elif url == assets['SHA256.txt']:
            sha = '0'*64 if self.cenario == 'hash' else hashlib.sha256(self._pacote).hexdigest()
            corpo = f'{sha}  {nucleo.PACOTE}\n'.encode()
        elif url == assets['VALIDACAO_WINDOWS.json']:
            corpo = json.dumps(self.relatorio()).encode()
        else:
            raise ValueError('Endereço não disponível no ensaio. Nenhuma conexão de rede foi feita.')
        if len(corpo) > limite:
            raise ValueError('Fixture excede o limite do núcleo.')
        with Path(destino).open('xb') as f:
            f.write(corpo)

    def consultar(self):
        return com_dependencias(nucleo.consultar, baixar=self.download_local)()

    def _testar_candidata(self, comando, **opcoes):
        if len(comando) != 3 or comando[1] != '--verificar-pacote':
            raise ValueError('Comando inesperado no ensaio; nada foi executado.')
        self.chamadas.append('teste-da-candidata-simulado')
        Path(comando[2]).write_text(json.dumps(self.relatorio(self.cenario != 'candidata')), encoding='utf-8')
        return SimpleNamespace(returncode=0)

    def _preparar_troca(self, comando, **opcoes):
        self.chamadas.append('inicio-do-helper-simulado')
        if self.cenario == 'instalador':
            raise OSError('Falha fictícia ao iniciar o preparador da troca.')
        stage = Path(opcoes['cwd'])
        if '-File' not in comando or Path(comando[comando.index('-File')+1]) != stage/'aplicar.ps1':
            raise ValueError('Helper inesperado. Nenhum processo foi iniciado.')
        (stage/'pronto').write_text('somente-ensaio', encoding='utf-8')
        return SimpleNamespace(poll=lambda:None)

    def preparar(self, release):
        self.limpar()
        self.temporaria = tempfile.TemporaryDirectory(prefix='feira-atualizador-estudo-')
        raiz = Path(self.temporaria.name)
        alvo = raiz/'aplicativo-ficticio'
        (alvo/'_internal').mkdir(parents=True)
        executavel = alvo/'GestaoDaFeira.exe'
        executavel.write_bytes(b'FICTICIO: VERSAO ANTERIOR DO ENSAIO')
        self.banco_ensaio = raiz/'dados-ficticios/vendas.db'
        copiar_verificado(self.banco, self.banco_ensaio)
        # Não copia configurações Drive/sessão: o ensaio não toca suas pastas.
        self._pacote = self.pacote()
        processos = SimpleNamespace(run=self._testar_candidata)
        try:
            preparar = com_dependencias(nucleo.preparar, baixar=self.download_local, subprocess=processos)
            self.preparacao = preparar(release, executavel, self.banco_ensaio)
            self._preparada_cenario = self.cenario
            return self.preparacao
        except BaseException:
            self.limpar()
            raise

    def instalar(self):
        if self.preparacao is None or self._preparada_cenario != self.cenario:
            raise ValueError('Faça uma nova consulta e preparação do ensaio.')
        processos = SimpleNamespace(Popen=self._preparar_troca)
        ambiente = SimpleNamespace(environ={**os.environ, 'SystemRoot':os.environ.get('SystemRoot','C:/Windows')}, getpid=os.getpid)
        instalar = com_dependencias(nucleo.instalar, subprocess=processos, os=ambiente)
        instalar(self.preparacao, self.banco_ensaio)
        anteriores = list((self.banco_ensaio.parent/'backups').glob('*antes-atualizacao*.db'))
        if len(anteriores) != 1:
            raise ValueError('Não foi possível confirmar a cópia anterior do ensaio.')
        return dict(backup=str(anteriores[0]), versao=self.preparacao['versao'],
                    observacao='Ensaio concluído. Nenhum programa foi instalado ou reiniciado.')
