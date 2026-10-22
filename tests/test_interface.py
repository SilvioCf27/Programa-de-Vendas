"""Teste funcional dos widgets reais. Execute com uma sessão gráfica disponível."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InterfaceTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'), 'Sem sessão gráfica')
    def test_fluxos_reais_em_banco_temporario(self):
        # Subprocesso evita que a interface acesse o banco pessoal dos demais testes.
        script = r'''
from unittest.mock import patch
from pathlib import Path
import sys, os
sys.path.insert(0, 'tests')
from dados_ficticios import criar_banco
criar_banco(Path(os.environ['PROGRAMFEIRA_DATA_DIR']) / 'vendas.db')
import tkinter as tk
from pathlib import Path
with patch.object(tk.Tk, 'mainloop'):
    import ProgramFeira.main as a
errors = []
a.janela.report_callback_exception = lambda *args: errors.append(args)
a.janela.update()
assert len(a.tabela.get_children()) == 9
assert a.formulario.state() == 'withdrawn'
# Configurações substitui Dados e as dicas abrem por hover, sem clique.
a.botao_configuracoes.invoke()
a.janela.update()
cfg = a.configuracoes
assert a.abrir_configuracoes() is cfg
assert len(cfg.acoes) == 7
titulo_verificar = 'Verificar integridade do backup…'
dica = cfg.ajudas[titulo_verificar]
dica.widget.event_generate('<Enter>')
a.janela.after(450, lambda: None)
import time
prazo = time.monotonic() + 2
while dica.popup is None and time.monotonic() < prazo:
    a.janela.update(); time.sleep(.01)
assert dica.popup is not None
assert 'Não altera' in dica.texto
dica.widget.event_generate('<Leave>'); a.janela.update()
assert dica.popup is None
with patch.object(a.filedialog, 'askopenfilename', return_value='') as escolher_backup:
    cfg.acoes[titulo_verificar].invoke()
    escolher_backup.assert_called_once()
assert not cfg.winfo_exists()
a.dica_configuracoes.mostrar(); a.janela.update()
a.verificar_formulario_sincronizacao()  # A dica não é um formulário pendente.
a.dica_configuracoes.fechar()
assert not any(a.menu.entrycget(i,'label') == 'Dados' for i in range(a.menu.index('end') + 1) if a.menu.type(i) == 'cascade')
# Sincronizar antes da primeira visita a Finanças preserva a carga sob demanda.
assert a.painel_financeiro.inicio is None
assert a.painel_financeiro.fim is None
with patch('ProgramFeira.financeiro.resumo_periodo') as consultar_financas:
    a.atualizar_apos_sincronizacao()
    consultar_financas.assert_not_called()
assert a.painel_financeiro.inicio is None
assert not errors
# O acabamento usa controles ttk reais: seletor, teclado e estados permanecem nativos.
combo = a.filtro_mes_combobox
combo.event_generate('<ButtonPress-1>', x=combo.winfo_width()-12, y=combo.winfo_height()//2)
a.janela.update()
popup = str(combo.tk.call('ttk::combobox::PopdownWindow', combo))
assert int(combo.tk.call('winfo', 'ismapped', popup)) == 1
combo.event_generate('<Escape>')
a.janela.update()
check = a.linha_dias.winfo_children()[0]
check.invoke()
assert a.filtros_dias_semana[0].get()
check.invoke()
assert not a.filtros_dias_semana[0].get()
assert 'Gestão da Feira' in a.janela.title()
for coluna in a.colunas:
    assert str(a.tabela.column(coluna, 'anchor')) == 'center'
    assert str(a.tabela.heading(coluna, 'anchor')) == 'center'
assert a.tabela.column('dinheiro', 'width') < 145
# Tema é trocado sem alterar banco, seleção ou formulário.
from ProgramFeira.preferencias import carregar_tema
from ProgramFeira.interface.visual import PALETAS
assert a.tema_atual.get() == 'escuro'
a.alternar_tema()
a.janela.update()
assert a.tema_atual.get() == 'claro'
assert carregar_tema(a.CAMINHO_BANCO.parent) == 'claro'
a.alternar_tema()
a.janela.update()
assert a.tema_atual.get() == 'escuro'
assert str(a.formulario.cget('background')) == PALETAS['escuro']['fundo']
assert str(a.tabela.tag_configure('impar', 'background')) == PALETAS['escuro']['alternada']
for tema in ('grafite', 'areia', 'aurora', 'claro', 'escuro'):
    a.alternar_tema(tema); a.janela.update()
    assert carregar_tema(a.CAMINHO_BANCO.parent) == tema
    assert str(a.tabela.tag_configure('impar', 'background')) == PALETAS[tema]['alternada']
    assert str(a.formulario.cget('background')) == PALETAS[tema]['fundo']
assert a.indicadores_visuais['total'].get() == 'R$ 561,25'
assert a.detalhes_cartoes['media'].get() == 'Inclui dias zerados'
assert a.detalhes_cartoes['total'].get() == '9 dias de feira'
assert a.detalhes_cartoes['dinheiro'].get() == '44,5% do período'
assert [a.abas.tab(i, 'text') for i in range(3)] == ['Vendas', 'Análises', 'Finanças']
a.abas.select(1)
a.janela.update()
assert a.painel_analises.winfo_viewable()
c = a.painel_analises.comparador
a.painel_analises.abas.select(1)
a.janela.update()
c.seletor_a.tipo.set('Mês');c.seletor_a.ano.set('2026');c.seletor_a.mes.set('Janeiro')
c.seletor_b.tipo.set('Mês');c.seletor_b.ano.set('2026');c.seletor_b.mes.set('Fevereiro')
snapshot = a.relatorio_atual
c.comparar()
assert c.ultima_selecao == (('2026-01-01', '2026-01-31'), ('2026-02-01', '2026-02-28'))
assert c.ultima_comparacao['a']['quantidade'] == len(a.listar_vendas('2026-01-01', '2026-01-31'))
assert a.relatorio_atual is snapshot
c.seletor_a.tipo.set('Data');c.seletor_a.inicio.set('02/01/2026')
c.seletor_b.tipo.set('Data');c.seletor_b.inicio.set('04/01/2026')
c.comparar()
assert c.ultima_comparacao['a']['total'] == 50
assert c.ultima_comparacao['b']['total'] == 50
anterior = c.ultima_comparacao
c.seletor_b.inicio.set('31/02/2026');c.comparar()
assert c.ultima_comparacao is anterior
assert 'válida' in c.aviso.get()
c.seletor_a.tipo.set('Fechamento');c.seletor_a.mes.set('Outubro')
c.seletor_b.tipo.set('Intervalo');c.seletor_b.inicio.set('10/10/2026');c.seletor_b.fim.set('09/11/2026')
c.comparar()
assert c.ultima_selecao[0] == c.ultima_selecao[1] == ('2026-10-10', '2026-11-09')
assert c.ultima_comparacao['diferenca'] == 0
a.painel_analises.abas.select(0)
a.janela.update()

assert len(a.painel_analises.pagamentos.get_children()) == 3
assert sum(int(a.painel_analises.semana.item(i, 'values')[1]) for i in a.painel_analises.semana.get_children()) == 9
from ProgramFeira.interface.ajuda import mostrar_ajuda, AJUDAS
for chave in AJUDAS:
    ajuda = mostrar_ajuda(a.janela, chave)
    a.janela.update()
    assert ajuda.winfo_viewable()
    ajuda.destroy()
a.abas.select(0)
a.janela.update()

# Filtro aplicado nos widgets reais.
a.filtro_ano.set('2026')
assert a.aviso_filtros.get()
a.atualizar_tabela()
assert not a.aviso_filtros.get()
a.janela.update()
assert len(a.tabela.get_children()) == 5
assert a.painel_analises.comparador.ultima_selecao[0] == ('2026-10-10', '2026-11-09')
assert a.painel_analises.filtro.get() == 'Ano: 2026'
assert sum(int(a.painel_analises.semana.item(i, 'values')[1]) for i in a.painel_analises.semana.get_children()) == 5
assert a.indicadores_visuais['quantidade'].get() == '5'
# Ordenar não aplica seletores que ainda não foram confirmados.
a.filtro_ano.set('2025')
assert a.painel_analises.aviso.get()
assert a.painel_analises.filtro.get() == 'Ano: 2026'
a.ordenar_tabela('total')
assert a.aviso_filtros.get()
assert len(a.tabela.get_children()) == 5
assert all(v[1].startswith('2026-') for v in a.relatorio_atual['vendas'])
assert a.relatorio_atual['vendas'][0][2] + a.relatorio_atual['vendas'][0][3] + a.relatorio_atual['vendas'][0][4] > 0
arquivo = Path(a.CAMINHO_BANCO).parent / 'relatorio.csv'
with patch.object(a.filedialog, 'asksaveasfilename', return_value=str(arquivo)), patch.object(a.messagebox, 'showinfo'):
    a.exportar_visualizacao('csv')
assert arquivo.exists()
with patch.object(a.filedialog, 'asksaveasfilename', return_value=''), patch.object(a, 'exportar') as writer:
    a.exportar_visualizacao('csv')
    writer.assert_not_called()
# Layout em janela menor mantém tabela e filtros acessíveis.
a.janela.geometry('980x700')
a.janela.update()
assert a.layout_colunas == 3
assert a.tabela.winfo_height() > 70
assert a.filtro_ano_combobox.winfo_viewable()
assert a.painel_filtros.winfo_rooty() == a.area_tabela.winfo_rooty()
assert a.painel_filtros.winfo_rootx() > a.area_tabela.winfo_rootx()
assert a.botao_editar.winfo_rooty() > a.tabela.winfo_rooty() + a.tabela.winfo_height()
assert a.barra_tabela.winfo_rootx() == a.tabela.winfo_rootx()
assert a.botao_aplicar_filtros.winfo_rooty() + a.botao_aplicar_filtros.winfo_height() < a.painel_filtros.winfo_rooty() + a.painel_filtros.winfo_height()
a.canvas_filtros.event_generate('<MouseWheel>', delta=-120)
a.janela.update()
assert a.canvas_filtros.yview()[0] > 0
a.canvas_filtros.yview_moveto(0)


a.limpar_filtros()
# Duplicidade recusada mantém o formulário aberto e não altera o banco.
a.nova_venda()
a.entrada_ano.set('2026')
a.entrada_mes.set('Janeiro')
a.atualizar_dias()
a.entrada_dia.set('2')
with patch.object(a.messagebox, 'askyesno', return_value=False):
    a.cadastrar()
assert len(a.tabela.get_children()) == 9
assert a.formulario.state() == 'normal'
a.cancelar_edicao()
# Cadastro pelo formulário real, seguido de edição e exclusão.
a.nova_venda()
a.janela.update()
assert a.formulario.state() == 'normal'
a.entrada_ano.set('2026')
a.entrada_mes.set('Outubro')
a.atualizar_dias()
a.entrada_dia.set('21')
a.entrada_dinheiro.insert(0, '125,50')
a.entrada_pix.insert(0, '24,50')
with patch.object(a.messagebox, 'showinfo'):
    a.cadastrar()
a.janela.update()
assert a.formulario.state() == 'withdrawn'
assert len(a.tabela.get_children()) == 10
v = a.buscar_venda_por_data('2026-10-21')
assert v[2:]==(125.5, 24.5, 0)
item = next(i for i in a.tabela.get_children() if int(a.tabela.item(i, 'values')[0]) == v[0])
a.tabela.selection_set(item)
a.janela.update()
assert str(a.botao_editar['state']) == 'normal'
a.botao_editar.invoke()
a.janela.update()
assert a.venda_em_edicao == v[0]
assert a.formulario.state() == 'normal'
a.entrada_pix.delete(0, 'end')
a.entrada_pix.insert(0, '30,00')
with patch.object(a.messagebox, 'showinfo'):
    a.cadastrar()
assert a.buscar_venda_por_id(v[0])[3] == 30
item = next(i for i in a.tabela.get_children() if int(a.tabela.item(i, 'values')[0]) == v[0])
a.tabela.selection_set(item)
with patch.object(a.messagebox, 'askyesno', return_value=True), patch.object(a.messagebox, 'showinfo'):
    a.excluir_venda_selecionada()
assert a.buscar_venda_por_id(v[0]) is None
assert len(a.tabela.get_children()) == 9
# Fecha e reabre formulário, com dias zerados permitidos.
a.nova_venda()
a.cancelar_edicao()
assert a.formulario.state() == 'withdrawn'
# Finanças tem consulta e formulários próprios, preservando o histórico de vendas.
a.abas.select(2)
a.janela.update()
f = a.painel_financeiro
f.tipo.set('Fechamento'); f.referencia.set('01/10/2026'); f.consultar()
assert (f.inicio, f.fim) == ('2026-10-10', '2026-11-09')
snapshot = a.relatorio_atual
popup = f.formulario('despesa')
corpo = popup.winfo_children()[0]
def campo(linha, texto):
    widget = corpo.grid_slaves(row=linha, column=1)[0]
    widget.set(texto) if hasattr(widget, 'set') else (widget.delete(0, 'end'), widget.insert(0, texto))
campo(0, '15/10/2026'); campo(1, 'Conta de água'); campo(2, '123,45')
corpo.grid_slaves(row=7, column=1)[0].invoke()
a.janela.update()
assert len(f.tabela.get_children()) == 1
assert f.valores['despesas'].get() == 'R$ 123,45'
assert a.relatorio_atual is snapshot
f.tabela.selection_set(f.tabela.get_children()[0])
popup = f.formulario('despesa', next(iter(f.registros.values())))
corpo = popup.winfo_children()[0]
campo(2, '120,00'); corpo.grid_slaves(row=7, column=1)[0].invoke()
assert f.valores['despesas'].get() == 'R$ 120,00'
popup = f.formulario_anual()
corpo = popup.winfo_children()[0]
campo(0, '2025'); campo(1, '01/01/2025'); campo(2, '31/12/2025'); campo(3, '210,25')
corpo.grid_slaves(row=7, column=1)[0].invoke()
f.tipo.set('Ano'); f.referencia.set('01/01/2025'); f.consultar()
assert f.valores['taxas'].get() == 'R$ 210,25'
f.tipo.set('Mês'); f.referencia.set('01/10/2025'); f.consultar()
assert 'provisório' in f.aviso.get()
assert f.valores['taxas'].get() == 'R$ 0,00'
a.alternar_tema(); a.janela.update()
assert f.winfo_viewable()
a.janela.geometry('980x700'); a.janela.update()
assert f.tabela.winfo_viewable()
assert f.tabela.winfo_height() > 30
a.abas.select(0); a.janela.update()
assert a.area_cartoes.winfo_viewable()
assert a.analises.winfo_viewable()
assert str(a.botao_exportar.cget('text')) == 'Exportar relatório'
assert len(a.listar_vendas()) == 9
# Conexão online roda fora do loop gráfico e não transfere o SQLite.
from ProgramFeira.nuvem import Sessao, carregar_config as carregar_nuvem
import time
popup = a.conexao_nuvem.configurar()
a.conexao_nuvem.automatico.set(False)
assert a.conexao_nuvem.configurar() is popup
campos = a.conexao_nuvem.campos
for nome, valor in {'url': 'https://projeto-ficticio.supabase.co', 'chave': 'sb_publishable_apenas_teste', 'email': 'teste@example.invalid', 'senha': 'senha-ficticia'}.items():
    campos[nome].insert(0, valor)
with patch('ProgramFeira.nuvem.ClienteNuvem.entrar', return_value=Sessao('11111111-1111-4111-8111-111111111111', 'teste@example.invalid', 'token-ficticio')) as login:
    a.conexao_nuvem.botao_entrar.invoke()
    assert campos['senha'].get() == ''
    assert a.conexao_nuvem.ocupado
    assert str(campos['email'].cget('state')) == 'disabled'
    prazo = time.monotonic() + 5
    while a.conexao_nuvem.ocupado and time.monotonic() < prazo:
        a.janela.update()
        time.sleep(0.01)
    assert not a.conexao_nuvem.ocupado
    login.assert_called_once_with('teste@example.invalid', 'senha-ficticia')
assert a.conexao_nuvem.sessao.email == 'teste@example.invalid'
assert 'Nenhum registro foi transferido' in a.conexao_nuvem.status.get()
assert carregar_nuvem(a.CAMINHO_BANCO.parent)['url'] == 'https://projeto-ficticio.supabase.co'
assert len(a.listar_vendas()) == 9
assert 'senha-ficticia' not in (a.CAMINHO_BANCO.parent / 'nuvem.json').read_text()
# Conferência real cria backup; somente a resposta do serviço é simulada.
import copy
def resposta_migracao(sessao, dados, aplicar):
    return dict(aplicado=aplicar, novos={t: len(dados[t]) for t in dados}, dados=copy.deepcopy(dados) if aplicar else {t: [] for t in dados})
def aguardar_nuvem():
    prazo = time.monotonic() + 5
    while a.conexao_nuvem.ocupado and time.monotonic() < prazo:
        a.janela.update()
        time.sleep(0.01)
    assert not a.conexao_nuvem.ocupado
with patch('ProgramFeira.nuvem.ClienteNuvem.migrar', side_effect=resposta_migracao) as rpc:
    a.conexao_nuvem.botao_conferir.invoke()
    aguardar_nuvem()
    assert a.conexao_nuvem.preparacao is not None, a.conexao_nuvem.status.get()
    assert a.conexao_nuvem.preparacao['relatorio']['resumo']['registros']['vendas'] == 9
    assert Path(a.conexao_nuvem.preparacao['relatorio']['backup']).exists()
    with patch.object(a.messagebox, 'askyesno', return_value=False):
        a.conexao_nuvem.botao_transferir.invoke()
    assert rpc.call_count == 1
    with patch.object(a.messagebox, 'askyesno', return_value=True):
        a.conexao_nuvem.botao_transferir.invoke()
        aguardar_nuvem()
    assert rpc.call_count == 2
    assert 'concluída e validada' in a.conexao_nuvem.status.get()
    assert a.conexao_nuvem.preparacao is None
assert len(a.listar_vendas()) == 9
# Vínculo e recebimento passam pelo botão real; o servidor é fictício.
from test_sincronizacao import Servidor
servidor = Servidor(a.CAMINHO_BANCO)
with patch('ProgramFeira.nuvem.ClienteNuvem.sincronizar', side_effect=servidor.sincronizar):
    a.conexao_nuvem.botao_sincronizar.invoke()
    aguardar_nuvem()
    assert a.conexao_nuvem.vinculado, a.conexao_nuvem.status.get()
    assert str(a.conexao_nuvem.botao_conferir.cget('state')) == 'disabled'
    registro = servidor.venda('2026-01-02')
    servidor.editar('vendas', registro['id'], pix_centavos=321)
    a.conexao_nuvem.botao_sincronizar.invoke()
    aguardar_nuvem()
    assert a.buscar_venda_por_data('2026-01-02')[3] == 3.21
    assert len(a.tabela.get_children()) == 9
    assert 'Sincronização concluída' in a.conexao_nuvem.status.get()
    a.nova_venda()
    chamadas = servidor.chamadas
    a.conexao_nuvem.botao_sincronizar.invoke()
    assert 'formulário' in a.conexao_nuvem.status.get()
    assert servidor.chamadas == chamadas
    a.cancelar_edicao()
# A consulta automática não bloqueia nem aplica dados enquanto há edição.
import threading
from ProgramFeira import sincronizacao as modulo_sync
original_sync = modulo_sync.sincronizar
consultando = threading.Event()
liberar_consulta = threading.Event()
aplicando = threading.Event()
liberar_aplicacao = threading.Event()
primeira_consulta = [True]
def consultar_automatico(sessao, alteracoes=None, operacao_id=None):
    if primeira_consulta[0]:
        primeira_consulta[0] = False
        consultando.set()
        assert liberar_consulta.wait(5)
    return servidor.sincronizar(sessao, alteracoes, operacao_id)
def aplicar_automatico(*args, **kwargs):
    aplicando.set()
    assert liberar_aplicacao.wait(5)
    return original_sync(*args, **kwargs)
def aguardar_evento(evento):
    prazo = time.monotonic() + 5
    while not evento.is_set() and time.monotonic() < prazo:
        a.janela.update()
        time.sleep(.01)
    assert evento.is_set()
a.conexao_nuvem.automatico.set(True)
# Editor financeiro não modal também impede iniciar uma consulta automática.
editor_financeiro = f.formulario('despesa')
a.janela.update()
chamadas = servidor.chamadas
a.conexao_nuvem.agendador._disparar()
assert not a.conexao_nuvem.ocupado
assert servidor.chamadas == chamadas
editor_financeiro.destroy()
a.conexao_nuvem.agendador.parar()
# Filtros pendentes, inclusive texto inválido em Finanças, não bloqueiam a rede.
a.filtro_ano.set('2025')
f.referencia.set('data incompleta')
periodo_aplicado = (f.inicio, f.fim)
a.verificar_automatico()
a.atualizar_apos_sincronizacao()
assert a.filtro_ano.get() == '2025'
assert a.aviso_filtros.get()
assert f.referencia.get() == 'data incompleta'
assert (f.inicio, f.fim) == periodo_aplicado
a.conexao_nuvem.agendador.parar()
a.conexao_nuvem.fechar()
servidor.editar('vendas', registro['id'], pix_centavos=555)
with patch('ProgramFeira.nuvem.ClienteNuvem.sincronizar', side_effect=consultar_automatico):
    a.conexao_nuvem.agendador._disparar()
    aguardar_evento(consultando)
    assert not a.conexao_nuvem.bloqueando_edicao
    a.nova_venda()
    a.entrada_pix.insert(0,'99,99')
    liberar_consulta.set()
    aguardar_nuvem()
    assert a.formulario.state() == 'normal'
    assert a.entrada_pix.get() == '99,99'
    assert a.buscar_venda_por_data('2026-01-02')[3] == 3.21
    a.cancelar_edicao()
    a.conexao_nuvem.agendador.parar()
    with patch.object(modulo_sync, 'sincronizar', side_effect=aplicar_automatico):
        a.conexao_nuvem.agendador._disparar()
        aguardar_evento(aplicando)
        assert a.conexao_nuvem.bloqueando_edicao
        a.nova_venda()
        assert a.formulario.state() == 'withdrawn'
        liberar_aplicacao.set()
        aguardar_nuvem()
    assert not a.conexao_nuvem.bloqueando_edicao
    assert a.buscar_venda_por_data('2026-01-02')[3] == 5.55
    assert a.filtro_ano.get() == '2025'
    assert a.aviso_filtros.get()
    assert f.referencia.get() == 'data incompleta'
    assert (f.inicio, f.fim) == periodo_aplicado
    a.limpar_filtros()
    f.referencia.set('02/01/2026')
    f.consultar()
    assert 'Automática ativa' in a.conexao_nuvem.resumo.get()
    assert not a.conexao_nuvem.agendador.pausado
    # Salvar no formulário marca pendência e envia sem o botão manual.
    a.nova_venda()
    a.entrada_ano.set('2099'); a.entrada_mes.set('Janeiro'); a.atualizar_dias(); a.entrada_dia.set('2')
    a.entrada_dinheiro.insert(0,'1,00')
    with patch.object(a.messagebox,'showinfo'):
        a.cadastrar()
    assert 'aguardando envio' in a.conexao_nuvem.resumo.get()
    assert a.conexao_nuvem.agendador.tarefa is not None
    a.conexao_nuvem.agendador.parar()
    a.conexao_nuvem.agendador._disparar()
    aguardar_nuvem()
    assert servidor.venda('2099-01-02')['dinheiro_centavos'] == 100
    venda_teste = a.buscar_venda_por_data('2099-01-02')
    item = next(i for i in a.tabela.get_children() if int(a.tabela.item(i,'values')[0]) == venda_teste[0])
    a.tabela.selection_set(item); a.janela.update()
    with patch.object(a.messagebox,'askyesno',return_value=True), patch.object(a.messagebox,'showinfo'):
        a.excluir_venda_selecionada()
    assert 'aguardando envio' in a.conexao_nuvem.resumo.get()
    a.conexao_nuvem.agendador.parar()
    a.conexao_nuvem.agendador._disparar()
    aguardar_nuvem()
    assert len(servidor.dados['vendas']) == 9
    # Outra abertura recupera a sessão sem formulário/login. O relógio avança
    # três consultas consecutivas, sem pressionar Sincronizar ou Verificar.
    from test_automacao_nuvem import Relogio
    sessao_salva = a.conexao_nuvem.sessao
    a.conexao_nuvem.configurar()
    with patch('ProgramFeira.sessao_windows.remover') as remover_sessao:
        a.conexao_nuvem.sair()
        remover_sessao.assert_called_once()
    a.conexao_nuvem.fechar()
    with patch('ProgramFeira.sessao_windows.carregar', return_value=sessao_salva), patch('ProgramFeira.nuvem.ClienteNuvem.entrar') as login_desnecessario:
        a.conexao_nuvem.restaurar_sessao()
        login_desnecessario.assert_not_called()
    assert a.conexao_nuvem.sessao == sessao_salva
    assert a.conexao_nuvem.agendador.tarefa is not None
    a.conexao_nuvem.agendador.parar()
    relogio = Relogio()
    a.conexao_nuvem.agendador.relogio = relogio
    a.conexao_nuvem.agendador.ativar()
    for indice in range(3):
        servidor.editar('vendas', registro['id'], pix_centavos=600 + indice)
        assert relogio.disparar() == (2000 if indice == 0 else 60000)
        aguardar_nuvem()
        assert a.buscar_venda_por_data('2026-01-02')[3] == (600 + indice) / 100
        assert not a.conexao_nuvem.agendador.pausado
        assert len(relogio.tarefas) == 1
    # Mesmo sem mudanças, continua agendando e recebe a alteração posterior.
    assert relogio.disparar() == 60000
    aguardar_nuvem()
    assert 'Nenhuma alteração' in a.conexao_nuvem.status.get()
    servidor.editar('vendas', registro['id'], pix_centavos=603)
    assert relogio.disparar() == 60000
    aguardar_nuvem()
    assert a.buscar_venda_por_data('2026-01-02')[3] == 6.03
    a.conexao_nuvem.agendador.parar()
    a.conexao_nuvem.agendador.relogio = a.janela
    # Uma exceção ao redesenhar não deixa o agendador preso em execução.
    a.conexao_nuvem.agendador.executando = True
    with patch.object(a.conexao_nuvem, 'ao_sincronizar', side_effect=ValueError('falha gráfica simulada')):
        try:
            a.conexao_nuvem._concluiu_sincronizacao(sessao_salva,
                dict(enviadas=0, recebidas=1, registros={'vendas': 9}, backup=None), automatico=True)
        except ValueError:
            pass
        else:
            raise AssertionError('O erro gráfico deveria ser reportado ao chamador')
    assert not a.conexao_nuvem.agendador.executando
    assert a.conexao_nuvem.agendador.tarefa is not None
    # Conflito pausa sem caixas de diálogo nem sobrescrita.
    a.atualizar_venda(a.buscar_venda_por_data('2026-01-02')[0], '2026-01-02', 1, 6, 0)
    servidor.editar('vendas', registro['id'], pix_centavos=777)
    a.conexao_nuvem.agendador.parar()
    a.conexao_nuvem.agendador._disparar()
    aguardar_nuvem()
    assert a.conexao_nuvem.agendador.pausado
    assert 'Conflitos' in a.conexao_nuvem.status.get()
    assert a.buscar_venda_por_data('2026-01-02')[3] == 6
    assert not a.conexao_nuvem.bloqueando_edicao
# A revisão mostra valores do PC e da nuvem e aplica a escolha explícita.
popup = a.conexao_nuvem.configurar()
with patch('ProgramFeira.nuvem.ClienteNuvem.sincronizar', side_effect=servidor.sincronizar):
    a.conexao_nuvem.botao_conflitos.invoke()
    aguardar_nuvem()
    revisao = a.conexao_nuvem.revisao_popup
    assert a.conexao_nuvem.agendador.pausado
    revisao.destroy()  # Cancelar não aplica escolhas nem reativa uma sincronização em conflito.
    assert a.buscar_venda_por_data('2026-01-02')[3] == 6
    assert a.conexao_nuvem.agendador.pausado
    a.conexao_nuvem.botao_conflitos.invoke()
    aguardar_nuvem()
    revisao = a.conexao_nuvem.revisao_popup
    assert '6,00' in revisao.textos['pc'].get('1.0','end')
    assert '7,77' in revisao.textos['nuvem'].get('1.0','end')
    revisao.usar_nuvem.invoke()
    with patch.object(a.messagebox, 'askyesno', return_value=True):
        revisao.botao_aplicar.invoke()
    aguardar_nuvem()
    assert a.buscar_venda_por_data('2026-01-02')[3] == 7.77
    assert not a.conexao_nuvem.agendador.pausado
    a.conexao_nuvem.botao_conflitos.invoke()
    aguardar_nuvem()
    assert 'Nenhum conflito' in a.conexao_nuvem.status.get()
    assert not a.conexao_nuvem.agendador.pausado
    assert a.conexao_nuvem.agendador.tarefa is not None
# Teste do backup pela ação da interface, com dados isolados.
from ProgramFeira.database.armazenamento import criar_backup as copiar_backup
copia = copiar_backup(a.CAMINHO_BANCO)
with patch.object(a.filedialog, 'askopenfilename', return_value=str(copia)), patch.object(a.messagebox, 'showinfo') as aviso:
    a.testar_copia()
    assert aviso.call_args.args[0] == 'Backup verificado'
    assert 'Nenhum dado do programa foi alterado' in aviso.call_args.args[1]
a.conexao_nuvem.botao_sair.invoke()
assert a.conexao_nuvem.sessao is None
a.conexao_nuvem.fechar()
assert not errors, errors
a.janela.destroy()
'''
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, 'PROGRAMFEIRA_DATA_DIR': folder}
            result = subprocess.run([sys.executable, '-c', script], cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
