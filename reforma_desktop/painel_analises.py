"""Análises Qt: identidade aprovada com snapshots/cálculos do núcleo existente."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import sqlite3

from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto, botao, caixa, titulo_secao, acesso, ajuda
from noturno_demo import LinhaResponsiva, Grafico
from tema_noturno import C
from estado_demo import MESES, Venda
from janelas_noturno import JanelaDetalhe, Coluna, janela_vendas, janela_dias, janela_pagamentos
from ProgramFeira.database import banco
from ProgramFeira.resumos import moeda
from reforma_desktop.campos_financeiros import data_iso, DataValidada
from reforma_desktop.analises import Periodo, analisar, comparar, comparar_limites, analisar_evolucao, centavos


class SeletorPeriodo(W.QWidget):
    alterado = Q.Signal()

    def __init__(self, referencia, anos, parent=None):
        super().__init__(parent)
        self.tipo = W.QComboBox()
        self.tipo.addItems(['Data', 'Mês', 'Fechamento', 'Intervalo'])
        self.tipo.setCurrentText('Mês')
        self.tipo.setAccessibleName('Comparar por')
        self.ano = W.QComboBox()
        self.ano.addItems([str(a) for a in sorted(set(anos) | {referencia.year})])
        self.ano.setCurrentText(str(referencia.year))
        self.ano.setAccessibleName('Ano do período')
        self.mes = W.QComboBox()
        self.mes.addItems(MESES)
        self.mes.setCurrentIndex(referencia.month - 1)
        self.mes.setAccessibleName('Mês do período')
        self.inicio, self.fim = DataValidada(Q.QDate(referencia)), DataValidada(Q.QDate(referencia))
        for nome, campo in [('Data inicial', self.inicio), ('Data final inclusive', self.fim)]:
            campo.setAccessibleName(nome)
            campo.setCalendarPopup(True)
            campo.setDisplayFormat('dd/MM/yyyy')
        layout = W.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(texto('Comparar por', 9, C['muted']))
        layout.addWidget(self.tipo)
        self.meses = W.QWidget()
        ml = W.QHBoxLayout(self.meses)
        ml.setContentsMargins(0, 0, 0, 0)
        for nome, campo in [('Mês', self.mes), ('Ano', self.ano)]:
            bloco = W.QVBoxLayout()
            bloco.addWidget(texto(nome, 9, C['muted']))
            bloco.addWidget(campo)
            ml.addLayout(bloco, 2 if nome == 'Mês' else 1)
        layout.addWidget(self.meses)
        self.datas = W.QWidget()
        dl = W.QGridLayout(self.datas)
        dl.setContentsMargins(0, 0, 0, 0)
        self.rotulo_inicio = texto('Data', 9, C['muted'])
        self.rotulo_fim = texto('Até (inclusive)', 9, C['muted'])
        dl.addWidget(self.rotulo_inicio, 0, 0)
        dl.addWidget(self.inicio, 1, 0)
        dl.addWidget(self.rotulo_fim, 0, 1)
        dl.addWidget(self.fim, 1, 1)
        layout.addWidget(self.datas)
        self.tipo.currentTextChanged.connect(self.ajustar)
        for campo in (self.ano, self.mes):
            campo.currentIndexChanged.connect(lambda _: self.alterado.emit())
        for campo in (self.inicio, self.fim):
            campo.dateChanged.connect(lambda _: self.alterado.emit())
        self.ajustar()

    def ajustar(self):
        tipo = self.tipo.currentText()
        datas = tipo in ('Data', 'Intervalo')
        self.meses.setVisible(not datas)
        self.datas.setVisible(datas)
        self.rotulo_inicio.setText('De' if tipo == 'Intervalo' else 'Data')
        self.rotulo_fim.setVisible(tipo == 'Intervalo')
        self.fim.setVisible(tipo == 'Intervalo')
        self.alterado.emit()

    def periodo(self):
        tipo = self.tipo.currentText()
        if tipo in ('Data', 'Intervalo'):
            inicio = date.fromisoformat(data_iso(self.inicio))
            fim = date.fromisoformat(data_iso(self.fim)) if tipo == 'Intervalo' else inicio
        else:
            inicio, fim = self.inicio.date().toPython(), self.fim.date().toPython()
        return Periodo(tipo, int(self.ano.currentText()), self.mes.currentIndex() + 1, inicio, fim)


class PainelAnalises(W.QScrollArea):
    def __init__(self, controlador):
        super().__init__()
        self.controlador = controlador
        self.snapshot = None
        self.sujo = True
        self.ultima_comparacao = None
        self.ultima_selecao = None
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Q.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.corpo = W.QWidget()
        self.layout = W.QVBoxLayout(self.corpo)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)
        self.setWidget(self.corpo)
        topo = LinhaResponsiva(900)
        self.intervalo = texto('', 10, C['muted'])
        self.intervalo.setWordWrap(True)
        topo.addWidget(self.intervalo, 1)
        topo.addWidget(botao('Alterar filtros em Vendas', lambda: controlador.mostrar('Vendas'), 'filter'))
        self.layout.addLayout(topo)
        self.aviso_vendas = texto('', 9, C['yellow'])
        self.aviso_vendas.setWordWrap(True)
        self.layout.addWidget(self.aviso_vendas)
        graficos = LinhaResponsiva(950)
        barras, bl = caixa()
        bl.addWidget(titulo_secao('Resultado por semana', 'trending-up'))
        self.barras = Grafico()
        bl.addWidget(self.barras, 1)
        bl.addWidget(ajuda('Semanas do gráfico', 'Até 12 semanas mais recentes da consulta aplicada. A tabela abaixo contém todas. Semanas nas bordas ou com filtro de dias estão recortadas; dias registrados com zero contam.'))
        graficos.addWidget(barras, 5)
        resumo, rl = caixa(10)
        rl.addWidget(titulo_secao('Resumo da seleção', 'receipt'))
        self.valores = {}
        mini = W.QGridLayout()
        for chave, nome, linha, coluna, span in [('total', 'Total do período', 0, 0, 2), ('semanas', 'Semanas', 1, 0, 1), ('dias', 'Dias de feira', 1, 1, 1), ('media', 'Média por dia', 2, 0, 2)]:
            box, vl = caixa(5)
            vl.addWidget(texto(nome, 8, C['muted']))
            self.valores[chave] = texto('', 15, bold=True)
            vl.addWidget(self.valores[chave])
            mini.addWidget(box, linha, coluna, 1, span)
        rl.addLayout(mini)
        graficos.addWidget(resumo, 2)
        pizza, pl = caixa()
        pl.addWidget(titulo_secao('Participação por pagamento', 'chart-pie'))
        self.pizza = Grafico('pizza')
        pl.addWidget(self.pizza, 1)
        graficos.addWidget(pizza, 4)
        self.layout.addLayout(graficos)
        box, tl = caixa()
        cab = W.QHBoxLayout()
        cab.addWidget(titulo_secao('Detalhamento por semana', 'calendar-days'))
        cab.addWidget(ajuda('Recorte semanal', 'Semanas de segunda a domingo. Parcial indica corte pelas datas ou pelos dias da semana escolhidos; não significa que faltou cadastrar uma venda. Sem registro é diferente de feira com valor zero.'))
        tl.addLayout(cab)
        self.tabela = W.QTableWidget(0, 8)
        self.tabela.setAccessibleName('Todas as semanas da consulta aplicada')
        self.tabela.setHorizontalHeaderLabels(['Início / fim', 'Dias', 'Total', 'Média/dia', 'Dinheiro', 'Pix', 'Cartão', 'Recorte'])
        self.tabela.verticalHeader().hide()
        self.tabela.verticalHeader().setDefaultSectionSize(29)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setShowGrid(False)
        self.tabela.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.horizontalHeader().setSectionResizeMode(W.QHeaderView.ResizeMode.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(0, W.QHeaderView.ResizeMode.ResizeToContents)
        tl.addWidget(self.tabela)
        self.layout.addWidget(box)
        baixo = LinhaResponsiva(995)
        comp, cl = caixa()
        cl.addWidget(titulo_secao('Comparar períodos (A e B)', 'arrow-right-left'))
        cl.addWidget(texto('Consulta independente dos filtros de Vendas.', 9, C['muted']))
        seletores = LinhaResponsiva(560)
        hoje = controlador.servico.hoje()
        anterior = hoje.replace(day=1) - timedelta(days=1)
        anos = set(banco.listar_anos_vendas()) | set(range(hoje.year - 5, hoje.year + 6))
        self.a, self.b = SeletorPeriodo(anterior, anos), SeletorPeriodo(hoje, anos)
        for nome, seletor, cor in [('Período A · referência', self.a, C['turquoise']), ('Período B · comparar', self.b, C['blue'])]:
            grupo, gl = caixa(10)
            grupo.setStyleSheet(f'QFrame[panel="true"]{{background:{C["side"]};border:1px solid {cor};border-radius:9px;}}')
            gl.addWidget(texto(nome, 10, cor, True))
            gl.addWidget(seletor)
            seletores.addWidget(grupo, 1)
            seletor.alterado.connect(self.marcar_pendente)
        cl.addLayout(seletores)
        cl.addWidget(botao('Comparar períodos', self.comparar, 'arrow-right-left', True))
        self.aviso = texto('Escolha A e B e clique em Comparar.', 9, C['muted'])
        self.aviso.setWordWrap(True)
        cl.addWidget(self.aviso)
        self.periodos = texto('', 9, C['muted'])
        self.periodos.setWordWrap(True)
        cl.addWidget(self.periodos)
        self.resultado = texto('A: —   |   B: —', 14, bold=True)
        self.resultado.setWordWrap(True)
        cl.addWidget(self.resultado)
        self.diferenca = texto('', 16, bold=True)
        self.diferenca.setWordWrap(True)
        cl.addWidget(self.diferenca)
        self.percentual = texto('', 9, C['muted'])
        self.percentual.setWordWrap(True)
        cl.addWidget(self.percentual)
        cl.addWidget(botao('Ver indicadores lado a lado', self.detalhes_comparacao, 'list'))
        baixo.addWidget(comp, 4)
        detalhe, dl = caixa()
        dl.addWidget(titulo_secao('Detalhes do período', 'list'))
        dl.addWidget(texto('Mesma seleção aplicada em Vendas.', 9, C['muted']))
        grid = W.QGridLayout()
        for i, (nome, sub, image, modo) in enumerate([
            ('Resultados por dia da semana', 'Totais e dias registrados de segunda a domingo.', 'calendar-days', 'dias'),
            ('Evolução mensal / fechamento', 'Até 12 períodos consecutivos, com a regra por vigência.', 'trending-up', 'evolucao'),
            ('Formas de pagamento', 'Distribuição entre dinheiro, Pix e cartão.', 'chart-pie', 'pagamentos'),
            ('Lista de vendas da seleção', 'Todos os registros da consulta aplicada.', 'list', 'vendas'),
        ]):
            acao = (lambda checked=False: self.escolher_evolucao()) if modo == 'evolucao' else (lambda checked=False, m=modo: self.abrir(self.criar_detalhe(m)))
            button = acesso(nome, sub, image, C['purple'] if modo == 'pagamentos' else C['blue'], acao)
            button.setMinimumHeight(110)
            grid.addWidget(button, i // 2, i % 2)
        dl.addLayout(grid)
        dl.addStretch()
        baixo.addWidget(detalhe, 3)
        self.layout.addLayout(baixo)

    def invalidar(self):
        self.sujo = True
        if self.controlador.area == 'Análises':
            self.atualizar()

    def atualizar(self):
        if not self.sujo:
            return
        self.snapshot = analisar(self.controlador.resultado['linhas'], self.controlador.consulta)
        s = self.snapshot
        for seletor in (self.a, self.b):
            with Q.QSignalBlocker(seletor.ano):
                for i in range(1, self.controlador.ano.count()):
                    ano = self.controlador.ano.itemText(i)
                    if seletor.ano.findText(ano) < 0:
                        seletor.ano.addItem(ano)
        self.intervalo.setText('Seleção aplicada em Vendas: ' + s['consulta'].descricao())
        indicadores = s['indicadores']
        for chave, valor in dict(total=moeda(indicadores['total']), semanas=str(len(s['semanas'])), dias=str(indicadores['quantidade']), media=moeda(indicadores['media'])).items():
            self.valores[chave].setText(valor)
        self.barras.dados = [(f"{g['inicio']:%d/%m}–{g['fim']:%d/%m}", centavos(g['total'])) for g in reversed(s['semanas'][:12])]
        self.barras.update()
        self.pizza.dados = list(zip(('Dinheiro', 'Pix', 'Cartão'), [centavos(x) for x in s['pagamentos']]))
        self.pizza.update()
        self.tabela.setRowCount(len(s['semanas']))
        self.tabela.setFixedHeight(38 + 29 * max(1, min(len(s['semanas']), 6)) + 12)
        for linha, g in enumerate(s['semanas']):
            valores = [f"{g['inicio']:%d/%m/%Y} — {g['fim']:%d/%m/%Y}", str(g['quantidade']), moeda(g['total']), moeda(g['media']),
                       *(moeda(x) for x in g['pagamentos']), 'Parcial' if g['parcial'] else 'Completa']
            for coluna, valor in enumerate(valores):
                item = W.QTableWidgetItem(valor)
                item.setToolTip(valor)
                self.tabela.setItem(linha, coluna, item)
        if not s['semanas']:
            self.tabela.setAccessibleDescription('Sem registros na consulta aplicada.')
        else:
            self.tabela.setAccessibleDescription(f"{len(s['semanas'])} semanas; inclui dias registrados com zero.")
        self.sujo = False
        if self.ultima_comparacao is not None:
            self.atualizar_comparacao_aplicada()
        self.aviso_pendente_vendas()

    def aviso_pendente_vendas(self):
        pendente = self.controlador.consulta_campos() != self.controlador.consulta
        self.aviso_vendas.setText('Há filtros pendentes em Vendas. As análises ainda mostram a consulta aplicada.' if pendente else '')
        self.aviso_vendas.setVisible(pendente)

    def marcar_pendente(self):
        self.aviso.setText('Seleção alterada — clique em Comparar. O resultado abaixo continua sendo o último aplicado.')

    def comparar(self):
        try:
            a, b = self.a.periodo(), self.b.periodo()
            resultado = comparar(a, b)
        except (ValueError, OSError, sqlite3.Error) as erro:
            self.aviso.setText('Não atualizado: ' + str(erro))
            return
        self.ultima_selecao = (a, b)
        self.exibir_comparacao(resultado)
        self.aviso.setText('Comparação aplicada. Todos os dias da semana; inclui registros zerados.')

    def atualizar_comparacao_aplicada(self):
        try:
            resultado = comparar_limites(*self.ultima_comparacao['limites'])
        except (ValueError, OSError, sqlite3.Error) as erro:
            self.aviso.setText('Comparação não atualizada: ' + str(erro))
            return
        self.exibir_comparacao(resultado)
        try:
            selecao = (self.a.periodo(), self.b.periodo())
        except ValueError:
            self.aviso.setText('Seleção incompleta — confirme as datas antes de Comparar. O resultado da consulta aplicada foi atualizado após alteração dos dados.')
            return
        if selecao != self.ultima_selecao:
            self.marcar_pendente()
        else:
            self.aviso.setText('Comparação aplicada atualizada após alteração dos dados.')

    def exibir_comparacao(self, resultado):
        self.ultima_comparacao = resultado
        self.resultado.setText(f"A: {moeda(resultado['a']['total'])}   |   B: {moeda(resultado['b']['total'])}")
        self.diferenca.setText('Diferença B − A: ' + moeda(resultado['diferenca']))
        self.diferenca.setStyleSheet(f'font-size:22px;font-weight:700;color:{C["red"] if resultado["diferenca"] < 0 else C["turquoise"]};')
        self.percentual.setText(resultado['motivo'] if resultado['variacao'] is None else ('Variação de B em relação a A: ' + f"{resultado['variacao'].quantize(Decimal('.1'), rounding=ROUND_HALF_UP):+.1f}%".replace('.', ',')))
        self.periodos.setText('  |  '.join(f"{nome}: {date.fromisoformat(a):%d/%m/%Y} a {date.fromisoformat(b):%d/%m/%Y}" for nome, (a, b) in zip(('A', 'B'), resultado['limites'])))

    def abrir(self, janela):
        janela.setAttribute(Q.Qt.WidgetAttribute.WA_DeleteOnClose)
        janela.open()
        return janela

    def detalhes_comparacao(self):
        if self.ultima_comparacao is None:
            self.aviso.setText('Clique em Comparar para consultar os indicadores lado a lado.')
            return None
        r = self.ultima_comparacao
        d = JanelaDetalhe(self, 'Comparação A e B', self.periodos.text(), 'arrow-right-left')
        linhas = [('Total registrado', moeda(r['a']['total']), moeda(r['b']['total'])),
                  ('Dias de feira (inclui zerados)', str(r['a']['quantidade']), str(r['b']['quantidade'])),
                  ('Média por dia', moeda(r['a']['media']), moeda(r['b']['media']))]
        linhas += [(nome, moeda(r['pagamentos_a'][i]), moeda(r['pagamentos_b'][i])) for i, nome in enumerate(('Dinheiro', 'Pix', 'Cartão'))]
        d.adicionar_tabela([Coluna('Indicador', ampla=True), Coluna('A'), Coluna('B')], linhas)
        d.tabela.setSortingEnabled(False)
        return self.abrir(d)

    def criar_detalhe(self, modo):
        self.atualizar()
        s = self.snapshot
        # Somente adaptação de unidades para as janelas visuais já aprovadas.
        # Os registros vêm do snapshot aplicado; não se instancia Estado da demo.
        rows = [Venda(v[0], banco.converter_data_salva(v[1]), *(centavos(x) for x in v[2:])) for v in s['linhas']]
        a, b = s['consulta'].limites()
        intervalo = (date.fromisoformat(a) if a else date.min, date.fromisoformat(b) if b else date.max)
        d = {'dias': janela_dias, 'pagamentos': janela_pagamentos, 'vendas': janela_vendas}[modo](self, rows, intervalo)
        if modo == 'dias':
            for barra, (_, grupo) in zip(d.barras, s['dias']):
                media = 'Média por dia registrado: ' + moeda(grupo['media']) if grupo['quantidade'] else 'Sem registros neste dia da semana.'
                barra.setToolTip(media)
                barra.setAccessibleDescription(media)
        return d

    def escolher_evolucao(self):
        modo, ok = W.QInputDialog.getItem(self, 'Evolução da seleção', 'Agrupar por:', ['Mês', 'Fechamento'], 0, False)
        if ok:
            return self.abrir(self.criar_evolucao(modo))

    def criar_evolucao(self, modo):
        self.atualizar()
        grupos = analisar_evolucao(self.snapshot, modo)
        d = JanelaDetalhe(self, 'Evolução por ' + modo.lower(), self.snapshot['consulta'].descricao(), 'trending-up',
                         explicacao='Até 12 períodos consecutivos, conforme o núcleo existente. Sem registros é diferente de um dia de feira registrado com zero. Fechamento usa a regra vigente em cada mês.')
        d.resumo([('Total da seleção', moeda(self.snapshot['indicadores']['total'])), ('Total exibido (até 12)', moeda(sum((g['total'] for g in grupos), Decimal(0))))])
        if grupos:
            grafico = Grafico()
            grafico.dados = [(g['rotulo'], centavos(g['total'])) for g in grupos]
            d.conteudo.addWidget(grafico)
            d.adicionar_tabela([Coluna('Período', 'mes', True), Coluna('Dias', 'inteiro'), Coluna('Vendas', 'moeda'), Coluna('Situação')],
                               [(date(int(g['rotulo'][3:]), int(g['rotulo'][:2]), 1), g['quantidade'], centavos(g['total']), 'Sem registros' if not g['quantidade'] else 'Com registros') for g in grupos])
        else:
            d.vazio('Sem registros para a evolução', 'A evolução acompanha os filtros aplicados em Vendas.')
        return d
