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
        self.setWindowTitle('Conflitos — projeto de validação' if getattr(getattr(parent,'conexao',getattr(parent,'nuvem',None)),'validacao_real',False) else 'Conflitos — dados fictícios')
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
        for lado, titulo in [('pc','Neste PC'),('nuvem','No projeto de validação' if getattr(getattr(parent,'conexao',getattr(parent,'nuvem',None)),'validacao_real',False) else 'No serviço simulado')]:
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
        real = self.conexao.validacao_real
        self.setWindowTitle('Conexão — projeto de validação' if real else 'Nuvem simulada — estudo Qt')
        self.resize(720, 650)
        root = W.QVBoxLayout(self)
        if real:
            scroll = W.QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Q.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            corpo = W.QWidget()
            l = W.QVBoxLayout(corpo)
            scroll.setWidget(corpo)
            root.addWidget(scroll)
        else:
            l = root
        l.addWidget(texto('Conexão de validação' if real else 'Sessão e sincronização — estudo', 20, bold=True))
        aviso = texto('Conecta ao projeto identificado abaixo. Use apenas exemplos de teste. Login não envia registros; a transferência inicial exige conferência e confirmação.' if real else 'Serviço fictício local. Não acessa sua conta, não envia dados ao Supabase e não pede senha. A conexão real será validada antes da versão 2.0.', 11, C['muted'])
        aviso.setWordWrap(True)
        l.addWidget(aviso)
        projeto = texto('Projeto: ' + self.conexao.cliente.url if real else 'Conta fictícia: estudo@example.invalid', 11, bold=True)
        projeto.setWordWrap(True)
        projeto.setTextInteractionFlags(Q.Qt.TextInteractionFlag.TextSelectableByMouse)
        l.addWidget(projeto)
        if real:
            form = W.QFormLayout()
            self.email = W.QLineEdit()
            self.email.setAccessibleName('E-mail da conta de validação')
            self.senha = W.QLineEdit()
            self.senha.setEchoMode(W.QLineEdit.EchoMode.Password)
            self.senha.setAccessibleName('Senha do aplicativo no projeto de validação')
            form.addRow('E-mail', self.email)
            form.addRow('Senha do aplicativo', self.senha)
            l.addLayout(form)
            self.conta = texto('', 10, C['muted'])
            self.conta.setWordWrap(True)
            l.addWidget(self.conta)
        self.status = W.QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumHeight(170)
        self.status.setAccessibleName('Resultado da conexão de validação' if real else 'Resultado da sincronização fictícia')
        l.addWidget(self.status, 1)
        self.botoes = {}
        for nome, rotulo, funcao, dica in [
            ('entrar','Verificar acesso' if real else 'Conectar conta fictícia',self.entrar if real else self.conexao.conectar,'Não transfere registros. A senha fica somente em memória; no Windows, só a sessão renovável é persistida com DPAPI.'),
            ('sair','Desconectar',self.conexao.desconectar,'Remove a sessão protegida do estudo. Preserva os registros, o vínculo e as cópias.'),
            ('conferir','Conferir transferência inicial',self.conexao.conferir,'Cria backup e compara todos os registros. Não transfere dados.'),
            ('transferir','Transferir dados conferidos',self.transferir,'Exige confirmação. Se os dados mudaram após a conferência, a transferência é recusada.'),
            ('sincronizar','Sincronizar agora',self.conexao.sincronizar,'Compara versões, confirma lotes pendentes e preserva uma cópia antes de aplicar mudanças.'),
            ('conflitos','Conferir conflitos…',self.conflitos,'Mostra as duas versões e exige escolha explícita. Nunca decide por data de modificação.'),
            ('simular','Simular alteração externa: + R$ 1,00 em Pix',self.simular,'Altera somente a venda mais recente no arquivo do serviço fictício. Use para verificar o recebimento automático sem celular ou conta real.')]:
            if real and nome == 'simular':
                continue
            linha = W.QHBoxLayout()
            b = botao(rotulo, funcao)
            self.botoes[nome] = b
            linha.addWidget(b)
            linha.addWidget(ajuda(rotulo, dica))
            l.addLayout(linha)
        if real:
            self.botoes['retomar'] = botao('Retomar sessão salva', self.conexao.retomar)
            l.addWidget(self.botoes['retomar'])
        self.automatico = W.QCheckBox('Consultar automaticamente a cada minuto enquanto conectado')
        self.automatico.toggled.connect(self.conexao.alterar_automatico)
        l.addWidget(self.automatico)
        if real:
            self.automatico.hide()
            l.addWidget(texto('Sincronização manual nesta validação. Nenhum envio ao abrir ou salvar.', 10, C['muted']))
        (root if real else l).addWidget(botao('Fechar', self.reject))
        self.conexao.mudou.connect(self.atualizar)
        self.atualizar()

    def entrar(self):
        email, senha = self.email.text().strip(), self.senha.text()
        self.senha.clear()
        self.conexao.conectar(email, senha)

    def atualizar(self):
        n = self.conexao
        vinculado = n.vinculado
        self.status.setPlainText(n.status)
        with Q.QSignalBlocker(self.automatico):
            self.automatico.setChecked(n.automatico)
        self.automatico.setEnabled(not n.ocupado)
        if n.validacao_real:
            self.conta.setText(('Conta: ' + n.sessao.email + (' · acesso verificado' if n.sessao_verificada else ' · verificação pendente')) if n.sessao else 'Nenhuma sessão ativa.')
            self.email.setEnabled(not n.ocupado)
            self.senha.setEnabled(not n.ocupado)
        for nome, b in self.botoes.items():
            permitido = bool(n.sessao and (not n.validacao_real or n.sessao_verificada))
            if nome == 'entrar': permitido = True
            elif nome == 'sair': permitido = bool(n.sessao)
            elif nome == 'retomar': permitido = bool(n.sessao)
            elif nome == 'conferir': permitido = bool(n.sessao and not vinculado and (not n.validacao_real or n.sessao_verificada))
            elif nome == 'transferir': permitido = bool(n.preparacao and not vinculado and (not n.validacao_real or n.sessao_verificada))
            elif nome == 'sincronizar' and n.validacao_real: permitido = bool(n.sessao_verificada and (vinculado or n.transferencia_confirmada))
            elif nome in ('conflitos','simular'): permitido = bool(n.sessao and vinculado and (not n.validacao_real or n.sessao_verificada))
            b.setEnabled(permitido and not n.ocupado)
        self.botoes['conflitos'].setText('Revisar escolhas dos conflitos…' if n.revisao and n.revisao['conflitos'] else 'Conferir conflitos…')

    def transferir(self):
        n = self.conexao
        if not n.preparacao or n.ocupado:
            return
        r = n.preparacao['relatorio']
        mensagem = ('Enviar ' + str(sum(r['novos'].values())) + ' registros para ' + n.cliente.url + '? Use somente dados de teste. Backup: ' + r['backup']) if n.validacao_real else ('Enviar ' + str(sum(r['novos'].values())) + ' registros para o serviço local simulado? Nenhum dado vai para a conta real. Backup: ' + r['backup'])
        if W.QMessageBox.question(self, 'Transferência para validação' if n.validacao_real else 'Transferência fictícia', mensagem, W.QMessageBox.StandardButton.Yes | W.QMessageBox.StandardButton.No, W.QMessageBox.StandardButton.No) == W.QMessageBox.StandardButton.Yes:
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
