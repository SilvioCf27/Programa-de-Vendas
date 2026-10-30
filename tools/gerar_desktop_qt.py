"""Compila e confere a candidata Windows Qt; não publica releases."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reforma_desktop.versao import VERSAO


def gerar():
    if sys.platform != 'win32' or platform.architecture()[0] != '64bit':
        raise SystemExit('O pacote Windows Qt deve ser gerado em Windows x64.')
    saida = ROOT/'dist-qt'
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm',
        '--distpath', str(saida), '--workpath', str(ROOT/'build-qt'),
        str(ROOT/'GestaoDaFeiraQt.spec')], cwd=ROOT, check=True)
    pasta = saida/'GestaoDaFeira'
    shutil.copy2(ROOT/'reforma_desktop/ATUALIZACAO_2_0.md', pasta/'LEIA-ME.md')
    relatorio = saida/'VALIDACAO_WINDOWS.json'
    relatorio.unlink(missing_ok=True)
    subprocess.run([str(pasta/'GestaoDaFeira.exe'), '--verificar-pacote', str(relatorio)],
        cwd=saida, check=True, timeout=120)
    r = json.loads(relatorio.read_text(encoding='utf-8'))
    from ProgramFeira.atualizador import validar_relatorio, MAX_ZIP, MAX_EXTRAIDO
    validar_relatorio(relatorio, VERSAO)
    if r.get('interface') != 'PySide6' or not r.get('atualizador_real') or not r.get('sem_rede'):
        raise RuntimeError('O smoke não validou a interface e o atualizador Qt.')
    r['commit_base'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    relatorio.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
    total = sum(p.stat().st_size for p in pasta.rglob('*') if p.is_file())
    if total > MAX_EXTRAIDO:
        raise RuntimeError('O pacote ultrapassa o limite de extração da versão 1.7.1.')
    pacote = Path(shutil.make_archive(str(saida/'GestaoDaFeira-Windows-x64'), 'zip', saida, 'GestaoDaFeira'))
    if pacote.stat().st_size > MAX_ZIP:
        raise RuntimeError('O ZIP ultrapassa o limite de download da versão 1.7.1.')
    with pacote.open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    (saida/'SHA256.txt').write_text(f'{sha}  {pacote.name}\n', encoding='utf-8')
    print(f'Candidata {VERSAO} compilada e conferida. Nenhuma release publicada.')


if __name__ == '__main__':
    gerar()
