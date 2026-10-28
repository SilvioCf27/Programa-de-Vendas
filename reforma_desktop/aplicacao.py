"""Primeira fatia funcional Qt: Vendas sobre o núcleo existente, em banco isolado."""
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import sqlite3

from PySide6 import QtCore as Q, QtGui as G, QtWidgets as W
from noturno_demo import preparar, Fundo, Cartoes, FaixaSemana, LinhaResponsiva, Tabela, Aplicativo as Referencia
from componentes_noturno import texto, botao, caixa, ajuda, titulo_secao, icone
from tema_noturno import C, estilo
from estado_demo import MESES, DIAS, Venda  # Somente nomes; não se instancia Estado da demo.
from ProgramFeira.database import banco
from ProgramFeira.resumos import moeda
from ProgramFeira.semanas import selecao_inicial
from ProgramFeira.preferencias import carregar_periodo_inicial
from ProgramFeira.exportacao import exportar
from reforma_desktop.vendas import Consulta, ServicoVendas
from janelas_noturno import janela_vendas
from reforma_desktop.temas import FundoQt as Fundo, FaixaSemanaQt as FaixaSemana, aplicar_tokens, NOMES
from ProgramFeira.preferencias import carregar_tema
from reforma_desktop.campos_financeiros import data_iso, DataValidada
from reforma_desktop.diagnostico_qt import registrar_seguro, instalar as instalar_diagnostico


AVISO_VIRADA = 'Consulta temporariamente indisponível. Os dados exibidos não foram confirmados para o novo dia; nova tentativa no próximo minuto.'

class FormularioVenda(W.QDialog):
    def __init__(self, servico, atualizado, esperado=None, parent=None):
        super().__init__(parent)
        self.servico, self.atualizado, self.esperado = servico, atualizado, esperado
        self.setWindowTitle('Editar venda' if esperado else 'Nova venda')
        self.setMinimumWidth(440)
        layout = W.QVBoxLayout(self)
        painel, conteudo = caixa(20)
        conteudo.addWidget(texto(self.windowTitle(), 18, bold=True))
        conteudo.addWidget(texto('Valores recebidos em cada forma de pagamento.', 10, C['muted']))
        form = W.QFormLayout()
        self.data = DataValidada(Q.QDate.currentDate())
        self.data.setCalendarPopup(True)
        self.data.setDisplayFormat('dd/MM/yyyy')
        self.data.setAccessibleName('Data da venda')
        if esperado:
            self.data.setDate(Q.QDate(banco.converter_data_salva(esperado[1])))
        form.addRow('Data da venda', self.data)
        self.campos = []
        for i, nome in enumerate(('Dinheiro', 'Pix', 'Cartão'), 2):
            campo = W.QLineEdit(f'{esperado[i]:.2f}'.replace('.', ',') if esperado else '')
            campo.setPlaceholderText('0,00')
            campo.setAccessibleName(nome)
            campo.setMinimumHeight(36)
            self.campos.append(campo)
            form.addRow(nome + ' (R$)', campo)
        conteudo.addLayout(form)
        self.erro = texto('', 10, C['red'])
        self.erro.setWordWrap(True)
        self.erro.setAccessibleName('Resultado da gravação')
        conteudo.addWidget(self.erro)
        linha = W.QHBoxLayout()
        linha.addStretch()
        cancelar = botao('Cancelar', self.reject)
        cancelar.setAutoDefault(False)
        linha.addWidget(cancelar)
        self.salvar = botao('Salvar venda', self.gravar, 'check', True)
        linha.addWidget(self.salvar)
        conteudo.addLayout(linha)
        layout.addWidget(painel)
        self.salvar.setDefault(True)

    def gravar(self):
        self.salvar.setEnabled(False)
        try:
            self.servico.salvar(data_iso(self.data),
                               *(c.text() for c in self.campos), esperado=self.esperado)
        except (ValueError, OSError, sqlite3.Error) as erro:
            self.erro.setText(str(erro))
            self.salvar.setEnabled(True)
            return
        self.accept()
        self.atualizado()


class Janela(W.QWidget):
    def __init__(self, servico, pasta, *, cliente_nuvem=None, validacao_real=False):
        super().__init__()
        if validacao_real and cliente_nuvem is None:
            raise ValueError('O modo de validação exige um cliente explícito.')
        self.validacao_real = validacao_real
        self.servico, self.pasta = servico, Path(pasta)
        self.setWindowTitle('Gestão da Feira — Etapa 4 · banco de estudo')
        self.resize(1536, 1024)
        self.setMinimumSize(1000, 700)
        self.consulta = Consulta()
        self.resultado = None
        self._apresentacao = {}
        self.analises = None
        self.financas = None
        self.ordem = (1, True)
        self.area = None
        self.nav = {}
        root = W.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        side = Fundo(True)
        side.setFixedWidth(226)
        sl = W.QVBoxLayout(side)
        sl.setContentsMargins(14, 22, 14, 18)
        marca = W.QHBoxLayout()
        logo = W.QLabel()
        logo.setPixmap(G.QIcon(str(Path(__file__).resolve().parents[1] / 'prototipos/reforma/recursos/logo.svg')).pixmap(42, 42))
        marca.addWidget(logo)
        marca.addWidget(texto('Gestão da Feira', 12, bold=True))
        sl.addLayout(marca)
        sl.addWidget(texto('Suas feiras, seus resultados.', 9, C['muted']))
        sl.addSpacing(28)
        for nome, image in [('Vendas', 'chart-no-axes-combined'), ('Análises', 'trending-up'), ('Finanças', 'wallet')]:
            b = botao(nome, lambda checked=False, n=nome: self.mostrar(n), image)
            b.setProperty('nav', True)
            self.nav[nome] = b
            sl.addWidget(b)
        sl.addStretch()
        sl.addWidget(texto('VALIDAÇÃO ONLINE' if validacao_real else 'IMPLEMENTAÇÃO EM ESTUDO', 9, C['muted']))
        aviso = texto(('Banco de validação · envio manual\n' + cliente_nuvem.url) if validacao_real else 'Banco separado · serviço local simulado\nNão substitui a versão 1.7.1.', 9, C['muted'])
        aviso.setWordWrap(True)
        sl.addWidget(aviso)
        self.status_nuvem = texto('Nuvem simulada · desconectada', 9, C['muted'])
        self.status_nuvem.setWordWrap(True)
        sl.addWidget(self.status_nuvem)
        root.addWidget(side)
        main = Fundo()
        ml = W.QVBoxLayout(main)
        ml.setContentsMargins(22, 18, 22, 10)
        ml.setSpacing(14)
        header = LinhaResponsiva(1050)
        self.titulo = texto('Vendas', 24, bold=True)
        header.addWidget(self.titulo)
        header.addStretch()
        acoes = W.QHBoxLayout()
        acoes.addWidget(botao('', self.configuracoes, 'settings'))
        tema = botao('Tema: ' + NOMES[carregar_tema(pasta)], self.temas, 'moon')
        tema.setToolTip('Escolha o tema para a próxima abertura nas configurações.')
        acoes.addWidget(tema)
        self.exportar = botao('Exportar relatório', lambda: None, 'download')
        menu = W.QMenu(self.exportar)
        for formato in ('csv', 'xlsx'):
            menu.addAction('Excel' if formato == 'xlsx' else 'CSV', lambda checked=False, f=formato: self.exportar_consulta(f))
        self.exportar.setMenu(menu)
        acoes.addWidget(self.exportar)
        self.nova = botao('Nova venda', self.nova_venda, 'plus', True)
        acoes.addWidget(self.nova)
        header.addLayout(acoes)
        ml.addLayout(header)
        self.stack = W.QStackedWidget()
        ml.addWidget(self.stack, 1)
        self.scroll = W.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Q.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body = W.QWidget()
        self.vendas_layout = W.QVBoxLayout(self.body)
        self.vendas_layout.setContentsMargins(0, 0, 0, 0)
        self.vendas_layout.setSpacing(14)
        self.construir_vendas(self.vendas_layout)
        self._atalhos_tabela = []
        for tecla in (Q.Qt.Key.Key_Return, Q.Qt.Key.Key_Enter):
            atalho = G.QShortcut(G.QKeySequence(tecla), self.tabela.table)
            atalho.setContext(Q.Qt.ShortcutContext.WidgetShortcut)
            atalho.activated.connect(self.editar_linha_atual)
            self._atalhos_tabela.append(atalho)
        self.scroll.setWidget(self.body)
        self.stack.addWidget(self.scroll)
        self.paginas = {'Vendas': self.scroll}
        self.status = texto(f'Estudo local · dados: {pasta} · sincronização não conectada nesta entrada', 8, C['muted'])
        self.status.setWordWrap(True)
        ml.addWidget(self.status)
        root.addWidget(main, 1)
        self.mostrar('Vendas')
        preferencia = carregar_periodo_inicial(pasta)
        ano, mes, fechamento = selecao_inicial(preferencia, servico.hoje())
        if ano:
            self.ano.setCurrentText(str(ano))
        self.mes.setCurrentIndex(mes or 0)
        self.fechamento.setChecked(fechamento)
        self.aplicar()
        self.relogio = Q.QTimer(self)
        self.relogio.setInterval(60_000)
        self.relogio.timeout.connect(self.verificar_dia)
        self.dia_exibido = servico.hoje()
        self.relogio.start()
        from reforma_desktop.conexao_nuvem import Conexao
        # Ponto de adaptação para contratos isolados; a entrada usa a simulação.
        self.nuvem = Conexao(self, cliente=cliente_nuvem, validacao_real=validacao_real)
        from reforma_desktop.atualizacoes import Atualizacoes
        self.atualizador = Atualizacoes(self)
        if validacao_real:
            self.setWindowTitle('Gestão da Feira — validação online · ' + cliente_nuvem.url)
            self.atualizador.parar()
        self.nuvem.mudou.connect(lambda: self.status_nuvem.setText(self.nuvem.resumo))
        self.status_nuvem.setText(self.nuvem.resumo)

    def construir_vendas(self, layout):
        cards = Cartoes()
        self.cards = []
        self.notas = []
        self.barras = []
        for nome, image, cor in [('TOTAL DO PERÍODO', 'trending-up', C['turquoise']), ('DIAS DE FEIRA', 'calendar-days', C['blue']), ('MÉDIA POR DIA', 'banknote', C['turquoise']), ('DINHEIRO', 'banknote', C['yellow']), ('PIX', 'gem', C['purple']), ('CARTÃO', 'credit-card', C['blue'])]:
            # Mesmo componente dos blocos já aprovados, sem instanciar a demo.
            w, valor = Referencia.cartao(self, nome, '', image, cor, chave='Indicador')
            cards.adicionar(w)
            self.cards.append(valor)
            if len(self.cards) > 1:
                valor.setStyleSheet(f'font-size:22pt;font-weight:600;color:{C["text"]};background:transparent;border:0;')
            nota = texto('', 9, C['muted'])
            w.layout().addWidget(nota)
            self.notas.append(nota)
            barra = W.QProgressBar()
            barra.setRange(0, 1000)
            barra.setTextVisible(False)
            barra.setFixedHeight(5)
            barra.setStyleSheet(estilo(f'QProgressBar{{background:@progress_track@;border:0;border-radius:2px;}}QProgressBar::chunk{{background:{cor};border-radius:2px;}}'))
            barra.setVisible(len(self.cards) > 3)
            w.layout().addWidget(barra)
            self.barras.append(barra)
        layout.addWidget(cards)
        semana = FaixaSemana()
        sl = W.QHBoxLayout(semana)
        sl.setContentsMargins(18, 12, 18, 12)
        bloco = W.QVBoxLayout()
        bloco.addWidget(texto('Semana atual', 15, C['turquoise'], True))
        self.semana_periodo = texto('', 10, C['muted'])
        bloco.addWidget(self.semana_periodo)
        self.semana_valor = texto('', 24, bold=True)
        bloco.addWidget(self.semana_valor)
        sl.addLayout(bloco, 1)
        self.semana_formas = texto('', 11, C['muted'])
        sl.addWidget(self.semana_formas)
        sl.addWidget(botao('Ver detalhes da semana', self.detalhes_semana, 'arrow-up-right'))
        sl.addWidget(ajuda('Semana atual', 'De segunda-feira até hoje; independente dos filtros, sem vendas futuras. Dias registrados com zero também contam.'))
        layout.addWidget(semana)
        self.comparacao = texto('', 10, C['muted'])
        self.comparacao.setWordWrap(True)
        layout.addWidget(self.comparacao)
        baixo = LinhaResponsiva(1050)
        baixo.setSpacing(16)
        historico, hl = caixa(16)
        hl.addWidget(titulo_secao('Histórico de vendas', 'list'))
        self.busca = W.QLineEdit()
        self.busca.setMinimumHeight(36)
        self.busca.setPlaceholderText('Buscar na tabela por data, dia ou valor…')
        self.busca.setAccessibleName('Buscar na tabela; não altera o resumo nem a exportação')
        self.busca.setToolTip('A busca reduz apenas a tabela. Resumo e exportação usam todos os registros dos filtros aplicados.')
        self.busca.textChanged.connect(self.preencher_tabela)
        hl.addWidget(self.busca)
        self.tabela = Tabela(['ID', 'Data', 'Dia da semana', 'Dinheiro', 'Pix', 'Cartão', 'Total'], 2)
        self.tabela.editar.connect(self.editar)
        self.tabela.excluir.connect(self.excluir)
        self.tabela.table.horizontalHeader().sectionClicked.connect(self.ordenar)
        hl.addWidget(self.tabela, 1)
        baixo.addWidget(historico, 1)
        filtro, fl = caixa(16)
        filtro.setFixedWidth(270)
        fl.addWidget(titulo_secao('Filtrar vendas', 'filter'))
        self.ano = W.QComboBox()
        self.ano.addItem('Todos os anos')
        self.ano.addItems([str(y) for y in sorted(set(banco.listar_anos_vendas()) | set(range(self.servico.hoje().year - 5, self.servico.hoje().year + 6)))])
        self.mes = W.QComboBox()
        self.mes.addItems(['Todos os meses', *MESES])
        for nome, campo in [('Ano', self.ano), ('Mês', self.mes)]:
            fl.addWidget(texto(nome, 10, C['muted']))
            campo.setAccessibleName(nome)
            fl.addWidget(campo)
        self.fechamento = W.QCheckBox('Período de fechamento')
        self.fechamento.setToolTip('Usa a regra por vigência do núcleo atual. Outubro: 10/10 a 09/11 na regra inicial.')
        fl.addWidget(self.fechamento)
        fl.addWidget(texto('Dias da semana', 10, C['muted']))
        grid = W.QGridLayout()
        self.dias = []
        for i, nome in enumerate(DIAS):
            campo = W.QCheckBox(nome.replace('-feira', ''))
            campo.setAccessibleName(nome)
            self.dias.append(campo)
            grid.addWidget(campo, i // 2, i % 2)
            campo.toggled.connect(self.pendente)
        fl.addLayout(grid)
        fl.addWidget(ajuda('Dias', 'Sem marcação: todos os dias. Uma ou mais marcações limitam a consulta aos dias escolhidos.'))
        self.aviso = texto('', 9, C['yellow'])
        self.aviso.setWordWrap(True)
        fl.addWidget(self.aviso)
        fl.addWidget(botao('Aplicar filtros', self.aplicar, 'filter', True))
        fl.addWidget(botao('Limpar filtros', self.limpar, 'rotate-ccw'))
        self.aplicado = texto('', 9, C['muted'])
        self.aplicado.setWordWrap(True)
        fl.addWidget(self.aplicado)
        fl.addStretch()
        baixo.addWidget(filtro)
        layout.addLayout(baixo, 1)
        self.ano.currentIndexChanged.connect(lambda: self.sincronizar('ano'))
        self.mes.currentIndexChanged.connect(lambda: self.sincronizar('mes'))
        self.fechamento.toggled.connect(lambda: self.sincronizar('fechamento'))

    def mostrar(self, nome):
        if nome == 'Finanças' and self.financas is None:
            from reforma_desktop.painel_financas import PainelFinancas
            self.financas = PainelFinancas(self)
            self.paginas[nome] = self.financas
            self.stack.addWidget(self.financas)
        if nome == 'Análises' and self.analises is None:
            from reforma_desktop.painel_analises import PainelAnalises
            self.analises = PainelAnalises(self)
            self.paginas[nome] = self.analises
            self.stack.addWidget(self.analises)
        self.area = nome
        self.stack.setCurrentWidget(self.paginas[nome])
        self.titulo.setText(nome)
        if nome == 'Análises':
            self.analises.atualizar()
        if nome == 'Finanças':
            self.financas.atualizar()
        self.nova.setVisible(nome in ('Vendas', 'Finanças'))
        self.nova.setText('Nova despesa' if nome == 'Finanças' else 'Nova venda')
        self.exportar.setVisible(nome in ('Vendas', 'Finanças'))
        self.exportar.setText('Exportar vendas' if nome == 'Finanças' else 'Exportar relatório')
        self.exportar.setToolTip('Exporta a consulta aplicada em Vendas; não exporta lançamentos financeiros.')
        for n, b in self.nav.items():
            b.setProperty('active', n == nome)
            b.style().unpolish(b)
            b.style().polish(b)

    def sincronizar(self, origem):
        campos = (self.ano, self.mes, self.fechamento)
        bloqueios = [Q.QSignalBlocker(w) for w in campos]
        if origem == 'ano' and self.ano.currentIndex() == 0:
            self.mes.setCurrentIndex(0)
            self.fechamento.setChecked(False)
        if origem == 'mes' and self.mes.currentIndex() == 0:
            self.fechamento.setChecked(False)
        if self.fechamento.isChecked() and self.mes.currentIndex() == 0:
            self.mes.setCurrentIndex(self.servico.hoje().month)
        if self.mes.currentIndex() and self.ano.currentIndex() == 0:
            self.ano.setCurrentText(str(self.servico.hoje().year))
        del bloqueios
        self.pendente()

    def consulta_campos(self):
        return Consulta(int(self.ano.currentText()) if self.ano.currentIndex() else None,
                        self.mes.currentIndex() or None, self.fechamento.isChecked(),
                        tuple(i for i, campo in enumerate(self.dias) if campo.isChecked()))

    def pendente(self):
        self.aviso.setText('Filtros alterados — clique em Aplicar.' if self.consulta_campos() != self.consulta else '')
        if self.analises is not None:
            self.analises.aviso_pendente_vendas()

    def aplicar(self):
        try:
            consulta = self.consulta_campos()
            resultado = self.servico.consultar(consulta)
        except (ValueError, OSError, sqlite3.Error) as erro:
            W.QMessageBox.warning(self, 'Consulta não aplicada', str(erro))
            return
        self.consulta, self.resultado = consulta, resultado
        self.exibir_resultado()
        self.pendente()

    def atualizar(self):
        # Uma gravação não aplica sem querer os seletores ainda pendentes.
        self.resultado = self.servico.consultar(self.consulta)
        anos = banco.listar_anos_vendas()
        for ano in anos:
            if self.ano.findText(str(ano)) < 0:
                with Q.QSignalBlocker(self.ano):
                    self.ano.addItem(str(ano))
        self.exibir_resultado()
        self.pendente()
        self.nuvem.notificar_alteracao()

    def exibir_resultado(self):
        r = self.resultado
        valores = [r['indicadores']['total'], r['indicadores']['quantidade'], r['indicadores']['media']]
        valores += [sum((Decimal(str(v[i])) for v in r['linhas']), Decimal(0)) for i in (2, 3, 4)]
        for i, (campo, valor) in enumerate(zip(self.cards, valores)):
            campo.setText(str(valor) if i == 1 else moeda(valor))
        total = r['indicadores']['total']
        notas = [f"{r['indicadores']['quantidade']} dias de feira", f"Média: {moeda(r['indicadores']['media'])}", 'Inclui dias zerados']
        notas += [f'{p:.1f}% do período'.replace('.', ',') if total else 'Sem participação' for p in r['indicadores']['participacoes']]
        for nota, valor in zip(self.notas, notas):
            nota.setText(valor)
        for i, percentual in enumerate(r['indicadores']['participacoes'], 3):
            self.barras[i].setValue(round(percentual * 10))
        semana = r['semana']
        self.semana_periodo.setText(f"{semana['inicio']:%d/%m} a {semana['ate']:%d/%m/%Y} · {semana['quantidade']} dias de feira")
        self.semana_valor.setText(moeda(semana['total']))
        self.semana_formas.setText('\n'.join(f'{nome}: {moeda(valor)}' for nome, valor in zip(('Dinheiro', 'Pix', 'Cartão'), semana['totais'])))
        self.comparacao.setText(r['comparacao'])
        self.aplicado.setText('Consulta aplicada\n' + self.consulta.descricao())
        self.preencher_tabela()
        if self.analises is not None:
            self.analises.invalidar()
        if self.financas is not None:
            self.financas.invalidar()

    def preencher_tabela(self):
        if self.resultado is None:
            return
        # Cache limitado ao snapshot atual, pela tupla COMPLETA, nunca só pelo ID.
        # Reconsulta continua acontecendo em Aplicar/atualizar; busca/ordenação
        # reaproveitam apenas datas e textos já formatados. Excluídos/fora do
        # recorte deixam de ser retidos e valores alterados geram outra entrada.
        anteriores = self._apresentacao
        apresentacao = {}
        for v in self.resultado['linhas']:
            if v in anteriores:
                apresentacao[v] = anteriores[v]
            else:
                dia = banco.converter_data_salva(v[1])
                valores = tuple(Decimal(str(x)) for x in v[2:])
                total = sum(valores)
                campos = [str(v[0]), dia.strftime('%d/%m/%Y') if dia else v[1], DIAS[dia.weekday()] if dia else 'Data não reconhecida',
                          *(moeda(x) for x in valores), moeda(total)]
                apresentacao[v] = (dia, valores, total, campos, ' '.join(campos).casefold())
        self._apresentacao = apresentacao
        coluna, reverso = self.ordem
        def chave(v):
            dia, valores, total, _, _ = apresentacao[v]
            if coluna == 1:
                return dia or date.min
            if coluna == 2:
                return dia.weekday() if dia else -1
            if coluna == 6:
                return total
            return v[0] if coluna == 0 else valores[coluna - 3]
        busca = self.busca.text().casefold()
        linhas = [(v[0], apresentacao[v][3])
                  for v in sorted(self.resultado['linhas'], key=chave, reverse=reverso)
                  if busca in apresentacao[v][4]]
        self.tabela.preencher(linhas)

    def ordenar(self, secao):
        if not 1 <= secao <= 7:
            return
        coluna = secao - 1
        self.ordem = (coluna, not self.ordem[1] if coluna == self.ordem[0] else False)
        self.tabela.table.horizontalHeader().setSortIndicator(secao, Q.Qt.SortOrder.DescendingOrder if self.ordem[1] else Q.Qt.SortOrder.AscendingOrder)
        self.tabela.table.horizontalHeader().setSortIndicatorShown(True)
        self.preencher_tabela()

    def limpar(self):
        self.ano.setCurrentIndex(0)
        self.mes.setCurrentIndex(0)
        self.fechamento.setChecked(False)
        for campo in self.dias:
            campo.setChecked(False)
        self.aplicar()

    def nova_venda(self):
        if self.area == 'Finanças':
            return self.financas.abrir_despesa()
        return self.abrir_formulario()

    def editar_linha_atual(self):
        linha = self.tabela.table.currentRow()
        if 0 <= linha < len(self.tabela.visiveis):
            self.tabela.editar.emit(self.tabela.visiveis[linha][0])

    def editar(self, identificador):
        esperado = next((r for r in self.resultado['linhas'] if r[0] == identificador), None)
        if esperado:
            self.abrir_formulario(esperado)

    def abrir_formulario(self, esperado=None):
        form = FormularioVenda(self.servico, self.atualizar, esperado, self)
        form.setAttribute(Q.Qt.WidgetAttribute.WA_DeleteOnClose)
        form.open()
        return form

    def excluir(self, ids):
        esperados = [r for r in self.resultado['linhas'] if r[0] in ids]
        if not esperados:
            return
        resposta = W.QMessageBox.question(self, 'Excluir vendas do estudo', f'Excluir {len(esperados)} venda(s) selecionada(s)?\nUm backup verificado será criado antes da exclusão.', W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No)
        if resposta != W.QMessageBox.StandardButton.Yes:
            return
        try:
            self.servico.excluir(esperados)
            self.atualizar()
        except (ValueError, OSError, sqlite3.Error) as erro:
            W.QMessageBox.warning(self, 'Exclusão não concluída', str(erro))

    def exportar_consulta(self, formato):
        caminho, _ = W.QFileDialog.getSaveFileName(self, 'Exportar consulta aplicada', f'vendas-estudo.{formato}', f'{formato.upper()} (*.{formato})')
        if not caminho:
            return
        if not Path(caminho).suffix:
            caminho += '.' + formato
        try:
            exportar(caminho, self.resultado['relatorio'], formato)
        except (ValueError, OSError, RuntimeError) as erro:
            W.QMessageBox.warning(self, 'Exportação não realizada', str(erro))
            return
        self.status.setText(f'Exportados {len(self.resultado["linhas"])} registros da consulta aplicada: {caminho}')

    def detalhes_semana(self):
        semana = self.resultado['semana']
        rows = banco.listar_vendas(semana['inicio'].isoformat(), semana['ate'].isoformat())
        registros = [Venda(v[0], banco.converter_data_salva(v[1]), *(int(Decimal(str(x)) * 100) for x in v[2:])) for v in rows]
        janela = janela_vendas(self, registros, (semana['inicio'], semana['ate']), 'Semana atual — independente dos filtros', True)
        janela.setAttribute(Q.Qt.WidgetAttribute.WA_DeleteOnClose)
        janela.open()
        return janela

    def verificar_dia(self):
        hoje = self.servico.hoje()
        if hoje != self.dia_exibido:
            try:
                self.atualizar()
            except (OSError, sqlite3.Error) as erro:
                registrar_seguro(erro, self.pasta)
                self.status.setText(AVISO_VIRADA)
                return
            self.dia_exibido = hoje
            if self.status.text() == AVISO_VIRADA:
                self.status.setText(f'Consulta atualizada para {hoje:%d/%m/%Y}. Filtros aplicados preservados.')

    def closeEvent(self, evento):
        configuracao_ocupada = any(getattr(d, 'operacao', None) is not None for d in self.findChildren(W.QDialog))
        trabalhador_ativo = any(t.isRunning() for t in self.findChildren(Q.QThread))
        if self.nuvem.ocupado or self.atualizador.ocupado or configuracao_ocupada or trabalhador_ativo:
            evento.ignore()
            return
        from reforma_desktop.operacoes_backup import fechar_com_backup
        fechar_com_backup(self, evento)
        if evento.isAccepted():
            self.nuvem.agendador.parar()
            self.atualizador.parar()
            self.atualizador.servico.limpar()

    def configuracoes(self):
        from reforma_desktop.configuracoes import Configuracoes
        janela = Configuracoes(self)
        janela.setAttribute(Q.Qt.WidgetAttribute.WA_DeleteOnClose)
        janela.open()
        return janela

    def conexao_nuvem(self):
        if getattr(self, '_painel_nuvem', None) is not None:
            self._painel_nuvem.raise_()
            return self._painel_nuvem
        from reforma_desktop.painel_nuvem import PainelNuvem
        janela = PainelNuvem(self)
        janela.setAttribute(Q.Qt.WidgetAttribute.WA_DeleteOnClose)
        self._painel_nuvem = janela
        janela.destroyed.connect(lambda: setattr(self, '_painel_nuvem', None))
        janela.open()
        return janela

    def configurar_fechamento(self):
        from reforma_desktop.configuracao_fechamento import ConfiguracaoFechamento
        janela = ConfiguracaoFechamento(self)
        janela.setAttribute(Q.Qt.WidgetAttribute.WA_DeleteOnClose)
        janela.open()
        return janela

    def atualizacoes(self):
        if self.validacao_real:
            W.QMessageBox.information(self, 'Validação online', 'O pacote e o atualizador real ainda serão validados. Nenhum ensaio fictício será aberto nesta entrada.')
            return
        from reforma_desktop.painel_atualizacao import PainelAtualizacao
        janela = PainelAtualizacao(self)
        janela.setAttribute(Q.Qt.WidgetAttribute.WA_DeleteOnClose)
        janela.setWindowModality(Q.Qt.WindowModality.ApplicationModal)
        janela.show()
        return janela

    def temas(self):
        return self.configuracoes()


def preparar_interface(tema='escuro'):
    aplicar_tokens(tema)
    Q.QLocale.setDefault(Q.QLocale('pt_BR'))
    app = preparar()
    paleta = app.palette()
    for papel, cor in [(G.QPalette.ColorRole.Window, C['bg']), (G.QPalette.ColorRole.WindowText, C['text']), (G.QPalette.ColorRole.Base, C['field']), (G.QPalette.ColorRole.AlternateBase, C['alternate']), (G.QPalette.ColorRole.Text, C['text']), (G.QPalette.ColorRole.Button, C['field']), (G.QPalette.ColorRole.ButtonText, C['text']), (G.QPalette.ColorRole.Highlight, C['selected']), (G.QPalette.ColorRole.HighlightedText, C['text']), (G.QPalette.ColorRole.ToolTipBase, C['field']), (G.QPalette.ColorRole.ToolTipText, C['text'])]:
        paleta.setColor(papel, G.QColor(cor))
    paleta.setColor(G.QPalette.ColorGroup.Disabled, G.QPalette.ColorRole.Text, G.QColor(C['discrete']))
    app.setPalette(paleta)
    app.setStyleSheet(app.styleSheet() + estilo('QLineEdit, QDateEdit, QSpinBox {background:@field@;color:@text@;border:1px solid @border@;border-radius:6px;padding:7px;} QLineEdit:focus, QDateEdit:focus {border:2px solid @turquoise@;} QMenu {background:@field@;color:@text@;border:1px solid @border@;} QMenu::item:selected {background:@selected@;} QCalendarWidget QAbstractItemView {selection-color:@text@;selection-background-color:@selected@;} QCalendarWidget QAbstractItemView::item:selected {color:@text@;background:@selected@;}'))
    return app


def iniciar(pasta, exemplo=False, captura=None, pagina='Vendas', *, cliente_nuvem=None, validacao_real=False):
    app = preparar_interface(carregar_tema(pasta))
    servico = ServicoVendas()
    if exemplo and not banco.listar_vendas():
        hoje = servico.hoje()
        for dias, valores in [(40, ('100', '25', '30')), (9, ('80', '40', '50')), (2, ('120', '35,50', '90')), (1, ('0', '0', '0')), (0, ('75', '45', '100'))]:
            servico.salvar((hoje - timedelta(days=dias)).isoformat(), *valores)
        from ProgramFeira import financeiro
        financeiro.inicializar()
        if not financeiro.listar_lancamentos('0001-01-01', '9999-12-31') and not financeiro.listar_taxas_anuais():
            financeiro.salvar_lancamento('despesa', (hoje - timedelta(days=2)).isoformat(), 'Reposição fictícia', '75,50', 'Dinheiro', 'Feira')
            compra = hoje.replace(day=9).isoformat()
            financeiro.salvar_lancamento('despesa', compra, 'Compra parcelada fictícia', '180,00', 'Cartão de crédito', 'Outros', 3, data_compra=compra)
            financeiro.salvar_lancamento('taxa', (hoje - timedelta(days=2)).isoformat(), 'Taxa fictícia das vendas', '2,30', 'Outro', 'Feira')
    janela = Janela(servico, pasta, cliente_nuvem=cliente_nuvem, validacao_real=validacao_real)
    if captura:
        janela.nuvem.agendador.parar()
        janela.atualizador.parar()
    janela.mostrar(pagina)
    janela.show()
    if validacao_real and not captura:
        Q.QTimer.singleShot(0, janela.conexao_nuvem)
    if captura:
        for _ in range(6):
            app.processEvents()
        if not janela.grab().save(str(captura)):
            raise OSError('Não foi possível salvar a captura no caminho informado.')
        # Captura não entra no loop nem deve iniciar uma cópia assíncrona.
        janela._fechamento_autorizado = True
        janela.close()
        return 0
    restaurar_diagnostico = instalar_diagnostico(pasta, lambda mensagem: W.QMessageBox.warning(janela, 'Operação não concluída', mensagem))
    try:
        return app.exec()
    finally:
        restaurar_diagnostico()
