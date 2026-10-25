"""Ensaia a atualização com dois binários reais, sem rede ou dados pessoais."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ProgramFeira import atualizador as a
from ProgramFeira.recuperacao import _conteudo
from ProgramFeira.versao import VERSAO


def aguardar(arquivo, processo, segundos=90):
    fim = time.monotonic() + segundos
    while time.monotonic() < fim:
        if arquivo.exists():
            return
        if processo.poll() is not None:
            break
        time.sleep(.1)
    raise RuntimeError(f'O binário não confirmou a abertura: {arquivo}')


def testar(pacote):
    if sys.platform != 'win32':
        raise RuntimeError('Este ensaio requer Windows.')
    with tempfile.TemporaryDirectory(prefix='feira atualizacao ') as tmp:
        raiz = Path(tmp)
        alvo = a.extrair(pacote, raiz / 'instalado')
        dados = raiz / 'dados'
        dados.mkdir()
        with patch.dict(os.environ, {'PROGRAMFEIRA_DATA_DIR': str(dados)}):
            from ProgramFeira.database import banco as db
            from ProgramFeira import financeiro
            db.criar_tabela()
            db.cadastrar_venda('2035-01-01', 10, 20, 30)
            financeiro.salvar_lancamento('despesa', '2035-01-10', 'Despesa fictícia', '100,01', 'Cartão de crédito', parcelas=3)
            financeiro.salvar_taxa_anual(2035, '2035-01-01', '2035-12-31', '12,34')
        (dados / 'preferencias.json').write_text('{"tema":"aurora"}')
        (dados / 'atualizacoes.json').write_text('{"consultar":false}')
        stage_inicial = alvo.parent / '.feira-atualizacao-inicial'
        stage_inicial.mkdir()
        recibo_inicial = stage_inicial / 'abriu.json'
        env = {**os.environ, 'PROGRAMFEIRA_DATA_DIR': str(dados)}
        antigo = subprocess.Popen([str(alvo / 'GestaoDaFeira.exe'), '--confirmar-atualizacao', str(recibo_inicial)], env=env)
        novo_pid = None
        helper = None
        try:
            aguardar(recibo_inicial, antigo)
            banco = dados / 'vendas.db'
            antes = _conteudo(banco)
            config = {p.name: p.read_bytes() for p in dados.glob('*.json')}
            release = {'versao': 'v' + VERSAO, 'assets': {n: f'https://github.com/{a.REPOSITORIO}/releases/download/v{VERSAO}/{n}' for n in (a.PACOTE, 'SHA256.txt', 'VALIDACAO_WINDOWS.json')}}
            def baixar(url, destino, limite):
                shutil.copy2(Path(pacote).parent / url.rsplit('/', 1)[-1], destino)
            with patch.object(a, 'VERSAO', '0.0.0'), patch.object(a, 'baixar', baixar):
                preparado = a.preparar(release, alvo / 'GestaoDaFeira.exe', banco)
            popen = subprocess.Popen
            def iniciar_helper(args, **kwargs):
                return popen([*args, '-SemDialogo'], **kwargs)
            with patch.dict(os.environ, {'PROGRAMFEIRA_DATA_DIR': str(dados)}), patch.object(a.os, 'getpid', return_value=antigo.pid), patch.object(a.subprocess, 'Popen', iniciar_helper):
                helper = a.instalar(preparado, banco)
            # O helper só pode trocar os arquivos depois que a versão em uso fecha.
            assert antigo.poll() is None
            antigo.terminate()
            antigo.wait(timeout=15)
            assert helper.wait(timeout=100) == 0, (preparado['stage'] / 'resultado.txt').read_text()
            recibo = json.loads((preparado['stage'] / 'abriu.json').read_text())
            novo_pid = recibo['pid']
            assert recibo['versao'] == VERSAO
            assert _conteudo(banco) == antes
            assert {p.name: p.read_bytes() for p in dados.glob('*.json')} == config
            assert list(alvo.parent.glob('GestaoDaFeira.anterior-*'))
            assert list((dados / 'backups').glob('*antes-atualizacao*'))
            return {'sucesso': True, 'versao': VERSAO, 'binarios_reais': True,
                    'dados_preservados': True, 'preferencias_preservadas': True, 'reinicio_confirmado': True}
        finally:
            if antigo.poll() is None:
                antigo.kill(); antigo.wait(timeout=15)
            if helper and helper.poll() is None:
                helper.kill(); helper.wait(timeout=15)
            if novo_pid:
                subprocess.run(['taskkill', '/PID', str(novo_pid), '/T', '/F'], capture_output=True)
            else:
                for recibo in raiz.rglob('abriu.json'):
                    try:
                        pid = json.loads(recibo.read_text())['pid']
                        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True)
                    except (OSError, ValueError, KeyError):
                        pass
            time.sleep(.5)


if __name__ == '__main__':
    resultado = testar(ROOT / 'dist' / a.PACOTE)
    (ROOT / 'dist/VALIDACAO_ATUALIZADOR.json').write_text(json.dumps(resultado, indent=2), encoding='utf-8')
    print(json.dumps(resultado), flush=True)
