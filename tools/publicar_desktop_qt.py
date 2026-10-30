"""Confere evidências Windows e prepara a release Qt; publicação é explícita."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ProgramFeira.atualizador import PACOTE, REPOSITORIO, validar_relatorio
from reforma_desktop.versao import VERSAO


def conferir(pasta, commit, evidencias):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Informe o SHA completo da revisão compilada.')
    pacote = pasta/PACOTE
    with pacote.open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    if (pasta/'SHA256.txt').read_text().strip() != f'{sha}  {PACOTE}':
        raise ValueError('SHA-256 não confere.')
    validar_relatorio(pasta/'VALIDACAO_WINDOWS.json', VERSAO)
    smoke = json.loads((pasta/'VALIDACAO_WINDOWS.json').read_text(encoding='utf-8-sig'))
    transicao = json.loads((pasta/'VALIDACAO_ATUALIZADOR.json').read_text(encoding='utf-8-sig'))
    if smoke.get('interface') != 'PySide6' or smoke.get('commit_base') != commit:
        raise ValueError('O smoke não corresponde ao pacote Qt desta revisão.')
    if (transicao.get('versao') != VERSAO or transicao.get('commit_base') != commit or
            transicao.get('pacote_sha256') != sha or not all(transicao.get(k) is True for k in
            ('sucesso','binarios_reais','reinicio_confirmado','dados_preservados','preferencias_preservadas'))):
        raise ValueError('A transição Windows não aprovou este pacote/revisão.')
    for nome, rollback in [('troca',False),('rollback',True)]:
        r = transicao.get(nome, {})
        if r.get('origem') != '1.7.1' or r.get('destino') != VERSAO or r.get('sucesso') is not True or r.get('recuperacao_apos_falha') is not rollback:
            raise ValueError('Falta comprovar a troca 1.7.1 e sua recuperação.')
    for suite in ('reforma_desktop-tests','tests','prototipos-reforma'):
        r = json.loads((evidencias/(suite+'.json')).read_text(encoding='utf-8-sig'))
        if not r.get('plataforma','').startswith('Windows') or r.get('sucesso') is not True or r.get('executados',0) <= 0 or r.get('ignorados') or r.get('falhas') or r.get('erros'):
            raise ValueError('A regressão Windows não foi aprovada integralmente.')
    revisao = json.loads((evidencias/'REVISAO.json').read_text(encoding='utf-8-sig'))
    if revisao.get('casos_conformes') is not True or revisao.get('commit_base') != commit:
        raise ValueError('A revisão de conformidade não corresponde a esta versão.')
    return [pacote, pasta/'SHA256.txt', pasta/'VALIDACAO_WINDOWS.json', pasta/'VALIDACAO_ATUALIZADOR.json']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pasta', type=Path, required=True)
    p.add_argument('--evidencias', type=Path, required=True)
    p.add_argument('--commit', required=True)
    p.add_argument('--criar-rascunho', action='store_true')
    p.add_argument('--publicar', action='store_true', help='Torna a release estável visível ao atualizador 1.7.1.')
    args = p.parse_args()
    arquivos = conferir(args.pasta, args.commit, args.evidencias)
    if args.publicar and args.criar_rascunho:
        p.error('Escolha rascunho ou publicação.')
    if not args.publicar and not args.criar_rascunho:
        print('Pacote Windows e evidências conferidos. Nenhuma release alterada.')
        return
    subprocess.run(['gh','release','create','v'+VERSAO, '--repo',REPOSITORIO,
        '--target',args.commit, '--title','Gestão da Feira '+VERSAO+' — Windows',
        '--notes-file',str(ROOT/'reforma_desktop/NOTAS_2_0.md'),
        '--latest' if args.publicar else '--draft', *map(str, arquivos)], check=True)


if __name__ == '__main__': main()
