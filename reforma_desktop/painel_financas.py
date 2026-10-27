"""Tela financeira Qt sobre as regras atuais; consulta independente de Vendas."""
from datetime import date
from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto, botao, caixa, titulo_secao, ajuda, acesso, tile
from noturno_demo import LinhaResponsiva, Tabela, Aplicativo as Referencia
from tema_noturno import C
from estado_demo import Lancamento
from janelas_noturno import JanelaDetalhe, Coluna, janela_despesas
from ProgramFeira import financeiro as f, fechamento
from ProgramFeira.resumos import moeda
from ProgramFeira.semanas import selecao_inicial
from reforma_desktop.financas import ServicoFinanceiro
from reforma_desktop.campos_financeiros import SeletorFinanceiro
from reforma_desktop.formularios_financeiros import FormularioLancamento, FormularioTaxas, FormularioAnual, ERROS


def reais(centavos):
    from decimal import Decimal
    return moeda(Decimal(centavos) / 100)


def br(iso):
    return date.fromisoformat(iso).strftime('%d/%m/%Y')


class HistoricoTaxas(W.QDialog):
    def __init__(self, painel):
        super().__init__(painel)
        self.painel = painel
        self.setWindowTitle('Histórico de taxas da maquininha')
        self.resize(960, 570)
        root = W.QVBoxLayout(self)
        root.addWidget(titulo_secao('Totais históricos de taxas', 'percent'))
        nota = texto('Todos os anos, independente da consulta financeira. Totais confirmados ou estimados, sem rateio por mês/dia.', 10, C['muted'])
        nota.setWordWrap(True)
        root.addWidget(nota)
        self.tabela = W.QTableWidget(0, 6)
        self.tabela.setAccessibleName('Histórico de taxas; todos os anos')
        self.tabela.setHorizontalHeaderLabels(['Ano', 'Início', 'Fim', 'Total', 'Natureza', 'Origem / observação'])
        self.tabela.verticalHeader().hide()
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.horizontalHeader().setSectionResizeMode(W.QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(5, W.QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tabela, 1)
        botoes = W.QHBoxLayout()
        botoes.addWidget(botao('Novo total histórico', lambda: self.formulario(), 'plus', True))
        self.editar = botao('Editar ano', self.editar_atual, 'pencil')
        self.excluir = botao('Excluir ano', self.excluir_atual, 'trash-2', danger=True)
        botoes.addWidget(self.editar)
        botoes.addWidget(self.excluir)
        botoes.addStretch()
        botoes.addWidget(botao('Fechar', self.accept))
        root.addLayout(botoes)
        self.erro = texto('', 10, C['red'])
        self.erro.setWordWrap(True)
        root.addWidget(self.erro)
        self.tabela.itemSelectionChanged.connect(self.selecao)
        self.recarregar()

    def recarregar(self):
        self.registros = f.listar_taxas_anuais()
        self.tabela.setRowCount(len(self.registros))
        self.tabela.clearSelection()
        for n, r in enumerate(self.registros):
            for c, valor in enumerate([r['ano'], br(r['inicio']), br(r['fim']), reais(r['valor_centavos']), r['natureza'], r['observacao']]):
                item = W.QTableWidgetItem(str(valor))
                item.setToolTip(str(valor))
                self.tabela.setItem(n, c, item)
        self.selecao()

    def selecao(self):
        selecionada = bool(self.tabela.selectionModel().selectedRows())
        self.editar.setEnabled(selecionada)
        self.excluir.setEnabled(selecionada)

    def registro(self):
        rows = self.tabela.selectionModel().selectedRows()
        return self.registros[rows[0].row()] if rows else None

    def alterado(self):
        self.painel.ao_alterar()
        self.recarregar()

    def formulario(self, registro=None):
        return self.painel.abrir(FormularioAnual(self.painel.servico, self.alterado, self.painel.hoje(), registro, self))

    def editar_atual(self):
        r = self.registro()
        if r:
            return self.formulario(r)

    def excluir_atual(self):
        r = self.registro()
        if not r:
            return
        if W.QMessageBox.question(self, 'Excluir histórico anual', f'Excluir o total histórico de {r["ano"]}?\nUm backup será criado. As taxas por data serão preservadas.', W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No) != W.QMessageBox.StandardButton.Yes:
            return
        try:
            self.painel.servico.excluir_anual(r)
        except ERROS as erro:
            self.erro.setText(str(erro))
            return
        self.alterado()


class PainelFinancas(W.QScrollArea):
    def __init__(self, controlador):
        super().__init__()
        self.controlador = controlador
        self.hoje = controlador.servico.hoje
        self.servico = ServicoFinanceiro()
        self.sujo, self.resultado = True, None
        self.recorte = 0
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Q.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.corpo = W.QWidget()
        self.layout = W.QVBoxLayout(self.corpo)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)
        self.setWidget(self.corpo)
        ano, mes, _ = selecao_inicial('Fechamento atual', self.hoje())
        self.seletor = SeletorFinanceiro(date(ano, mes, 1))
        self.consulta = self.seletor.consulta()
        filtro, fl = caixa(12)
        linha = LinhaResponsiva(1000)
        linha.addWidget(self.seletor, 1)
        acoes = W.QHBoxLayout()
        acoes.addWidget(botao('Consultar', self.consultar, 'search', True))
        acoes.addWidget(botao('Limpar', self.limpar, 'rotate-ccw'))
        linha.addLayout(acoes)
        fl.addLayout(linha)
        self.intervalo = texto('', 9, C['muted'])
        self.intervalo.setWordWrap(True)
        self.pendente = texto('', 9, C['yellow'])
        self.pendente.setWordWrap(True)
        fl.addWidget(self.intervalo)
        fl.addWidget(self.pendente)
        self.layout.addWidget(filtro)
        self.seletor.alterado.connect(self.marcar_pendente)
        cards = LinhaResponsiva(950)
        self.cards = {}
        for chave, nome, image, cor, nota in [('saldo', 'Saldo após despesas', 'wallet', C['turquoise'], 'Vendas − taxas − despesas'), ('despesas', 'Despesas a cobrir', 'receipt', C['red'], 'Compromissos incluídos na consulta'), ('falta', 'Falta cobrir', 'banknote', C['blue'], 'Despesas ainda não cobertas')]:
            w, valor = Referencia.cartao(self, nome, '', image, cor, nota, chave)
            self.cards[chave] = valor
            cards.addWidget(w, 1)
        self.layout.addLayout(cards)
        secundario, sl = caixa(12)
        linha = LinhaResponsiva(700)
        self.secundarios = {}
        for chave, nome, image, cor in [('bruto', 'Vendas brutas', 'wallet', C['green']), ('taxas', 'Taxas cadastradas', 'percent', C['yellow']), ('liquido', 'Vendas menos taxas', 'banknote', C['blue'])]:
            item = W.QHBoxLayout()
            item.addWidget(tile(image, cor, 36))
            col = W.QVBoxLayout()
            col.addWidget(texto(nome, 9, C['muted']))
            valor = texto('', 15, bold=True)
            self.secundarios[chave] = valor
            col.addWidget(valor)
            item.addLayout(col, 1)
            linha.addLayout(item, 1)
        linha.addWidget(ajuda('Taxas e saldo', 'Saldo considera somente taxas e despesas cadastradas, inclusive futuras no período. Taxa ausente não significa isenção. Totais históricos anuais não são rateados; um recorte parcial pode ter saldo provisório. A exportação do cabeçalho continua sendo de Vendas.'))
        sl.addLayout(linha)
        self.aviso = texto('', 9, C['yellow'])
        self.aviso.setWordWrap(True)
        sl.addWidget(self.aviso)
        self.layout.addWidget(secundario)
        lista, ll = caixa()
        cabecalho = LinhaResponsiva(1000)
        cabecalho.addWidget(titulo_secao('Lançamentos do período', 'receipt'), 1)
        acoes = W.QHBoxLayout()
        acoes.addWidget(botao('Taxas da maquininha', self.abrir_taxas, 'percent'))
        acoes.addWidget(botao('Nova despesa', self.abrir_despesa, 'plus', True))
        cabecalho.addLayout(acoes)
        ll.addLayout(cabecalho)
        recortes = W.QHBoxLayout()
        self.botoes_recorte = []
        for i, nome in enumerate(['Todas', 'Despesas', 'Taxas', 'Parcelas']):
            b = botao(nome, lambda checked=False, n=i: self.aplicar_recorte(n))
            recortes.addWidget(b)
            self.botoes_recorte.append(b)
        recortes.addWidget(ajuda('Recorte da lista', 'Altera só a lista, não os totais da consulta financeira aplicada. Seleção múltipla e exclusão se limitam à página visível.'))
        recortes.addStretch()
        ll.addLayout(recortes)
        self.tabela = Tabela(['Compra', 'Fatura / pagamento', 'Descrição / compra', 'Meio', 'Categoria', 'Parcela', 'Valor'], 2)
        self.tabela.table.setAccessibleName('Lançamentos da consulta financeira aplicada')
        self.tabela.editar.connect(self.editar)
        self.tabela.excluir.connect(self.excluir)
        ll.addWidget(self.tabela, 1)
        ll.addWidget(texto('Editar abre a compra inteira. Excluir remove somente os lançamentos escolhidos.', 9, C['muted']))
        self.layout.addWidget(lista, 1)
        links = LinhaResponsiva(950)
        for nome, subtitulo, image, acao in [('Despesas por semana', 'Despesas agrupadas por semana.', 'calendar-days', self.despesas_semanas), ('Histórico de taxas', 'Totais confirmados ou estimados.', 'percent', self.historico_taxas), ('Regra de fechamento', 'Histórico por vigência, somente leitura.', 'receipt', self.regra_fechamento)]:
            links.addWidget(acesso(nome, subtitulo, image, C['yellow'] if image == 'percent' else C['blue'], acao), 1)
        self.layout.addLayout(links)

    def abrir(self, janela):
        janela.setAttribute(Q.Qt.WidgetAttribute.WA_DeleteOnClose)
        janela.open()
        return janela

    def ao_alterar(self):
        self.controlador.atualizar()

    def invalidar(self):
        self.sujo = True
        if self.controlador.area == 'Finanças':
            self.atualizar()

    def consultar(self):
        try:
            consulta = self.seletor.consulta()
            resultado = self.servico.consultar(consulta)
        except ERROS as erro:
            self.pendente.setText('Consulta não aplicada: ' + str(erro))
            self.pendente.show()
            return
        self.consulta, self.resultado = consulta, resultado
        self.sujo = False
        self.exibir()
        self.marcar_pendente()

    def atualizar(self):
        if self.sujo:
            try:
                self.resultado = self.servico.consultar(self.consulta)
            except ERROS as erro:
                self.pendente.setText('Dados não atualizados: ' + str(erro))
                self.pendente.show()
                return
            self.sujo = False
            self.exibir()
        self.marcar_pendente()

    def marcar_pendente(self):
        try:
            pendente = self.seletor.consulta() != self.consulta
        except ValueError as erro:
            self.pendente.setText(str(erro) + ' Os valores continuam na consulta aplicada.')
            self.pendente.show()
            return
        self.pendente.setText('Período alterado — clique em Consultar. Os valores ainda são da consulta aplicada.' if pendente else '')
        self.pendente.setVisible(pendente)

    def limpar(self):
        ano, mes, _ = selecao_inicial('Fechamento atual', self.hoje())
        self.seletor.tipo.setCurrentText('Fechamento')
        self.seletor.ano.setValue(ano)
        self.seletor.mes.setCurrentIndex(mes - 1)
        self.recorte = 0
        self.consultar()

    def exibir(self):
        r = self.resultado['resumo']
        for chave, campo in {**self.cards, **self.secundarios}.items():
            campo.setText(moeda(r[chave]))
        self.cards['saldo'].setStyleSheet(f'font-size:22pt;font-weight:600;color:{C["red"] if r["saldo"] < 0 else C["turquoise"]};background:transparent;border:0;')
        a, b = self.resultado['intervalo']
        self.intervalo.setText(f'Consulta financeira independente: {br(a)} a {br(b)} · Inclui faturas futuras dentro do período.')
        avisos = []
        if r['parciais']:
            avisos.append('Histórico de ' + ', '.join(map(str, r['parciais'])) + ' não descontado neste recorte: saldo provisório, sem rateio.')
        if r['estimados']:
            avisos.append('Taxas estimadas em ' + ', '.join(map(str, r['estimados'])) + ': saldo não confirmado.')
        self.aviso.setText(' '.join(avisos))
        self.aviso.setVisible(bool(avisos))
        self.preencher_lista()

    def aplicar_recorte(self, indice):
        self.recorte = indice
        self.preencher_lista()

    def preencher_lista(self):
        if self.resultado is None:
            return
        linhas = self.resultado['linhas']
        r = self.recorte
        linhas = [v for v in linhas if r == 0 or r == 1 and v['tipo'] == 'despesa' or r == 2 and v['tipo'] == 'taxa' or r == 3 and v['parcelas'] > 1]
        self.tabela.preencher([(v['id'], [br(v['data_compra']) if v.get('data_compra') else '—', br(v['data']), v['descricao'], v['meio'], v['categoria'], f"{v['parcela']}/{v['parcelas']}" if v['parcelas'] > 1 else '—', reais(v['valor_centavos'])]) for v in linhas])
        for i, b in enumerate(self.botoes_recorte):
            b.setProperty('active', i == self.recorte)
            b.style().unpolish(b)
            b.style().polish(b)

    def abrir_despesa(self):
        return self.abrir(FormularioLancamento(self.servico, self.ao_alterar, self.hoje(), parent=self))

    def editar(self, identificador):
        registro = next((r for r in self.resultado['linhas'] if r['id'] == identificador), None)
        if registro:
            try:
                form = FormularioLancamento(self.servico, self.ao_alterar, self.hoje(), registro, self)
            except ERROS as erro:
                W.QMessageBox.warning(self, 'Compra não carregada', str(erro))
                return None
            return self.abrir(form)

    def abrir_taxas(self):
        return self.abrir(FormularioTaxas(self.servico, self.ao_alterar, self.hoje(), self))

    def excluir(self, ids):
        registros = [r for r in self.resultado['linhas'] if r['id'] in ids]
        if not registros:
            return
        if W.QMessageBox.question(self, 'Excluir lançamentos', f'Excluir somente {len(registros)} lançamento(s) selecionado(s)?\nUm backup será criado. As outras parcelas serão preservadas; editar uma compra com parcelas faltantes será bloqueado.', W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No) != W.QMessageBox.StandardButton.Yes:
            return
        try:
            self.servico.excluir(registros)
        except ERROS as erro:
            W.QMessageBox.warning(self, 'Exclusão não concluída', str(erro))
            return
        self.ao_alterar()

    def despesas_semanas(self):
        registros = [Lancamento(r['id'], date.fromisoformat(r['data']), date.fromisoformat(r['data_compra']) if r.get('data_compra') else None,
                                r['descricao'], r['meio'], 'Taxa' if r['tipo'] == 'taxa' else r['categoria'], r['valor_centavos'], f"{r['parcela']}/{r['parcelas']}" if r['parcelas'] > 1 else '—') for r in self.resultado['linhas']]
        return self.abrir(janela_despesas(self, registros, tuple(date.fromisoformat(d) for d in self.resultado['intervalo'])))

    def historico_taxas(self):
        return self.abrir(HistoricoTaxas(self))

    def regra_fechamento(self):
        config = fechamento.estado()
        d = JanelaDetalhe(self, 'Regra de fechamento', 'Histórico do banco de estudo · somente leitura', 'receipt', explicacao='A regra é usada por vigência, preservando períodos antigos. A edição será integrada com configurações e nuvem na sequência do plano; não há configuração de conta nesta entrada.')
        d.resumo([('Dia vigente neste mês', fechamento.dia_no_mes(self.hoje().year, self.hoje().month)), ('Regra inicial', 'dia 09')])
        if config['historico']:
            d.adicionar_tabela([Coluna('Vigência', 'data', True), Coluna('Dia de fechamento', 'numero')], [(date.fromisoformat(r['vigencia']), r['dia']) for r in config['historico']])
        else:
            d.vazio('Regra inicial: dia 09', 'Sem alterações por vigência neste banco. O fechamento de Outubro corresponde a 10/10 a 09/11. Compras no dia 09 entram na fatura seguinte.')
        return self.abrir(d)
