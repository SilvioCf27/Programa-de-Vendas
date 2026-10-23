"""Gera e testa a distribuição portátil em Python 3.11 x64 no Windows."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def gerar():
    if sys.platform != 'win32' or platform.architecture()[0] != '64bit':
        raise SystemExit('Gere a distribuição Windows em Windows 64 bits, com Python 3.11 x64.')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', str(ROOT / 'GestaoDaFeira.spec')], cwd=ROOT, check=True)
    pasta = ROOT / 'dist/GestaoDaFeira'
    shutil.copy2(ROOT / 'docs/EXECUTAVEL.md', pasta / 'LEIA-ME.md')
    for guia in ('RECUPERACAO.md', 'USO.md', 'CELULAR.md', 'INTERFACE.md', 'FINANCAS.md'):
        shutil.copy2(ROOT / 'docs' / guia, pasta / guia)
    shutil.copy2(ROOT / 'supabase/migrations/005_fechamentos.sql', pasta / 'SQL_005_FECHAMENTOS.sql')
    shutil.copytree(ROOT / 'docs/imagens', pasta / 'imagens', dirs_exist_ok=True)
    relatorio = ROOT / 'dist/VALIDACAO_WINDOWS.json'
    # Popen é necessário: Python pode não aguardar processos GUI no Windows
    # quando iniciados pelo shell. Aqui aguardamos explicitamente o processo.
    retorno = subprocess.run([str(pasta / 'GestaoDaFeira.exe'), '--verificar-pacote', str(relatorio)], cwd=ROOT / 'dist', timeout=90)
    if retorno.returncode != 0 or not relatorio.exists():
        if relatorio.exists():
            erro = relatorio.read_text(encoding='utf-8').replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D')
            print('::error::' + erro, flush=True)
        raise SystemExit('O executável falhou na verificação. Consulte dist/VALIDACAO_WINDOWS.json.')
    resultado = json.loads(relatorio.read_text(encoding='utf-8'))
    if not resultado.get('sucesso') or not resultado.get('empacotado') or resultado.get('plataforma') != 'win32':
        raise SystemExit(f'Pacote não aprovado: {resultado}')
    zip_path = Path(shutil.make_archive(str(ROOT / 'dist/GestaoDaFeira-Windows-x64'), 'zip', ROOT / 'dist', 'GestaoDaFeira'))
    resumo = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (ROOT / 'dist/SHA256.txt').write_text(f'{resumo}  {zip_path.name}\n', encoding='utf-8')
    print(f'Pronto: {zip_path}')


if __name__ == '__main__':
    gerar()
