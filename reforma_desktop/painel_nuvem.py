"""Sessão e revisão de sincronização Qt, explicitamente fictícias nesta etapa."""
from PySide6 import QtCore as Q, QtWidgets as W
from componentes_noturno import texto, botao, ajuda
from tema_noturno import C
from datetime import date

NOMES = {'vendas':'Venda', 'financeiro_lancamentos':'Lançamento financeiro', 'financeiro_taxas_anuais':'Taxa anual'}


def descrever(registro):
    if registro is None:
        return 'Registro excluído neste lado. Escolher esta versão confirma a exclusão.'
    nomes = {'data':'Data', 'data_compra':'Data da compra', 'ano':'Ano', 'inicio':'Início', 'fim':'Fim', 'descricao':'Descrição', 'tipo':'Tipo', 'meio':'Pagamento', 'categoria':'Categoria', 'parcela':'Parcela', 'parcelas':'Parcelas', 'natureza':'Natureza', 'observacao':'Observação', 'dinheiro_centavos':'Dinheiro', 'pix_centavos':'Pix', 'cartao_centavos':'Cartão', 'valor_centavos':'Valor'}
    from ProgramFeira.resumos import moeda
    from decimal import Decimal
    linhas = []
    for k, v in registro.items():
        if k not in nomes:
            continue
        if k in ('data', 'data_compra', 'inicio', 'fim') and v is not None:
            v = date.fromisoformat(v).strftime('%d/%m/%Y')
        if k.endswith('_centavos'):
            v = moeda(Decimal(v)/100)
        linhas.append(nomes[k] + ': ' + str(v if v is not None else ''))
    return '\n'.join(linhas)


class Revisao(W.QDialog):
    def __init__(self, parent, revisao, aplicar):
        super().__init__(parent)
        self.revisao, self.aplicar = revisao, aplicar
        self.escolhas = {}
        self.setWindowTitle('Conflitos — dados fictícios')
        self.resize(840, 620)
        l = W.QVBoxLayout(self)
        l.addWidget(texto('Qual versão deve ser mantida?', 18, bold=True))
        nota = texto('Escolha cada registro. Um registro excluído confirma a exclusão. O núcleo confere novamente as versões e preserva um backup antes da aplicação.', 10, C['muted'])
        nota.setWordWrap(True)
        l.addWidget(nota)
        self.lista = W.QListWidget()
        for r in revisao['conflitos']:
            d = r['pc'] or r['nuvem'] or {}
            self.lista.addItem(NOMES[r['tabela']] + ' · ' + str(d.get('data', d.get('ano', r['id']))))
        self.lista.setMaximumHeight(min(160, max(48, 28*len(revisao['conflitos'])+12)))
        l.addWidget(self.lista)
        lados = W.QHBoxLayout()
        self.textos = {}
        self.botoes_lado = {}
        for lado, titulo in [('pc','Neste PC'),('nuvem','No serviço simulado')]:
            coluna = W.QVBoxLayout()
            coluna.addWidget(texto(titulo, 12, bold=True))
            campo = W.QPlainTextEdit()
            campo.setReadOnly(True)
            campo.setAccessibleName(titulo)
            self.textos[lado] = campo
            coluna.addWidget(campo)
            b = botao('Usar esta versão', lambda checked=False, lado=lado: self.escolher(lado))
            self.botoes_lado[lado] = b
            coluna.addWidget(b)
            lados.addLayout(coluna)
        l.addLayout(lados, 1)
        self.aviso = texto('', 10)
        self.aviso.setWordWrap(True)
        l.addWidget(self.aviso)
        self.confirmar = botao('Aplicar escolhas', self.confirmar_escolhas, 'check')
        self.confirmar.setEnabled(False)
        l.addWidget(self.confirmar)
        l.addWidget(botao('Cancelar', self.reject))
        self.lista.currentRowChanged.connect(self.mostrar)
        self.lista.setCurrentRow(0)

    def mostrar(self):
        r = self.revisao['conflitos'][self.lista.currentRow()]
        for lado, campo in self.textos.items():
            campo.setPlainText(descrever(r[lado]))
        for b in self.botoes_lado.values():
            b.setEnabled(r['resolvivel'])
        self.aviso.setText('Escolha: ' + self.escolhas.get(r['tabela'] + ':' + r['id'], 'pendente') if r['resolvivel'] else 'Cadastros independentes na mesma data/ano: revise os cadastros. Esta tela não sobrescreve essas versões.')

    def escolher(self, lado):
        r = self.revisao['conflitos'][self.lista.currentRow()]
        if not r['resolvivel']:
            return
        self.escolhas[r['tabela'] + ':' + r['id']] = lado
        self.confirmar.setEnabled(len(self.escolhas) == len(self.revisao['conflitos']))
        self.mostrar()

    def confirmar_escolhas(self):
        if len(self.escolhas) != len(self.revisao['conflitos']):
            return
        if W.QMessageBox.question(self, 'Aplicar versões escolhidas', 'Sincronizar mantendo as versões escolhidas? Uma versão excluída confirma a exclusão. Uma cópia anterior será preservada.', W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No) != W.QMessageBox.StandardButton.Yes:
            return
        escolhas = dict(self.escolhas)
        self.accept()
        self.aplicar(self.revisao, escolhas)


class PainelNuvem(W.QDialog):
    def __init__(self, janela):
        super().__init__(janela)
        self.conexao = janela.nuvem
        self.setWindowTitle('Nuvem simulada — estudo Qt')
        self.resize(720, 650)
        l = W.QVBoxLayout(self)
        l.addWidget(texto('Sessão e sincronização — estudo', 20, bold=True))
        aviso = texto('Serviço fictício local. Não acessa sua conta, não envia dados ao Supabase e não pede senha. A conexão real será validada antes da versão 2.0.', 11, C['muted'])
        aviso.setWordWrap(True)
        l.addWidget(aviso)
        l.addWidget(texto('Conta fictícia: estudo@example.invalid', 11, bold=True))
        self.status = W.QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumHeight(170)
        self.status.setAccessibleName('Resultado da sincronização fictícia')
        l.addWidget(self.status, 1)
        self.botoes = {}
        for nome, rotulo, funcao, dica in [
            ('entrar','Conectar conta fictícia',self.conexao.conectar,'Não transfere registros. No Windows, salva somente a sessão renovável fictícia com DPAPI na pasta do estudo.'),
            ('sair','Desconectar',self.conexao.desconectar,'Remove a sessão protegida do estudo. Preserva os registros, o vínculo e as cópias.'),
            ('conferir','Conferir transferência inicial',self.conexao.conferir,'Cria backup e compara todos os registros. Não transfere dados.'),
            ('transferir','Transferir dados conferidos',self.transferir,'Exige confirmação. Se os dados mudaram após a conferência, a transferência é recusada.'),
            ('sincronizar','Sincronizar agora',self.conexao.sincronizar,'Compara versões, confirma lotes pendentes e preserva uma cópia antes de aplicar mudanças.'),
            ('conflitos','Conferir conflitos…',self.conflitos,'Mostra as duas versões e exige escolha explícita. Nunca decide por data de modificação.'),
            ('simular','Simular alteração externa: + R$ 1,00 em Pix',self.simular,'Altera somente a venda mais recente no arquivo do serviço fictício. Use para verificar o recebimento automático sem celular ou conta real.')]:
            linha = W.QHBoxLayout()
            b = botao(rotulo, funcao)
            self.botoes[nome] = b
            linha.addWidget(b)
            linha.addWidget(ajuda(rotulo, dica))
            l.addLayout(linha)
        self.automatico = W.QCheckBox('Consultar automaticamente a cada minuto enquanto conectado')
        self.automatico.toggled.connect(self.conexao.alterar_automatico)
        l.addWidget(self.automatico)
        l.addWidget(botao('Fechar', self.reject))
        self.conexao.mudou.connect(self.atualizar)
        self.atualizar()

    def atualizar(self):
        n = self.conexao
        vinculado = n.vinculado
        self.status.setPlainText(n.status)
        with Q.QSignalBlocker(self.automatico):
            self.automatico.setChecked(n.automatico)
        self.automatico.setEnabled(not n.ocupado)
        for nome, b in self.botoes.items():
            permitido = bool(n.sessao)
            if nome == 'entrar': permitido = True
            elif nome == 'sair': permitido = bool(n.sessao)
            elif nome == 'conferir': permitido = bool(n.sessao and not vinculado)
            elif nome == 'transferir': permitido = bool(n.preparacao and not vinculado)
            elif nome in ('conflitos','simular'): permitido = bool(n.sessao and vinculado)
            b.setEnabled(permitido and not n.ocupado)
        self.botoes['conflitos'].setText('Revisar escolhas dos conflitos…' if n.revisao and n.revisao['conflitos'] else 'Conferir conflitos…')

    def transferir(self):
        n = self.conexao
        if not n.preparacao or n.ocupado:
            return
        r = n.preparacao['relatorio']
        if W.QMessageBox.question(self, 'Transferência fictícia', 'Enviar ' + str(sum(r['novos'].values())) + ' registros para o serviço local simulado? Nenhum dado vai para a conta real. Backup: ' + r['backup'], W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No) == W.QMessageBox.StandardButton.Yes:
            n.transferir()

    def conflitos(self):
        n = self.conexao
        if n.revisao and n.revisao['conflitos']:
            self.revisao_popup = Revisao(self, n.revisao, lambda r, e: n.sincronizar(r, e))
            self.revisao_popup.open()
        else:
            n.conferir_conflitos()

    def simular(self):
        try:
            dia = self.conexao.cliente.simular_venda_externa()
            self.conexao.informar('Alteração externa fictícia em ' + dia + ': Pix + R$ 1,00. Feche as janelas de configuração para permitir a consulta automática, ou use Sincronizar agora.')
        except (ValueError, OSError):
            self.conexao.informar('Não foi possível simular a alteração externa. Confira a transferência inicial.')

    def reject(self):
        if not self.conexao.ocupado:
            super().reject()

    def closeEvent(self, evento):
        if self.conexao.ocupado:
            evento.ignore()
        else:
            super().closeEvent(evento)
