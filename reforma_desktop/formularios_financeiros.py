"""Formulários Qt sobre as transações financeiras existentes, em banco de estudo."""
from datetime import date, timedelta
import sqlite3
from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto, botao, caixa, ajuda
from tema_noturno import C
from ProgramFeira import financeiro as f
from reforma_desktop.campos_financeiros import campo_data, data_iso, valor_br, SeletorFinanceiro

ERROS = (ValueError, OSError, sqlite3.Error)


class FormularioBase(W.QDialog):
    def __init__(self, titulo, ao_alterar, parent=None):
        super().__init__(parent)
        self.ao_alterar = ao_alterar
        self.setWindowTitle(titulo)
        self.resize(610, 500)
        self.setMinimumWidth(460)
        root = W.QVBoxLayout(self)
        root.addWidget(texto(titulo, 18, bold=True))
        scroll = W.QScrollArea()
        scroll.setWidgetResizable(True)
        self.corpo = W.QWidget()
        self.layout = W.QVBoxLayout(self.corpo)
        scroll.setWidget(self.corpo)
        root.addWidget(scroll, 1)
        self.erro = texto('', 10, C['red'])
        self.erro.setWordWrap(True)
        self.erro.setAccessibleName('Resultado da gravação')
        root.addWidget(self.erro)
        botoes = W.QHBoxLayout()
        botoes.addWidget(botao('Cancelar', self.reject))
        botoes.addStretch()
        self.salvar = botao('Salvar', self.gravar, 'check', True)
        botoes.addWidget(self.salvar)
        root.addLayout(botoes)

    def confirmar(self, titulo, mensagem):
        return W.QMessageBox.question(self, titulo, mensagem, W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No) == W.QMessageBox.StandardButton.Yes

    def gravar(self):
        self.salvar.setEnabled(False)
        try:
            if self.executar() is False:
                self.salvar.setEnabled(True)
                return
        except ERROS as erro:
            self.erro.setText(str(erro))
            self.salvar.setEnabled(True)
            return
        self.accept()
        self.ao_alterar()


class FormularioLancamento(FormularioBase):
    def __init__(self, servico, ao_alterar, hoje, registro=None, parent=None):
        self.servico = servico
        self.anterior = servico.compra(registro['id']) if registro else None
        r = self.anterior or {}
        self.tipo = r.get('tipo', 'despesa')
        titulo = ('Editar compra inteira' if r else 'Nova despesa') if self.tipo == 'despesa' else 'Editar taxa das vendas'
        super().__init__(titulo, ao_alterar, parent)
        self.data = campo_data(r.get('data_compra') or r.get('data') or hoje, 'Data')
        self.descricao = W.QLineEdit(r.get('descricao', ''))
        self.descricao.setMaxLength(200)
        self.valor = W.QLineEdit(valor_br(r['valor_centavos']) if r else '')
        self.valor.setPlaceholderText('0,00')
        self.meio, self.categoria = W.QComboBox(), W.QComboBox()
        self.meio.addItems(f.MEIOS)
        self.meio.setCurrentText(r.get('meio', 'Dinheiro'))
        self.categoria.addItems(f.CATEGORIAS)
        self.categoria.setCurrentText(r.get('categoria', 'Outros'))
        self.parcelas = W.QSpinBox()
        self.parcelas.setRange(1, 120)
        self.parcelas.setValue(r.get('parcelas', 1))
        self.origem = W.QComboBox()
        self.origem.addItems(['Preservar primeira fatura antiga', 'Informar data original da compra'])
        self.legado = bool(r and not r.get('data_compra') and r['meio'] == 'Cartão de crédito' and self.tipo == 'despesa')
        self.form = W.QFormLayout()
        self.rotulo_data = texto('Data de pagamento', 10)
        self.form.addRow(self.rotulo_data, self.data)
        self.form.addRow('Descrição', self.descricao)
        self.form.addRow('Valor total da compra (R$)' if self.tipo == 'despesa' else 'Valor da taxa (R$)', self.valor)
        self.form.addRow('Pagamento', self.meio)
        self.form.addRow('Categoria', self.categoria)
        if self.tipo == 'despesa':
            self.form.addRow('Quantidade de parcelas', self.parcelas)
        self.rotulo_origem = texto('Registro antigo', 10)
        self.form.addRow(self.rotulo_origem, self.origem)
        self.layout.addLayout(self.form)
        self.previa = texto('', 10, C['muted'])
        self.previa.setWordWrap(True)
        self.layout.addWidget(self.previa)
        self.layout.addWidget(ajuda('Como registrar', 'Informe o TOTAL da compra, não uma parcela. Os centavos são distribuídos para a soma ser exata. No cartão, a data é a da compra; compras no fechamento vão para a fatura seguinte. Editar qualquer parcela altera toda a compra, inclusive meses anteriores. Não lance novamente o pagamento da fatura.' if self.tipo == 'despesa' else 'Taxa é o desconto da maquininha nas vendas dessa data. Não é uma despesa do cartão de compras. Não repita descontos já incluídos no histórico anual.'))
        for nome, campo in [('Descrição', self.descricao), ('Valor total da compra' if self.tipo == 'despesa' else 'Valor da taxa', self.valor), ('Pagamento', self.meio), ('Categoria', self.categoria), ('Quantidade de parcelas', self.parcelas)]:
            campo.setAccessibleName(nome)
        self.data.dateChanged.connect(lambda _: self.atualizar_previa())
        self.valor.textChanged.connect(self.atualizar_previa)
        self.parcelas.valueChanged.connect(self.atualizar_previa)
        self.meio.currentIndexChanged.connect(self.atualizar_previa)
        self.origem.currentIndexChanged.connect(self.trocar_origem)
        self.salvar.setText('Salvar compra' if self.tipo == 'despesa' else 'Salvar taxa')
        self.atualizar_previa()

    def trocar_origem(self):
        with Q.QSignalBlocker(self.data):
            if self.origem.currentIndex() == 1:
                self.data.setSpecialValueText('Informe a compra original')
                self.data.setDate(self.data.minimumDate())
            else:
                self.data.setSpecialValueText('')
                self.data.setDate(Q.QDate(date.fromisoformat(self.anterior['data'])))
        self.atualizar_previa()

    def dados(self):
        if not self.parcelas.hasAcceptableInput():
            raise ValueError('Informe de 1 a 120 parcelas.')
        self.parcelas.interpretText()
        credito = self.tipo == 'despesa' and self.meio.currentText() == 'Cartão de crédito'
        original = credito and (not self.legado or self.origem.currentIndex() == 1)
        if original and self.legado and self.data.date() == self.data.minimumDate():
            raise ValueError('Informe a data original da compra antes de salvar.')
        data = data_iso(self.data)
        return dict(tipo=self.tipo, data=data, descricao=self.descricao.text(), valor=self.valor.text(),
                    meio=self.meio.currentText(), categoria=self.categoria.currentText(),
                    parcelas=self.parcelas.value() if self.tipo == 'despesa' else 1,
                    anterior=self.anterior, data_compra=data if original else None)

    def atualizar_previa(self, *args):
        credito = self.tipo == 'despesa' and self.meio.currentText() == 'Cartão de crédito'
        self.rotulo_data.setText(('Primeira fatura antiga' if self.legado and self.origem.currentIndex() == 0 else 'Data da compra') if credito else 'Data da venda' if self.tipo == 'taxa' else 'Data de pagamento')
        self.origem.setVisible(self.legado and credito)
        self.rotulo_origem.setVisible(self.legado and credito)
        try:
            d = self.dados()
            if d['parcelas'] > 1 and d['meio'] != 'Cartão de crédito':
                self.previa.setText('Parcelas são permitidas somente para despesas no cartão de crédito. Para outro meio, escolha 1 lançamento.')
                return
            datas, valores = f.preparar_parcelas(d['data'], f.centavos(d['valor']), d['parcelas'], d['meio'], d['data_compra'], self.anterior)
            mostra = datas if len(datas) <= 4 else [*datas[:3], '…', datas[-1]]
            texto_datas = ' · '.join(date.fromisoformat(v).strftime('%d/%m/%Y') if v != '…' else v for v in mostra)
            quantias = ' / '.join('R$ ' + valor_br(v) for v in sorted(set(valores)))
            self.previa.setText(f'Total: R$ {valor_br(sum(valores))} · {len(valores)} lançamento(s): {quantias}.\n' + ('Faturas previstas: ' if credito else 'Pagamento em: ') + texto_datas)
        except (ValueError, OverflowError):
            self.previa.setText('Informe o valor total e confira as datas antes de salvar.')

    def executar(self):
        d = self.dados()
        if d['parcelas'] > 1 and d['meio'] != 'Cartão de crédito':
            raise ValueError('Parcelas são permitidas somente para despesas no cartão de crédito.')
        # Valida a distribuição antes de perguntar; o núcleo valida o restante.
        quantias = f.dividir_total(f.centavos(d['valor']), d['parcelas'])
        if d['parcelas'] > 1 or (self.anterior and self.anterior['parcelas'] > 1):
            removidas = max(0, (self.anterior or {}).get('parcelas', 1) - d['parcelas'])
            aviso = f'\nAs últimas {removidas} parcelas serão removidas.' if removidas else ''
            if not self.confirmar('Confirmar compra inteira', f'Total: R$ {valor_br(sum(quantias))}, em {d["parcelas"]} parcela(s).\nTodas as parcelas serão atualizadas, inclusive as de meses anteriores.{aviso}'):
                return False
        self.servico.salvar_compra(**d)


class FormularioTaxas(FormularioBase):
    def __init__(self, servico, ao_alterar, hoje, parent=None):
        self.servico = servico
        super().__init__('Taxas da maquininha por semana', ao_alterar, parent)
        self.layout.addWidget(texto('Descontos cobrados nas vendas do cartão, em reais.', 11, bold=True))
        self.seletor = SeletorFinanceiro(hoje, 'Semana', fixo=True)
        self.layout.addWidget(self.seletor)
        self.layout.addWidget(botao('Carregar semana', self.carregar, 'search'))
        self.aviso_semana = texto('', 9, C['yellow'])
        self.aviso_semana.setWordWrap(True)
        self.layout.addWidget(self.aviso_semana)
        self.dias = W.QWidget()
        self.grade = W.QFormLayout(self.dias)
        self.layout.addWidget(self.dias)
        self.layout.addWidget(ajuda('Taxas por data', 'Preencha sexta, domingo ou qualquer dia em que vendeu. Campo vazio mantém uma taxa existente. Cada taxa fica na data da venda; para removê-la use Excluir no lançamento. Datas cobertas pelo histórico anual não podem receber a mesma taxa novamente.'))
        self.campos, self.iniciais = {}, {}
        self.intervalo = None
        self.seletor.alterado.connect(self.pendente)
        self.salvar.setText('Salvar taxas da semana')
        self.carregar()

    def pendente(self):
        try:
            limites = self.seletor.consulta().limites()
        except ValueError as erro:
            self.aviso_semana.setText(str(erro))
            return
        if self.intervalo and limites != self.intervalo:
            self.aviso_semana.setText('Semana alterada — clique em Carregar. Os campos abaixo ainda pertencem à semana carregada.')
        else:
            self.aviso_semana.setText('')

    def carregar(self):
        if self.intervalo and any(c.text() != self.iniciais[d] for d, c in self.campos.items()):
            if not self.confirmar('Trocar semana', 'Descartar os valores ainda não salvos e carregar a semana escolhida?'):
                return
        try:
            self.esperado = self.servico.semana_taxas(self.seletor.consulta().limites()[0])
        except ERROS as erro:
            self.erro.setText(str(erro))
            return
        self.intervalo = self.esperado['intervalo']
        while self.grade.rowCount():
            self.grade.removeRow(0)
        self.campos, self.iniciais = {}, {}
        registros = {r['data']: r for r in self.esperado['registros']}
        primeira = date.fromisoformat(self.intervalo[0])
        for i, nome in enumerate(('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')):
            dia = (primeira + timedelta(days=i)).isoformat()
            cobertura = next((r for r in self.esperado['anuais'] if r['inicio'] <= dia <= r['fim']), None)
            if cobertura:
                campo = texto(f'Incluída no histórico de {cobertura["ano"]}', 10, C['muted'])
            else:
                campo = W.QLineEdit(valor_br(registros[dia]['valor_centavos']) if dia in registros else '')
                campo.setAccessibleName(f'Taxa de {nome}, {dia}')
                self.campos[dia], self.iniciais[dia] = campo, campo.text()
            self.grade.addRow(f'{nome} · {date.fromisoformat(dia):%d/%m/%Y}', campo)
        self.salvar.setEnabled(bool(self.campos))
        self.erro.setText('')
        self.pendente()

    def executar(self):
        if self.seletor.consulta().limites() != self.intervalo:
            raise ValueError('Carregue a semana escolhida antes de salvar; os campos não foram movidos para outra data.')
        self.servico.salvar_taxas(self.intervalo[0], {dia: campo.text() for dia, campo in self.campos.items()}, self.esperado)


class FormularioAnual(FormularioBase):
    def __init__(self, servico, ao_alterar, hoje, registro=None, parent=None):
        self.servico, self.anterior = servico, registro
        r = registro or {}
        super().__init__('Editar total histórico de taxas' if registro else 'Novo total histórico de taxas', ao_alterar, parent)
        form = W.QFormLayout()
        self.ano = W.QSpinBox()
        self.ano.setRange(1900, 9998)
        self.ano.setValue(r.get('ano', hoje.year))
        self.ano.setReadOnly(bool(registro))
        self.inicio = campo_data(r.get('inicio', date(hoje.year, 1, 1)), 'Cobertura inicial')
        self.fim = campo_data(r.get('fim', hoje), 'Cobertura final')
        self.valor = W.QLineEdit(valor_br(r['valor_centavos']) if r else '')
        self.natureza = W.QComboBox()
        self.natureza.addItems(['Confirmada', 'Estimada'])
        self.natureza.setCurrentText(r.get('natureza', 'Confirmada'))
        self.natureza.setToolTip('Confirmada: valor conferido no extrato. Estimada: aproximação; o saldo será identificado como não confirmado.')
        self.observacao = W.QLineEdit(r.get('observacao', ''))
        for nome, campo in [('Ano', self.ano), ('Cobertura inicial', self.inicio), ('Cobertura final', self.fim), ('Total acumulado (R$)', self.valor), ('Natureza', self.natureza), ('Origem / observação', self.observacao)]:
            campo.setAccessibleName(nome)
            form.addRow(nome, campo)
        self.layout.addLayout(form)
        explicacao = texto('Informe o TOTAL coberto pelo extrato, não apenas a diferença. O histórico não é dividido entre meses ou dias. Ao trocar o ano, confira as duas datas da cobertura.', 10, C['muted'])
        explicacao.setWordWrap(True)
        self.layout.addWidget(explicacao)

    def executar(self):
        if not self.ano.hasAcceptableInput():
            raise ValueError('Informe um ano válido.')
        self.ano.interpretText()
        self.servico.salvar_anual(self.ano.value(), data_iso(self.inicio), data_iso(self.fim), self.valor.text(), self.natureza.currentText(), self.observacao.text(), self.anterior)
