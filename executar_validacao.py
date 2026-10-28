"""Abre a validação online em perfil/projeto e pasta separados; não é a versão 2.0."""
import argparse
import os
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--perfil',required=True,type=Path)
    p.add_argument('--pasta-execucao',required=True,type=Path)
    p.add_argument('--captura',type=Path,help='Renderiza sem login nem requisições.')
    a=p.parse_args()
    try:
        from reforma_desktop.execucao_validacao import preparar
        from ProgramFeira.nuvem import carregar_config,ClienteNuvem
        pasta=preparar(a.perfil,a.pasta_execucao)
        config=carregar_config(pasta)
        cliente=ClienteNuvem(config['url'],config['chave_publica'])
        os.environ['PROGRAMFEIRA_DATA_DIR']=str(pasta)
        sys.path.insert(0,str(Path(__file__).resolve().parent/'prototipos/reforma'))
        from reforma_desktop.aplicacao import iniciar
        return iniciar(pasta,captura=a.captura,cliente_nuvem=cliente,validacao_real=True)
    except Exception:
        print('Não foi possível abrir a validação. Confira o perfil verificado, a pasta de execução separada e os requisitos. Nenhum dado pessoal foi importado.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
