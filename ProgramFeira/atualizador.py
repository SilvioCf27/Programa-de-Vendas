"""Atualizações portáteis: somente releases estáveis do repositório oficial."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import zipfile

from ProgramFeira.database.seguranca_arquivos import sem_redirecionamentos
from ProgramFeira.versao import VERSAO

REPOSITORIO = 'SilvioCf27/Programa-de-Vendas'
API = f'https://api.github.com/repos/{REPOSITORIO}/releases/latest'
PACOTE = 'GestaoDaFeira-Windows-x64.zip'
MAX_ZIP = 250 * 1024 * 1024
MAX_EXTRAIDO = 600 * 1024 * 1024
HOSTS = {'api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


def numero(versao):
    if not isinstance(versao, str) or not re.fullmatch(r'v?\d{1,4}\.\d{1,4}\.\d{1,4}', versao):
        raise ValueError('Versão publicada inválida.')
    return tuple(map(int, versao.removeprefix('v').split('.')))


def url_segura(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.port not in (None, 443) or p.username or p.password:
        raise ValueError('O endereço da atualização não pertence à distribuição oficial.')
    return url


class _Redirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, url_segura(newurl))


def baixar(url, destino, limite):
    """Stream limitado; sem login, token, banco ou configuração do usuário."""
    aceitar = 'application/vnd.github+json' if urlsplit(url).hostname == 'api.github.com' else 'application/octet-stream'
    req = Request(url_segura(url), headers={'User-Agent': f'GestaoDaFeira/{VERSAO}', 'Accept': aceitar})
    with build_opener(_Redirecionamento).open(req, timeout=20) as resposta, Path(destino).open('xb') as arquivo:
        url_segura(resposta.url)
        tamanho = resposta.headers.get('Content-Length')
        if tamanho and int(tamanho) > limite:
            raise ValueError('O download ultrapassa o tamanho permitido.')
        total = 0
        fim = time.monotonic() + 180
        while bloco := resposta.read(256 * 1024):
            total += len(bloco)
            if total > limite or time.monotonic() > fim:
                raise ValueError('O download ultrapassou o tamanho ou tempo permitido.')
            arquivo.write(bloco)


def consultar():
    with tempfile.TemporaryDirectory(prefix='feira-versao-') as pasta:
        arquivo = Path(pasta) / 'release.json'
        baixar(API, arquivo, 2 * 1024 * 1024)
        release = json.loads(arquivo.read_text(encoding='utf-8'))
    versao = release.get('tag_name')
    numero(versao)
    if release.get('draft') or release.get('prerelease'):
        raise ValueError('A versão ainda não é uma publicação estável.')
    if numero(versao) <= numero(VERSAO):
        return None
    esperados = {PACOTE, 'SHA256.txt', 'VALIDACAO_WINDOWS.json'}
    assets = {}
    for item in release.get('assets', []):
        nome = item.get('name')
        if nome not in esperados:
            continue
        url = item.get('browser_download_url', '')
        # O metadado da API não pode trocar o repositório ou o nome do arquivo.
        if url != f'https://github.com/{REPOSITORIO}/releases/download/{versao}/{nome}' or nome in assets:
            raise ValueError('Metadados da publicação inconsistentes.')
        assets[nome] = url
    if assets.keys() != esperados:
        raise ValueError('A publicação ainda está incompleta. Tente novamente mais tarde.')
    return {'versao': versao, 'assets': assets}


def extrair(pacote, destino):
    """Não usa extractall: recusa caminhos Windows perigosos também no Linux."""
    destino = Path(destino)
    with zipfile.ZipFile(pacote) as zipado:
        itens = zipado.infolist()
        if len(itens) > 5000 or sum(i.file_size for i in itens) > MAX_EXTRAIDO:
            raise ValueError('Pacote grande demais para atualização.')
        vistos = set()
        for item in itens:
            nome = item.filename
            partes = PurePosixPath(nome).parts
            if ('\\' in nome or not partes or partes[0] != 'GestaoDaFeira' or
                any(p in ('.', '..') or p.rstrip(' .') != p or ':' in p or
                    re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', p) for p in partes) or
                stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1):
                raise ValueError('O pacote contém um caminho ou tipo de arquivo não permitido.')
            chave = '/'.join(partes).casefold()
            if chave in vistos:
                raise ValueError('O pacote contém arquivos duplicados.')
            vistos.add(chave)
        for item in itens:
            caminho = destino.joinpath(*PurePosixPath(item.filename).parts)
            if item.is_dir():
                caminho.mkdir(parents=True, exist_ok=True)
            else:
                caminho.parent.mkdir(parents=True, exist_ok=True)
                with zipado.open(item) as src, caminho.open('xb') as dst:
                    shutil.copyfileobj(src, dst, 256 * 1024)
    pasta = destino / 'GestaoDaFeira'
    if not (pasta / 'GestaoDaFeira.exe').is_file() or not (pasta / '_internal').is_dir():
        raise ValueError('A estrutura do executável está incompleta.')
    return pasta


def validar_destino(executavel, banco):
    # Windows pode fornecer TEMP/LOCALAPPDATA no formato 8.3 (RUNNER~1).
    # Inspeciona links antes de resolver e só depois compara formas canônicas.
    executavel = sem_redirecionamentos(executavel).resolve()
    alvo = executavel.parent
    if executavel.name != 'GestaoDaFeira.exe' or not executavel.is_file() or not (alvo / '_internal').is_dir():
        raise ValueError('A atualização requer a pasta completa do executável portátil.')
    banco = Path(banco).resolve()
    if banco.is_relative_to(alvo) or alvo.is_relative_to(banco.parent):
        raise ValueError('A pasta do aplicativo precisa ficar separada da pasta de dados.')
    if (alvo / '.git').exists() or alvo == alvo.parent or str(alvo).startswith('\\\\'):
        raise ValueError('Use uma pasta local própria para o executável, fora do repositório.')
    return alvo


def preparar(release, executavel, banco):
    """Não modifica a versão em uso. Só prepara e testa a candidata isolada."""
    alvo = validar_destino(executavel, banco)
    if numero(release['versao']) <= numero(VERSAO):
        raise ValueError('A versão publicada não é mais recente que a instalada.')
    stage = Path(tempfile.mkdtemp(prefix='.feira-atualizacao-', dir=alvo.parent))
    try:
        for nome, limite in ((PACOTE, MAX_ZIP), ('SHA256.txt', 8192), ('VALIDACAO_WINDOWS.json', 65536)):
            url = release['assets'][nome]
            if url != f'https://github.com/{REPOSITORIO}/releases/download/{release["versao"]}/{nome}':
                raise ValueError('Publicação não oficial.')
            baixar(url, stage / nome, limite)
        linhas = (stage / 'SHA256.txt').read_text(encoding='utf-8').splitlines()
        esperado = next((l.split()[0] for l in linhas if len(l.split()) == 2 and l.split()[1] == PACOTE), '')
        with (stage / PACOTE).open('rb') as arquivo:
            sha = hashlib.file_digest(arquivo, 'sha256').hexdigest()
        if not re.fullmatch('[0-9a-fA-F]{64}', esperado) or sha != esperado.lower():
            raise ValueError('A integridade do download não confere. Nada foi instalado.')
        validar_relatorio(stage / 'VALIDACAO_WINDOWS.json', release['versao'])
        nova = extrair(stage / PACOTE, stage / 'nova')
        relatorio = stage / 'teste-local.json'
        subprocess.run([str(nova / 'GestaoDaFeira.exe'), '--verificar-pacote', str(relatorio)],
                       cwd=stage, check=True, timeout=120,
                       env={**os.environ, 'PYINSTALLER_RESET_ENVIRONMENT': '1'})
        validar_relatorio(relatorio, release['versao'])
        # Script estático da versão atual, nunca texto vindo do servidor.
        script = Path(__file__).parent / 'assets/aplicar_atualizacao.ps1'
        shutil.copy2(script, stage / 'aplicar.ps1')
        return {'stage': stage, 'nova': nova, 'alvo': alvo, 'versao': release['versao']}
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def validar_relatorio(arquivo, versao):
    dados = json.loads(Path(arquivo).read_text(encoding='utf-8'))
    if (numero(dados.get('versao')) != numero(versao) or dados.get('plataforma') != 'win32' or
        not all(dados.get(k) is True for k in ('sucesso', 'empacotado', 'backup_seguranca', 'banco_isolado'))):
        raise ValueError('A nova versão não passou na verificação do executável.')


def instalar(preparacao, banco):
    from ProgramFeira.database.armazenamento import criar_backup
    from ProgramFeira import backup_drive
    alvo = validar_destino(preparacao['alvo'] / 'GestaoDaFeira.exe', banco)
    stage = sem_redirecionamentos(preparacao['stage']).resolve()
    if (stage.parent != alvo.parent or not stage.name.startswith('.feira-atualizacao-') or
        preparacao['nova'] != stage / 'nova/GestaoDaFeira'):
        raise ValueError('Pasta de atualização inválida.')
    backup = criar_backup(banco, motivo='antes-atualizacao')
    config = backup_drive.carregar_config(Path(banco).parent)
    if config.get('pasta'):
        copia = backup_drive.executar(banco, config)
        if copia['avisos']:
            raise ValueError('A cópia no Drive exige atenção: ' + '; '.join(copia['avisos']))
    parametros = {'pid': os.getpid(), 'alvo': str(alvo), 'nova': str(preparacao['nova']),
                  'versao': preparacao['versao'].removeprefix('v'), 'backup': str(backup)}
    (stage / 'parametros.json').write_text(json.dumps(parametros), encoding='utf-8')
    # Caminho absoluto do PowerShell do Windows: não executa um homônimo no PATH.
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    processo = subprocess.Popen([str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                '-File', str(stage / 'aplicar.ps1'), '-Parametros', str(stage / 'parametros.json')],
                               cwd=stage, creationflags=0x08000000,
                               env={**os.environ, 'PYINSTALLER_RESET_ENVIRONMENT': '1'})
    limite = time.monotonic() + 15
    while time.monotonic() < limite:
        if processo.poll() is not None:
            raise ValueError('O Windows não iniciou o atualizador. A versão atual foi preservada.')
        if (stage / 'pronto').is_file():
            return processo
        time.sleep(0.1)
    processo.kill()
    processo.wait(timeout=5)
    raise ValueError('O atualizador não respondeu. A versão atual foi preservada.')


def confirmar_inicio():
    """Chamado no loop gráfico; recibo restrito à área de atualização."""
    if len(sys.argv) != 3 or sys.argv[1] != '--confirmar-atualizacao':
        return
    recibo = sem_redirecionamentos(sys.argv[2]).resolve()
    alvo = Path(sys.executable).resolve().parent
    if (recibo.name != 'abriu.json' or not recibo.parent.name.startswith('.feira-atualizacao-') or
        recibo.parent.parent != alvo.parent or recibo.exists()):
        raise ValueError('Caminho do recibo de atualização inválido.')
    with recibo.open('x', encoding='utf-8') as arquivo:
        json.dump({'versao': VERSAO, 'pid': os.getpid()}, arquivo)
