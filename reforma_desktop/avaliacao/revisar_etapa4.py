"""Coleta reproduções de lacunas da revisão, só em banco fictício temporário.

Por padrão, exit 0 significa coleta concluída, NÃO aprovação da Etapa 4.
Com --exigir-conformidade, retorna 1 se um caso direcionado não estiver conforme. Cada cenário
registra sua conformidade; nunca deve ser confundido com a suíte de regressão.
"""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'prototipos/reforma'))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')


def executar():
    from reforma_desktop.ambiente import preparar
    with tempfile.TemporaryDirectory(prefix='feira-revisao-etapa4-') as pasta:
        preparar(pasta)
        from reforma_desktop.aplicacao import preparar_interface, Janela, FormularioVenda
        from reforma_desktop.vendas import ServicoVendas
        from reforma_desktop.conexao_nuvem import Tarefa
        from ProgramFeira.database import banco
        from PySide6 import QtCore as Q, QtWidgets as W, QtTest
        app = preparar_interface()
        servico = ServicoVendas(lambda:date(2026,10,27))
        j = Janela(servico,pasta)
        j.show()
        casos = []
        def eventos():
            for _ in range(5):app.processEvents()
        def esperar(condicao):
            limite = time.monotonic()+10
            while condicao() and time.monotonic()<limite:
                app.processEvents();time.sleep(.005)
            if condicao():raise RuntimeError('Tempo de coleta excedido.')
        try:
            eventos()
            f = FormularioVenda(servico,lambda:None,parent=j)
            f.data.setDate(Q.QDate(2035,1,2))
            f.campos[0].setText('1,00')
            f.show();eventos()
            f.data.setFocus();f.data.setSelectedSection(W.QDateEdit.Section.YearSection)
            QtTest.QTest.keyClicks(f.data,'2')
            texto,aceitavel = f.data.lineEdit().text(),f.data.hasAcceptableInput()
            f.gravar()
            linhas = banco.listar_vendas()
            casos.append(dict(id='R01',item='V01',entrada=texto,aceitavel_antes=aceitavel,
                linhas_depois=len(linhas),data_gravada=linhas[0][1] if linhas else None,
                conforme=not linhas,esperado='Recusar a data inválida sem gravar.'))
            f.close()
            if banco.buscar_venda_por_data('2035-01-02') is None:
                servico.salvar('2035-01-02','1','0','0')

            j.mostrar('Análises')
            p = j.analises
            for seletor,dia in [(p.a,2),(p.b,3)]:
                seletor.tipo.setCurrentText('Data')
                seletor.inicio.setDate(Q.QDate(2035,1,dia))
            p.comparar()
            eventos()
            p.a.inicio.setFocus();p.a.inicio.setSelectedSection(W.QDateEdit.Section.YearSection)
            QtTest.QTest.keyClicks(p.a.inicio,'2')
            texto,aceitavel = p.a.inicio.lineEdit().text(),p.a.inicio.hasAcceptableInput()
            p.comparar()
            casos.append(dict(id='R02',item='A02',entrada=texto,aceitavel_antes=aceitavel,
                mensagem=p.aviso.text(),conforme=p.aviso.text().startswith('Não atualizado:'),
                esperado='Recusar a data inválida e manter a comparação anterior identificada.'))

            j.mostrar('Vendas');j.limpar();eventos()
            t = j.tabela.table
            j.scroll.ensureWidgetVisible(t)
            j.activateWindow();eventos()
            t.setCurrentCell(0,2);t.setFocus();eventos()
            foco = t.hasFocus()
            spy = QtTest.QSignalSpy(j.tabela.editar)
            QtTest.QTest.keyClick(t,Q.Qt.Key.Key_Return);eventos()
            enter = spy.count()
            for d in j.findChildren(W.QDialog):
                if d.isVisible():d.close()
            eventos()
            item = t.item(0,2)
            QtTest.QTest.mouseClick(t.viewport(),Q.Qt.MouseButton.LeftButton,pos=t.visualItemRect(item).center());eventos()
            QtTest.QTest.mouseDClick(t.viewport(),Q.Qt.MouseButton.LeftButton,pos=t.visualItemRect(item).center())
            eventos()
            duplo = spy.count()-enter
            casos.append(dict(id='R03',item='V03',edicoes_por_enter=enter,edicoes_por_duplo_clique=duplo,
                foco_na_tabela=foco,linhas=t.rowCount(),conforme=enter==1 and duplo==1,esperado='Enter na linha selecionada abre a edição uma única vez.'))
            for d in j.findChildren(W.QDialog):
                if d.isVisible():d.close()
            eventos()

            def contar_runtime():
                quantidade = 0
                for arquivo in (Path(pasta)/'logs').glob('*.jsonl'):
                    for linha in arquivo.read_text(encoding='utf-8').splitlines():
                        try:registro = json.loads(linha)
                        except ValueError:continue
                        if isinstance(registro,dict) and registro.get('tipo')=='RuntimeError':quantidade += 1
                return quantidade
            erros_antes = contar_runtime()
            def falhar():raise RuntimeError('falha-ficticia-sem-dados-pessoais')
            tarefa = Tarefa(falhar,j)
            sinais = QtTest.QSignalSpy(tarefa.resultado)
            tarefa.start();esperar(tarefa.isRunning);eventos()
            registros = list((Path(pasta)/'logs').glob('*'))
            mensagem_no_log = any('falha-ficticia-sem-dados-pessoais' in r.read_text(encoding='utf-8') for r in registros if r.is_file())
            casos.append(dict(id='R04',item='G02',resultado_trabalhador=bool(sinais.at(0)[0]) if sinais.count() else None,
                arquivos_de_diagnostico=len(registros),registros_runtime_error_novos=contar_runtime()-erros_antes,
                mensagem_presente_no_log=mensagem_no_log,conforme=contar_runtime()>erros_antes and not mensagem_no_log,
                esperado='Erro inesperado sanitizado gera registro técnico sem mensagem/variáveis.'))
            tarefa.deleteLater();eventos()

            j.dia_exibido = date(2026,10,26)
            propagou = False
            with patch.object(j,'atualizar',side_effect=[sqlite3.OperationalError('banco ficticio ocupado'),None]) as atualizar:
                try:j.verificar_dia()
                except sqlite3.OperationalError:propagou = True
                j.verificar_dia()
                casos.append(dict(id='R06',item='V06',erro_propagou=propagou,
                    tentativas_em_dois_disparos=atualizar.call_count,
                    conforme=atualizar.call_count==2 and not propagou,
                    esperado='Falha transitória na virada mantém nova tentativa e não confirma o dia antes de atualizar.'))

            c = j.configuracoes();eventos()
            liberar = threading.Event()
            try:
                c.executar(lambda:liberar.wait(5),lambda r:None)
                eventos()
                j.close()
                casos.append(dict(id='R05',item='G03',banco_operacao_ativa=c.operacao is not None,
                    janela_principal_visivel=j.isVisible(),janela_backup_visivel=c.isVisible(),conforme=j.isVisible(),
                    esperado='Encerramento direto da janela principal aguarda a operação de backup.'))
            finally:
                liberar.set()
                esperar(lambda:c.operacao is not None)
                c.close();eventos()
        finally:
            j.relogio.stop();j.nuvem.agendador.parar();j.atualizador.parar()
            j.close();eventos()
        casos.sort(key=lambda c:c['id'])
        return dict(plataforma=platform.platform(),python=platform.python_version(),sqlite=sqlite3.sqlite_version,
                    qt=Q.qVersion(),dados='Somente banco/pasta fictícios temporários; sem contas ou rede.',
                    casos=casos,casos_conformes=all(c['conforme'] for c in casos),aprovacao_etapa4=False,
                    observacao='Coleta direcionada de lacunas, não uma suíte geral de equivalência. A aprovação da etapa exige o inventário completo e revisão conjunta.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--saida',type=Path,required=True)
    p.add_argument('--exigir-conformidade',action='store_true',help='Retorna 1 se algum dos cenários direcionados não estiver conforme.')
    args=p.parse_args()
    resultado=executar()
    resultado['commit_base']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    args.saida.parent.mkdir(parents=True,exist_ok=True)
    args.saida.write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(resultado,ensure_ascii=False,indent=2))

    if args.exigir_conformidade and not resultado['casos_conformes']:
        raise SystemExit(1)
