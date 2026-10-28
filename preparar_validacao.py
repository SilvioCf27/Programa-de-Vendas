"""Prepara um perfil offline a partir de uma pasta de estudo, sem abrir a nuvem."""
import argparse
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--origem-estudo',type=Path,required=True)
    p.add_argument('--destino',type=Path,required=True,help='Pasta nova; não pode existir.')
    p.add_argument('--url-projeto-teste',required=True)
    p.add_argument('--chave-publica',required=True,help='Somente Publishable/anon; nunca senha ou service_role.')
    a=p.parse_args()
    try:
        from reforma_desktop.perfil_validacao import preparar,conferir
        perfil=preparar(a.origem_estudo,a.destino,a.url_projeto_teste,a.chave_publica)
        r=conferir(perfil)
    except Exception:
        print('Preparação não concluída. Confira a pasta marcada do estudo, o destino novo, o projeto de teste e os requisitos. A origem não foi substituída.',file=sys.stderr)
        return 1
    print('Perfil offline verificado:',perfil)
    print('Tabelas preservadas:',r['tabelas'])
    print('Nenhum registro enviado. Sessão original arquivada; automações desativadas. A entrada online ainda será validada.')
    return 0


if __name__=='__main__':raise SystemExit(main())
