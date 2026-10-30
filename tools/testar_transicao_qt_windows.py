"""Troca 1.7.1 → Qt real e rollback após falha, com dados fictícios e sem HTTP."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ProgramFeira import atualizador as a
from ProgramFeira.recuperacao import _conteudo
from reforma_desktop.versao import VERSAO
from tools.testar_atualizacao_windows import aguardar


def matar(pid):
    subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True)


def caso(pacote_antigo, pacote_novo, falha=False, diagnostico=None):
    diagnostico = {} if diagnostico is None else diagnostico
    diagnostico.update(cenario='rollback' if falha else 'troca', etapa='extrair-referencia')
    with tempfile.TemporaryDirectory(prefix='feira transicao qt ') as temp:
        raiz = Path(temp)
        alvo = a.extrair(pacote_antigo, raiz/'instalado')
        dados = raiz/'dados'; dados.mkdir()
        # Banco/configurações são fixtures; nenhum destino externo é configurado.
        from ProgramFeira.database import banco
        from ProgramFeira import financeiro
        with patch.dict(os.environ, {'PROGRAMFEIRA_DATA_DIR': str(dados)}), \
                patch.object(banco, 'CAMINHO_BANCO', dados/'vendas.db'):
            banco.criar_tabela(); financeiro.inicializar()
            banco.cadastrar_venda('2035-01-01', 10, 20, 30)
            financeiro.salvar_lancamento('despesa', '2035-01-09', 'Parcelas fictícias', '100,01', 'Cartão de crédito', parcelas=3)
        configs = {'preferencias.json':'{"tema":"aurora"}', 'inicio.json':'{"periodo":"Todas as vendas"}',
                   'atualizacoes.json':'{"consultar":false}', 'sincronizacao.json':'{"automatica":false}',
                   'backup_drive.json':'{}'}
        for nome, corpo in configs.items(): (dados/nome).write_text(corpo, encoding='utf-8')
        # Blob opaco sem projeto configurado: não será decifrado nem renovado.
        (dados/'sessao-nuvem.dpapi').write_bytes(b'fixture-opaca-preservar-sem-configuracao')
        antes = _conteudo(dados/'vendas.db')
        arquivos_antes = {p.name:p.read_bytes() for p in dados.iterdir() if p.is_file() and p.suffix != '.db'}
        env = {**os.environ, 'PROGRAMFEIRA_DATA_DIR':str(dados), 'PYINSTALLER_RESET_ENVIRONMENT':'1'}
        inicial = alvo.parent/'.feira-atualizacao-inicial'; inicial.mkdir()
        recibo_inicial = inicial/'abriu.json'
        antigo = subprocess.Popen([str(alvo/'GestaoDaFeira.exe'), '--confirmar-atualizacao', str(recibo_inicial)], env=env)
        helper = None
        try:
            diagnostico['etapa'] = 'abrir-referencia-171'
            aguardar(recibo_inicial, antigo)
            assert json.loads(recibo_inicial.read_text())['versao'] == '1.7.1'
            release = {'versao':'v'+VERSAO, 'assets':{n:f'https://github.com/{a.REPOSITORIO}/releases/download/v{VERSAO}/{n}'
                for n in (a.PACOTE,'SHA256.txt','VALIDACAO_WINDOWS.json')}}
            def baixar_local(url, destino, limite):
                origem = pacote_novo.parent/url.rsplit('/',1)[-1]
                assert origem.stat().st_size <= limite
                shutil.copy2(origem, destino)
            with patch.object(a, 'baixar', baixar_local):
                diagnostico['etapa'] = 'conferir-candidata'
                preparado = a.preparar(release, alvo/'GestaoDaFeira.exe', dados/'vendas.db', versao_atual='1.7.1')
            hash_anterior = hashlib.sha256((alvo/'GestaoDaFeira.exe').read_bytes()).hexdigest()
            if falha:
                # A candidata real passa primeiro no smoke. A perda dos recursos
                # depois da conferência força erro de abertura e o rollback real.
                shutil.rmtree(preparado['nova']/'_internal/prototipos/reforma/recursos')
                shutil.rmtree(preparado['nova']/'_internal/recursos')
            popen = subprocess.Popen
            def abrir_helper(args, **kwargs): return popen([*args, '-SemDialogo'], **kwargs)
            with patch.dict(os.environ, env), patch.object(a.os, 'getpid', return_value=antigo.pid), \
                    patch.object(a.subprocess, 'Popen', abrir_helper):
                diagnostico['etapa'] = 'iniciar-helper'
                helper = a.instalar(preparado, dados/'vendas.db')
            assert antigo.poll() is None
            antigo.terminate(); antigo.wait(timeout=15)
            diagnostico['etapa'] = 'trocar-e-reiniciar'
            codigo = helper.wait(timeout=120)
            diagnostico['codigo_helper'] = codigo
            if codigo != (1 if falha else 0):
                log = preparado['stage']/'resultado.txt'
                if log.is_file():
                    # Só o helper estático local e caminhos fictícios do ensaio;
                    # não há configuração de conta ou credencial nesse arquivo.
                    diagnostico['helper'] = log.read_text(encoding='utf-8-sig')[:4096].replace(str(raiz), '<ensaio>')
                seguro = dados/'logs/erros.jsonl'
                if seguro.is_file():
                    diagnostico['erros_aplicacao'] = [json.loads(l) for l in seguro.read_text(encoding='utf-8').splitlines()[-5:]]
            assert codigo == (1 if falha else 0)
            if falha:
                assert hashlib.sha256((alvo/'GestaoDaFeira.exe').read_bytes()).hexdigest() == hash_anterior
                assert (preparado['stage']/'versao-recusada').is_dir()
                import psutil
                limite = time.monotonic()+15
                recuperado = False
                while time.monotonic() < limite:
                    for processo in psutil.process_iter(['pid','exe']):
                        try:
                            if processo.info['exe'] and Path(processo.info['exe']).resolve() == (alvo/'GestaoDaFeira.exe').resolve() and processo.pid != antigo.pid:
                                recuperado = True
                        except (OSError, psutil.Error):
                            pass
                    if recuperado: break
                    time.sleep(.1)
                assert recuperado, 'A versão anterior precisa reabrir após o rollback.'
            else:
                recibo = json.loads((preparado['stage']/'abriu.json').read_text())
                assert recibo['versao'] == VERSAO
                assert (Path(str(alvo)+'.anterior-'+preparado['stage'].name.removeprefix('.feira-atualizacao-'))/'GestaoDaFeira.exe').is_file()
            diagnostico['etapa'] = 'conferir-preservacao'
            assert _conteudo(dados/'vendas.db') == antes
            assert all((dados/nome).read_bytes() == corpo for nome, corpo in arquivos_antes.items())
            assert list((dados/'backups').glob('*antes-atualizacao*.db'))
            return dict(sucesso=True, origem='1.7.1', destino=VERSAO,
                recuperacao_apos_falha=falha, reinicio_confirmado=not falha,
                dados_preservados=True, preferencias_preservadas=True, sessao_opaca_preservada=True,
                binarios_reais=True, download='arquivos locais; sem consulta HTTP')
        finally:
            if antigo.poll() is None: antigo.kill(); antigo.wait(timeout=15)
            if helper and helper.poll() is None: helper.kill(); helper.wait(timeout=15)
            # Encerra somente executáveis que pertencem a esta pasta temporária,
            # inclusive a versão antiga reiniciada pelo rollback.
            import psutil
            for p in psutil.process_iter(['pid','exe']):
                try:
                    if p.info['exe'] and Path(p.info['exe']).is_relative_to(raiz):
                        matar(p.pid)
                except (OSError, psutil.Error):
                    pass
            time.sleep(.5)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pacote-171', type=Path, required=True)
    p.add_argument('--pacote-qt', type=Path, required=True)
    p.add_argument('--saida', type=Path, required=True)
    args = p.parse_args()
    if sys.platform != 'win32': raise SystemExit('Este ensaio requer Windows x64.')
    args.saida.unlink(missing_ok=True)
    with args.pacote_qt.open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    resultado = {'versao':VERSAO, 'sucesso':False, 'pacote_sha256':sha,
        'commit_base':subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()}
    try:
        resultado['troca'] = caso(args.pacote_171, args.pacote_qt, diagnostico=resultado.setdefault('diagnostico',{}))
        resultado['rollback'] = caso(args.pacote_171, args.pacote_qt, falha=True, diagnostico=resultado['diagnostico'])
        resultado.update(sucesso=True, binarios_reais=True, reinicio_confirmado=True,
            dados_preservados=True, preferencias_preservadas=True)
    except Exception as erro:
        resultado['erro_tipo'] = type(erro).__name__
        resultado['pilha'] = [dict(arquivo=Path(f.filename).name,funcao=f.name,linha=f.lineno)
            for f in traceback.extract_tb(erro.__traceback__)]
        raise
    finally:
        args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__': main()
