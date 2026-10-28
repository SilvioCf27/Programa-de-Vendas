"""Etapa 5: aplicativos reais, processos novos e somente bases fictícias."""
import argparse
from contextlib import closing, ExitStack
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def resumo(valores):
    s = sorted(valores)
    return dict(mediana_ms=round(statistics.median(s), 3), max_ms=round(max(s), 3),
                p95_ms=round(s[max(0, (95 * len(s) + 99) // 100 - 1)], 3), amostras=len(s))


def sem_rede(*args, **kwargs):
    raise AssertionError('Rede bloqueada na medição isolada')


def gerar(pasta, volume, referencia):
    os.environ['PROGRAMFEIRA_DATA_DIR'] = str(pasta)
    from ProgramFeira.database import banco
    from ProgramFeira import financeiro
    from ProgramFeira.preferencias import salvar_periodo_inicial, salvar_tema
    banco.criar_tabela()
    financeiro.inicializar()
    with closing(banco.conectar()) as c, c:
        c.executemany('INSERT INTO vendas(data,dinheiro,pix,cartao) VALUES(?,?,?,?)',
            [(str(referencia-timedelta(days=i)), 0 if i%9==0 else 80+i%17, 30+i%11, 40+i%23) for i in range(volume)])
        c.executemany('INSERT INTO financeiro_lancamentos(tipo,data,descricao,valor_centavos,meio,categoria) VALUES(?,?,?,?,?,?)',
            [('despesa',str(referencia-timedelta(days=i)),'Compra fictícia',1234+i%7,'Pix','Feira') for i in range(0,volume,3)])
    salvar_periodo_inicial(pasta, 'Mês atual')
    salvar_tema(pasta, 'grafite')
    return banco


def fingerprint(banco):
    with closing(banco.conectar()) as c:
        rows=c.execute('SELECT id,data,dinheiro,pix,cartao FROM vendas ORDER BY id').fetchall()
        despesas=c.execute('SELECT tipo,data,valor_centavos FROM financeiro_lancamentos ORDER BY id').fetchall()
    raw=json.dumps([rows,despesas],ensure_ascii=False).encode()
    return dict(sha_dados=hashlib.sha256(raw).hexdigest(), vendas=len(rows), despesas=len(despesas),
                total_centavos=sum(int(sum(Decimal(str(x)) for x in r[2:])*100) for r in rows))


def filho(ferramenta, volume, ciclos):
    import psutil
    processo=psutil.Process()
    with tempfile.TemporaryDirectory(prefix='feira-etapa5-') as temp, ExitStack() as stack:
        pasta=Path(temp)/'dados'
        if ferramenta=='qt':
            from reforma_desktop.ambiente import preparar
            preparar(pasta)
        referencia=date.today()
        banco=gerar(pasta,volume,referencia)
        base=fingerprint(banco)
        stack.enter_context(patch('urllib.request.OpenerDirector.open',sem_rede))
        stack.enter_context(patch('socket.create_connection',sem_rede))
        eventos=[]; contagens={}; partes={}; atrasos=[]; ultima=[None]
        def pulso():
            agora=time.perf_counter()
            if ultima[0] is not None:atrasos.append((agora-ultima[0])*1000)
            ultima[0]=agora
        def instrumentar(obj,nome,chave):
            original=getattr(obj,nome)
            def chamada(*a,**kw):
                inicio=time.perf_counter()
                contagens[chave]=contagens.get(chave,0)+1
                try:return original(*a,**kw)
                finally:partes[chave]=partes.get(chave,0)+(time.perf_counter()-inicio)*1000
            stack.enter_context(patch.object(obj,nome,chamada))
        inicio=time.perf_counter()
        if ferramenta=='tk':
            import tkinter as tk
            stack.enter_context(patch.object(tk.Tk,'mainloop'))
            from ProgramFeira import main as a
            j=a.janela;j.geometry('1536x960')
            def bombear():j.update()
            def navegar(nome):a.abas.select({'Vendas':a.aba_vendas,'Análises':a.aba_analises,'Finanças':a.painel_financeiro}[nome])
            todas=a.limpar_filtros
            def mes():a.aplicar_periodo_inicial();a.atualizar_tabela()
            atualizar=a.atualizar_tabela
            def financeiro_ano():
                a.painel_financeiro.tipo.set('Ano')
                a.painel_financeiro.referencia.set(referencia.strftime('%d/%m/%Y'))
                a.painel_financeiro.consultar()
            def sql_vendas():return a.listar_vendas()
            def linhas():return len(a.tabela.get_children())
            def confirmar(n,total):
                assert len(a.relatorio_atual['vendas'])==n
                assert int(sum(Decimal(str(x)) for r in a.relatorio_atual['vendas'] for x in r[2:])*100)==total
            def agendar_pulso():pulso();j.after(10,agendar_pulso)
            def confirmar_financas():
                from ProgramFeira import financeiro as f
                from ProgramFeira.resumos import moeda
                p=a.painel_financeiro
                esperado=f.resumo_periodo(p.inicio,p.fim)
                assert all(v.get()==moeda(esperado[k]) for k,v in p.valores.items())
                return dict(intervalo=[p.inicio,p.fim],registros=len(p.registros))
            def fechar():j.destroy()
        else:
            sys.path.insert(0,str(ROOT/'prototipos/reforma'))
            from reforma_desktop.aplicacao import preparar_interface, Janela
            from reforma_desktop.vendas import ServicoVendas
            from PySide6 import QtCore as Q
            app=preparar_interface('grafite');j=Janela(ServicoVendas(),pasta)
            j.resize(1536,960);j.show()
            def bombear():
                app.processEvents();Q.QCoreApplication.sendPostedEvents(None,Q.QEvent.Type.DeferredDelete);app.processEvents()
            navegar=j.mostrar;todas=j.limpar
            def mes():
                j.ano.setCurrentText(str(referencia.year));j.mes.setCurrentIndex(referencia.month);j.fechamento.setChecked(False);j.aplicar()
            atualizar=j.atualizar
            def financeiro_ano():
                p=j.financas
                p.seletor.tipo.setCurrentText('Ano');p.seletor.ano.setValue(referencia.year);p.consultar()
            def sql_vendas():return banco.listar_vendas()
            def linhas():return j.tabela.table.rowCount()
            def confirmar(n,total):
                assert len(j.resultado['linhas'])==n
                assert int(j.resultado['indicadores']['total']*100)==total
            timer=Q.QTimer(j);timer.setInterval(10);timer.timeout.connect(pulso)
            def agendar_pulso():pulso();timer.start()
            def confirmar_financas():
                from ProgramFeira import financeiro as f
                r=j.financas.resultado
                assert r['resumo']==f.resumo_periodo(*r['intervalo'])
                return dict(intervalo=list(r['intervalo']),registros=len(r['linhas']))
            def fechar():j._fechamento_autorizado=True;j.close();j.deleteLater();bombear()
        bombear()
        abertura=(time.perf_counter()-inicio)*1000
        rss_inicial=processo.memory_info().rss
        instrumentar(banco,'listar_vendas','leitura_vendas')
        if ferramenta=='tk':
            # main importa alias: substitui pelo mesmo wrapper, sem dupla contagem.
            stack.enter_context(patch.object(a,'listar_vendas',banco.listar_vendas))
            instrumentar(a,'ajustar_larguras_colunas','larguras')
            instrumentar(a.painel_analises,'atualizar','analises')
            instrumentar(a.painel_financeiro,'consultar','financas')
        else:
            instrumentar(j.servico,'consultar','consulta_vendas')
            instrumentar(j,'preencher_tabela','tabela')
        agendar_pulso()
        def evento(nome,acao):
            contagens.clear();partes.clear();ultima[0]=time.perf_counter()
            t=time.perf_counter();acao();bombear()
            eventos.append(dict(cenario=nome,ms=round((time.perf_counter()-t)*1000,3),
                chamadas=dict(contagens),partes_ms={k:round(v,3) for k,v in partes.items()}))
        evento('primeira_analises',lambda:navegar('Análises'))
        evento('primeira_financas',lambda:navegar('Finanças'))
        navegar('Vendas');bombear();gc.collect()
        rss_aquecido=processo.memory_info().rss
        for _ in range(ciclos):
            evento('retorno_analises',lambda:navegar('Análises'))
            evento('retorno_financas',lambda:navegar('Finanças'))
            evento('retorno_vendas',lambda:navegar('Vendas'))
        gc.collect();bombear();rss_ciclos=processo.memory_info().rss
        navegar('Finanças');bombear();evento('financas_ano',financeiro_ano)
        financeiro_verificado=confirmar_financas()
        navegar('Vendas');bombear()
        evento('aplicar_mes',mes)
        evento('todas_as_vendas',todas)
        confirmar(volume,base['total_centavos'])
        linhas_visiveis=linhas()
        evento('repetir_consulta_todas',atualizar)
        confirmar(volume,base['total_centavos'])
        # Escreve somente na fixture, para verificar invalidação (sem medir backup/cadastro).
        with closing(banco.conectar()) as c,c:c.execute('UPDATE vendas SET dinheiro=dinheiro+1 WHERE id=1')
        evento('atualizar_apos_mudanca',atualizar)
        confirmar(volume,base['total_centavos']+100)
        evento('analises_apos_mudanca',lambda:navegar('Análises'))
        evento('financas_apos_mudanca',lambda:navegar('Finanças'))
        if ferramenta=='qt':
            assert int(j.analises.snapshot['indicadores']['total']*100)==base['total_centavos']+100
            assert j.relogio.isActive() and not j.nuvem.ocupado and not j.atualizador.ocupado
            assert len(j.findChildren(Q.QTimer))==2  # um do estudo e um do medidor
        with closing(banco.conectar()) as c,c:c.execute('UPDATE vendas SET dinheiro=dinheiro-1 WHERE id=1')
        assert fingerprint(banco)==base
        sql=[]
        for _ in range(10):
            t=time.perf_counter();sql_vendas();sql.append((time.perf_counter()-t)*1000)
        gc.collect();bombear()
        rss_final=processo.memory_info().rss
        memoria=processo.memory_info()
        tela=[j.width(),j.height()] if ferramenta=='qt' else [j.winfo_width(),j.winfo_height()]
        fechar()
        return dict(ferramenta=ferramenta,referencia=str(referencia),**base,abertura_ms=round(abertura,3),
            rss_inicial_mib=round(rss_inicial/2**20,3),rss_final_mib=round(rss_final/2**20,3),
            crescimento_mib=round((rss_final-rss_inicial)/2**20,3),rss_aquecido_mib=round(rss_aquecido/2**20,3),rss_apos_ciclos_mib=round(rss_ciclos/2**20,3),crescimento_ciclos_mib=round((rss_ciclos-rss_aquecido)/2**20,3),financeiro_verificado=financeiro_verificado,
            pico_so_mib=round(memoria.peak_wset/2**20,3) if hasattr(memoria,'peak_wset') else None,
            eventos=eventos,sql_todas=resumo(sql),intervalos_pulso=resumo(atrasos) if atrasos else None,
            linhas_visiveis_todas=linhas_visiveis,tela=tela,sqlite=sqlite3.sqlite_version,
            dados_verificados=True,rede='bloqueada, sem sessão/Drive/contas configuradas')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--filho',choices=['tk','qt'])
    p.add_argument('--volume',type=int,default=224)
    p.add_argument('--volumes',type=int,nargs='+',default=[224,5000])
    p.add_argument('--repeticoes',type=int,default=3)
    p.add_argument('--ciclos',type=int,default=10)
    p.add_argument('--saida',type=Path,required=True)
    args=p.parse_args()
    if not 1<=args.repeticoes<=10 or not 1<=args.ciclos<=100 or any(not 1<=n<=10000 for n in [args.volume,*args.volumes]):p.error('Parâmetros fora dos limites de estudo')
    if args.filho:
        d=filho(args.filho,args.volume,args.ciclos)
    else:
        resultados=[]
        with tempfile.TemporaryDirectory(prefix='feira-medicoes-') as temp:
            for n in args.volumes:
                for rep in range(args.repeticoes):
                    for ferramenta in (['tk','qt'] if rep%2==0 else ['qt','tk']):
                        destino=Path(temp)/'resultado.json'
                        r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--filho',ferramenta,'--volume',str(n),'--ciclos',str(args.ciclos),'--saida',str(destino)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240,cwd=ROOT)
                        if r.returncode:raise RuntimeError(f'{ferramenta}/{n}: {r.stderr[-5000:]}')
                        item=json.loads(destino.read_text(encoding='utf-8'));item['repeticao']=rep+1;resultados.append(item)
                        print(f'{ferramenta}/{n}, repetição {rep+1}: concluído',flush=True)
                    assert resultados[-1]['sha_dados']==resultados[-2]['sha_dados']
                    assert resultados[-1]['total_centavos']==resultados[-2]['total_centavos']
        d=dict(data_utc=datetime.now(timezone.utc).isoformat(),commit_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),plataforma=platform.platform(),python=platform.python_version(),
            metodo='Aplicativos ligados ao núcleo real; processos novos alternados; mesmo gerador/SQLite; abertura após fixture e antes de imports gráficos; Mês atual, Grafite, 1536x960 solicitados. Retornos sem mudança separados da invalidação. Paginação Qt preservada, Tk tabela integral. Sem contas/rede.',
            repeticoes=args.repeticoes,ciclos=args.ciclos,resultados=resultados)
    args.saida.parent.mkdir(parents=True,exist_ok=True)
    args.saida.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
