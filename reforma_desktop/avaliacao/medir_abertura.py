"""Contraprova de abertura: revisões alternadas e fases medidas separadamente."""
import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def filho():
    from reforma_desktop.desempenho.medir import gerar, sem_rede
    from reforma_desktop.ambiente import preparar
    import psutil
    with tempfile.TemporaryDirectory(prefix='feira-abertura-') as temp:
        pasta=Path(temp)/'dados';preparar(pasta);gerar(pasta,224,date.today())
        with patch('urllib.request.OpenerDirector.open',sem_rede),patch('socket.create_connection',sem_rede):
            t0=time.perf_counter();cpu0=time.process_time()
            sys.path.insert(0,str(ROOT/'prototipos/reforma'))
            from reforma_desktop.aplicacao import preparar_interface,Janela
            from reforma_desktop.vendas import ServicoVendas
            from PySide6 import QtCore as Q
            t1=time.perf_counter()
            app=preparar_interface('grafite');t2=time.perf_counter()
            j=Janela(ServicoVendas(),pasta);t3=time.perf_counter()
            j.resize(1536,960);j.show()
            app.processEvents();Q.QCoreApplication.sendPostedEvents(None,Q.QEvent.Type.DeferredDelete);app.processEvents()
            t4=time.perf_counter();cpu1=time.process_time()
            info=psutil.Process().memory_info()
            resultado=dict(total_ms=(t4-t0)*1000,cpu_ms=(cpu1-cpu0)*1000,importacao_ms=(t1-t0)*1000,
                preparar_interface_ms=(t2-t1)*1000,construcao_ms=(t3-t2)*1000,exibicao_ms=(t4-t3)*1000,
                rss_mib=info.rss/2**20,linhas=len(j.resultado['linhas']),tela=[j.width(),j.height()],qt=Q.qVersion())
            j._fechamento_autorizado=True;j.close();j.deleteLater();app.processEvents()
            return resultado


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--filho',action='store_true')
    p.add_argument('--base',type=Path)
    p.add_argument('--repeticoes',type=int,default=7)
    p.add_argument('--saida',required=True,type=Path)
    args=p.parse_args()
    if args.filho:d=filho()
    else:
        if args.base is None or not 3<=args.repeticoes<=15:p.error('Informe a referência separada e 3–15 repetições')
        resultados=[]
        with tempfile.TemporaryDirectory(prefix='feira-aberturas-') as temp:
            for rep in range(args.repeticoes):
                for nome,raiz in ([('antes',args.base),('depois',ROOT)] if rep%2==0 else [('depois',ROOT),('antes',args.base)]):
                    destino=Path(temp)/'abertura.json'
                    subprocess.run([sys.executable,str(raiz/'reforma_desktop/avaliacao/medir_abertura.py'),'--filho','--saida',str(destino)],check=True,timeout=60,cwd=raiz)
                    r=json.loads(destino.read_text(encoding='utf-8'));r.update(revisao=nome,repeticao=rep+1);resultados.append(r)
                    print(nome,rep+1,round(r['total_ms'],2),flush=True)
        d=dict(data_utc=datetime.now(timezone.utc).isoformat(),plataforma=platform.platform(),python=platform.python_version(),
            commit_antes=subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.base,text=True).strip(),
            commit_depois=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),repeticoes=args.repeticoes,
            metodo='Somente abertura Qt, 224 registros, mesmas bases/tema/janela. Processos novos; revisões alternadas a cada par, sem descartar primeiras amostras. Fases e CPU separados. Sem contas/rede. Não substitui a coleta completa.',resultados=resultados)
    args.saida.parent.mkdir(parents=True,exist_ok=True)
    args.saida.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
