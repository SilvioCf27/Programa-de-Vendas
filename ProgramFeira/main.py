# Permite executar tanto como módulo quanto pelo botão Run do editor.
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import sqlite3
from ProgramFeira.resumos import calcular_indicadores, periodo_anterior, descrever_comparacao, moeda
from ProgramFeira.exportacao import montar_relatorio, exportar
from ProgramFeira.interface.fontes import registrar_fontes
from ProgramFeira.interface.painel_backup import BackupDrive
from ProgramFeira.interface.painel_nuvem import ConexaoNuvem
from ProgramFeira.nuvem import ErroNuvem
from ProgramFeira.versao import VERSAO
from ProgramFeira.diagnostico import registrar as registrar_erro
from ProgramFeira.interface.icones import rotulo_icone
from ProgramFeira.interface.visual import aplicar_tema, ordenar_vendas, CORES
from ProgramFeira.preferencias import carregar_tema, salvar_tema
from ProgramFeira.interface.ajuda import botao_ajuda, rotulo_com_ajuda
from ProgramFeira.interface.analises import PainelAnalises
from ProgramFeira.interface.painel_financeiro import PainelFinanceiro
from ProgramFeira.financeiro import inicializar as inicializar_financeiro
from ProgramFeira.comparacao import fechamento_do_mes
import calendar
from datetime import date, timedelta
from decimal import Decimal

from ProgramFeira.database.banco import (
    listar_vendas,
    listar_anos_vendas,
    obter_resumo_vendas,
    converter_data_salva,
    cadastrar_venda,
    buscar_venda_por_data,
    buscar_venda_por_id,
    criar_tabela,
    excluir_venda,
    atualizar_venda,
    criar_backup,
    restaurar_backup,
    CAMINHO_BANCO
    )

criar_tabela()
inicializar_financeiro()

relatorio_atual = None
filtros_aplicados = None
ordenacao_coluna = "data"
ordenacao_decrescente = True

venda_em_edicao = None

# Dia final do período de fechamento. Altere somente este número se necessário.
# Use um valor de 1 a 27. Com 9, o período vai do dia 10 ao dia 9 do mês seguinte.
DIA_FECHAMENTO = 9

MESES = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12
}

DIAS_SEMANA = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo"
)


def obter_anos_disponiveis():
    anos = set(listar_anos_vendas())
    anos.add(date.today().year)
    anos.add(date.today().year + 1)

    return sorted(anos)


ANOS = obter_anos_disponiveis()


def converter_valor(texto):
    texto = texto.strip()

    # Campo vazio = zero
    if not texto:
        return 0.0

    # Permite formatos como:
    # 125,50
    # 125.50
    # 1.250,50
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")

    return float(texto)


def assinatura_filtros():
    return (filtro_tipo.get(), filtro_ano.get(), filtro_mes.get(), filtro_fechamento.get(),
            tuple(d for d, variavel in filtros_dias_semana.items() if variavel.get()))


def atualizar_aviso_filtros(*args):
    pendentes = filtros_aplicados is not None and assinatura_filtros() != filtros_aplicados
    aviso_filtros.set('Filtros alterados — clique em Aplicar.' if pendentes else '')
    painel_analises.aviso.set('Há filtros pendentes na aba Vendas. Estas análises ainda mostram a seleção aplicada.' if pendentes else '')


def sincronizar_filtros(origem=None):
    global sincronizando_filtros
    if sincronizando_filtros:
        return
    sincronizando_filtros = True
    try:
        if origem == 'ano' and filtro_ano.get() == 'Todos os anos':
            filtro_mes.set('Todos os meses')
            filtro_fechamento.set(False)
        if origem == 'mes' and filtro_mes.get() == 'Todos os meses':
            filtro_fechamento.set(False)
        if filtro_fechamento.get() and filtro_mes.get() == 'Todos os meses':
            filtro_mes.set(next(nome for nome, numero in MESES.items() if numero == date.today().month))
        if filtro_mes.get() != 'Todos os meses' and filtro_ano.get() == 'Todos os anos':
            filtro_ano.set(str(date.today().year))
        if filtro_fechamento.get():
            filtro_tipo.set('Período de fechamento')
        elif filtro_mes.get() != 'Todos os meses':
            filtro_tipo.set('Mês')
        elif filtro_ano.get() != 'Todos os anos':
            filtro_tipo.set('Ano')
        else:
            filtro_tipo.set('Todas as vendas')
    finally:
        sincronizando_filtros = False
    atualizar_aviso_filtros()


def selecionar_ano_filtro(event=None):
    sincronizar_filtros('ano')


def selecionar_mes_filtro(event=None):
    sincronizar_filtros('mes')


def obter_filtros():
    sincronizar_filtros()
    data_inicial = None
    data_final = None
    tipo = filtro_tipo.get()

    if tipo != "Todas as vendas":
        ano = int(filtro_ano.get())
        if tipo == "Ano":
            data_inicial = date(ano, 1, 1)
            data_final = date(ano, 12, 31)
        else:
            mes = MESES[filtro_mes.get()]
            if tipo == "Mês":
                data_inicial = date(ano, mes, 1)
                data_final = date(ano, mes, calendar.monthrange(ano, mes)[1])
            elif tipo == "Período de fechamento":
                inicio, fim = fechamento_do_mes(ano, mes, DIA_FECHAMENTO)
                data_inicial, data_final = date.fromisoformat(inicio), date.fromisoformat(fim)

    dias_semana = [
        numero for numero, variavel in filtros_dias_semana.items()
        if variavel.get()
    ]
    return (
        data_inicial.isoformat() if data_inicial else None,
        data_final.isoformat() if data_final else None,
        dias_semana
    )


def atualizar_tabela():
    global relatorio_atual, filtros_aplicados
    # Apaga os registros que já aparecem
    for item in tabela.get_children():
        tabela.delete(item)

    # Busca os registros no banco
    data_inicial, data_final, dias_semana = obter_filtros()
    vendas = ordenar_vendas(listar_vendas(data_inicial, data_final, dias_semana), ordenacao_coluna, ordenacao_decrescente)

    # Coloca cada venda na tabela
    for indice_linha, venda in enumerate(vendas):
        id_venda, data, dinheiro, pix, cartao = venda

        data_convertida = converter_data_salva(data)

        if data_convertida:
            data_exibicao = data_convertida.strftime("%d/%m/%Y")
            dia_semana = DIAS_SEMANA[data_convertida.weekday()]
        else:
            data_exibicao = data
            dia_semana = "Data inválida"

        tabela.insert(
            "",
            tk.END,
            values=(
                id_venda,
                data_exibicao,
                dia_semana,
                moeda(Decimal(str(dinheiro))),
                moeda(Decimal(str(pix))),
                moeda(Decimal(str(cartao))),
                moeda(sum(Decimal(str(v)) for v in (dinheiro, pix, cartao)))
            ),
            tags=("par" if indice_linha % 2 == 0 else "impar",)
        )

    atualizar_resumo(data_inicial, data_final, dias_semana, len(vendas), vendas)
    texto_filtro_atual.set(descrever_filtro_atual(data_inicial, data_final, dias_semana))
    painel_analises.atualizar(vendas, texto_filtro_atual.get(), resumo_comparacao.get())
    relatorio_atual = montar_relatorio(vendas, texto_filtro_atual.get(), resumo_comparacao.get())
    atualizar_botoes_selecao()
    atualizar_cabecalhos()
    ajustar_larguras_colunas()
    filtros_aplicados = assinatura_filtros()
    atualizar_aviso_filtros()


def atualizar_resumo(data_inicial, data_final, dias_semana, quantidade_vendas, vendas=None):
    dinheiro, pix, cartao = obter_resumo_vendas(
        data_inicial,
        data_final,
        dias_semana
    )
    total = dinheiro + pix + cartao

    resumo_dinheiro.set(f"Dinheiro: R$ {dinheiro:.2f}")
    resumo_pix.set(f"Pix: R$ {pix:.2f}")
    resumo_cartao.set(f"Cartão: R$ {cartao:.2f}")
    resumo_total.set(f"Total geral: R$ {total:.2f}")
    resumo_quantidade.set(f"Vendas encontradas: {quantidade_vendas}")
    if vendas is None:
        vendas = listar_vendas(data_inicial, data_final, dias_semana)
    indicadores = calcular_indicadores(vendas)
    valores_cartoes = {'total': moeda(indicadores['total']), 'quantidade': str(indicadores['quantidade']),
                      'media': moeda(indicadores['media']), 'dinheiro': moeda(Decimal(str(dinheiro))),
                      'pix': moeda(Decimal(str(pix))), 'cartao': moeda(Decimal(str(cartao)))}
    for chave, valor in valores_cartoes.items():
        indicadores_visuais[chave].set(valor)
    resumo_media.set(f"Média por dia de feira: {moeda(indicadores['media'])} (inclui dias zerados)")
    partes = indicadores['participacoes']
    if indicadores['total']:
        texto = " | ".join(f"{nome}: {valor:.1f}%".replace('.', ',') for nome, valor in zip(("Dinheiro", "Pix", "Cartão"), partes))
        resumo_participacao.set("Participação: " + texto)
    else:
        resumo_participacao.set("Participação: indisponível (total zero)")
    periodo = periodo_anterior(filtro_tipo.get(), data_inicial, data_final)
    anteriores = calcular_indicadores(listar_vendas(*periodo, dias_semana)) if periodo else None
    resumo_comparacao.set(descrever_comparacao(indicadores, anteriores, periodo))



def descrever_filtro_atual(data_inicial, data_final, dias_semana):
    if filtro_tipo.get() == "Ano":
        descricao = f"Ano: {filtro_ano.get()}"
    elif filtro_tipo.get() == "Mês":
        descricao = f"Mês: {filtro_mes.get()} de {filtro_ano.get()}"
    elif filtro_tipo.get() == "Período de fechamento":
        inicio = date.fromisoformat(data_inicial).strftime("%d/%m/%Y")
        fim = date.fromisoformat(data_final).strftime("%d/%m/%Y")
        descricao = f"Fechamento: {inicio} até {fim}"
    else:
        descricao = "Todas as vendas"

    if dias_semana:
        nomes_dias = ", ".join(DIAS_SEMANA[dia] for dia in dias_semana)
        descricao += f" | Dias: {nomes_dias}"

    return descricao


def limpar_filtros():
    filtro_fechamento.set(False)
    filtro_mes.set('Todos os meses')
    filtro_ano.set('Todos os anos')
    for variavel in filtros_dias_semana.values():
        variavel.set(False)
    sincronizar_filtros()
    atualizar_tabela()


def atualizar_anos_disponiveis():
    global ANOS

    ANOS = obter_anos_disponiveis()
    entrada_ano["values"] = ANOS
    filtro_ano_combobox["values"] = ("Todos os anos", *ANOS)

    if entrada_ano.get() not in map(str, ANOS):
        entrada_ano.set(str(ANOS[-1]))

    if filtro_ano.get() != "Todos os anos" and filtro_ano.get() not in map(str, ANOS):
        filtro_ano.set("Todos os anos")


def cadastrar():
    if conexao_nuvem.bloqueando_edicao:
        return
    global venda_em_edicao

    try:
        dinheiro = converter_valor(entrada_dinheiro.get())
        pix = converter_valor(entrada_pix.get())
        cartao = converter_valor(entrada_cartao.get())

        data = converter_data()

        if dinheiro < 0 or pix < 0 or cartao < 0:
            messagebox.showerror(
                "Valores inválidos",
                "Os valores de dinheiro, Pix e cartão não podem ser negativos."
            )
            return

        # Atualiza o registro selecionado sem duplicar sua data.
        if venda_em_edicao is not None:
            venda_existente = buscar_venda_por_data(data)

            if venda_existente and venda_existente[0] != venda_em_edicao:
                messagebox.showerror(
                    "Data já cadastrada",
                    "Já existe uma venda registrada para essa data."
                )
                return

            atualizar_venda(
                venda_em_edicao,
                data,
                dinheiro,
                pix,
                cartao
            )

            messagebox.showinfo(
                "Sucesso",
                "Venda alterada com sucesso!"
            )

            venda_em_edicao = None

            botao_cadastrar.config(text="Cadastrar venda")
            botao_cancelar_edicao.pack_forget()

            atualizar_anos_disponiveis()

            entrada_dinheiro.delete(0, tk.END)
            entrada_pix.delete(0, tk.END)
            entrada_cartao.delete(0, tk.END)

            atualizar_tabela()
            cancelar_edicao()
            conexao_nuvem.notificar_alteracao()
            return

        #  Venda existente recebe o valor inserido da data, pelo utilizador e verifica se já consta no sistema.
        venda_existente = buscar_venda_por_data(data)

        if venda_existente:
            resposta = messagebox.askyesno(
                "Venda já cadastrada",
                "Já existe uma venda registrada para este dia.\n\n"
                "Deseja alterá-la?"
            )

            if resposta is True:
                preencher_venda(venda_existente)
                return

            elif resposta is False:
                return

            else:
                return

        # Continuação do cadastro normal
        cadastrar_venda(data, dinheiro, pix, cartao)

        messagebox.showinfo(
            "Sucesso",
            "Venda cadastrada com sucesso!"
        )

        atualizar_anos_disponiveis()

        entrada_dinheiro.delete(0, tk.END)
        entrada_pix.delete(0, tk.END)
        entrada_cartao.delete(0, tk.END)

        atualizar_tabela()
        cancelar_edicao()
        conexao_nuvem.notificar_alteracao()

    except ValueError:
        messagebox.showerror(
            "Erro",
            "Verifique os dados informados."
        )
        return



def converter_data():
    dia = int(entrada_dia.get())
    mes = MESES[entrada_mes.get()]
    ano = int(entrada_ano.get())

    data = date(ano, mes, dia)

    return data.isoformat()

def preencher_venda(venda):
    global venda_em_edicao

    id_venda, data, dinheiro, pix, cartao = venda

    venda_em_edicao = id_venda

    data_convertida = converter_data_salva(data)

    if data_convertida:
        entrada_ano.set(str(data_convertida.year))
        entrada_mes.set(next(nome for nome, numero in MESES.items() if numero == data_convertida.month))
        atualizar_dias()
        entrada_dia.set(str(data_convertida.day))

    entrada_dinheiro.delete(0, tk.END)
    entrada_dinheiro.insert(0, f"{dinheiro:.2f}")

    entrada_pix.delete(0, tk.END)
    entrada_pix.insert(0, f"{pix:.2f}")

    entrada_cartao.delete(0, tk.END)
    entrada_cartao.insert(0, f"{cartao:.2f}")

    botao_cadastrar.config(text="Salvar alteração")
    mostrar_formulario()


def editar_venda_selecionada(event=None):
    if conexao_nuvem.bloqueando_edicao:
        return
    if event is not None and event.type == tk.EventType.ButtonPress and tabela.identify_region(event.x, event.y) not in ('cell', 'tree'):
        return
    selecao = tabela.selection()

    if not selecao:
        return

    valores = tabela.item(selecao[0], "values")
    id_venda = valores[0]
    venda = buscar_venda_por_id(id_venda)

    if venda:
        preencher_venda(venda)


def excluir_venda_selecionada():
    if conexao_nuvem.bloqueando_edicao:
        return
    selecao = tabela.selection()

    if not selecao:
        messagebox.showwarning(
            "Nenhuma venda selecionada",
            "Selecione uma venda na tabela antes de excluí-la."
        )
        return

    valores = tabela.item(selecao[0], "values")
    id_venda, data = valores[0], valores[1]

    confirmar = messagebox.askyesno(
        "Confirmar exclusão",
        f"Deseja excluir permanentemente a venda do dia {data}?"
    )

    if not confirmar:
        return

    if venda_em_edicao == int(id_venda):
        cancelar_edicao()

    excluir_venda(id_venda)
    atualizar_tabela()

    messagebox.showinfo("Sucesso", "Venda excluída com sucesso!")
    conexao_nuvem.notificar_alteracao()

def cancelar_edicao():
    global venda_em_edicao

    venda_em_edicao = None

    entrada_dinheiro.delete(0, tk.END)
    entrada_pix.delete(0, tk.END)
    entrada_cartao.delete(0, tk.END)

    botao_cadastrar.config(text="Cadastrar venda")

    botao_cancelar_edicao.pack_forget()
    formulario.grab_release()
    formulario.withdraw()


#############################################################################


def fazer_backup_manual():
    try:
        caminho = criar_backup()
        messagebox.showinfo("Backup criado", f"Cópia verificada salva em:\n{caminho}")
    except (OSError, sqlite3.Error, ValueError) as erro:
        messagebox.showerror("Backup não realizado", str(erro))


def testar_copia():
    arquivo = filedialog.askopenfilename(title='Verificar integridade do backup', filetypes=[('Banco SQLite', '*.db')])
    if not arquivo:
        return
    from ProgramFeira.recuperacao import testar_recuperacao
    try:
        resultado = testar_recuperacao(arquivo)
        tabelas = resultado['tabelas']
        messagebox.showinfo('Backup verificado',
            f"Backup verificado. Nenhum dado do programa foi alterado.\n\n"
            f"Vendas: {tabelas.get('vendas', 0)}\nLançamentos financeiros: {tabelas.get('financeiro_lancamentos', 0)}\n"
            f"Ajustes anuais: {tabelas.get('financeiro_taxas_anuais', 0)}\n\n"
            'Estrutura, conteúdo de todas as tabelas e cópia anterior conferidos. A sessão de login e a configuração do Drive não fazem parte deste backup.')
    except (ValueError, OSError, sqlite3.Error, RuntimeError) as erro:
        messagebox.showerror('Backup não verificado', str(erro))


def restaurar_copia():
    if conexao_nuvem.bloqueando_edicao:
        return
    arquivo = filedialog.askopenfilename(title="Selecionar backup", filetypes=[("Banco SQLite", "*.db")])
    if not arquivo:
        return
    if not messagebox.askyesno("Restaurar backup", "Substituir os dados atuais pelos dados desse backup?\nUma cópia dos dados atuais será preservada antes da restauração.\nFeche outras instâncias do programa antes de continuar."):
        return
    try:
        anterior = restaurar_backup(arquivo)
        inicializar_financeiro()
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as erro:
        messagebox.showerror("Restauração não realizada", str(erro))
        return
    cancelar_edicao()
    atualizar_anos_disponiveis()
    limpar_filtros()
    messagebox.showinfo("Backup restaurado", f"Dados restaurados. Cópia anterior preservada em:\n{anterior}")
    conexao_nuvem.banco_restaurado()


def exportar_visualizacao(formato):
    if relatorio_atual is None:
        return
    extensao = '.' + formato
    caminho = filedialog.asksaveasfilename(
        title="Exportar vendas e resumo", defaultextension=extensao,
        initialfile='vendas-filtradas' + extensao,
        filetypes=[("Excel" if formato == 'xlsx' else "CSV", '*' + extensao)])
    if not caminho:
        return
    try:
        exportar(caminho, relatorio_atual, formato)
    except (OSError, ValueError, RuntimeError) as erro:
        messagebox.showerror("Exportação não realizada", str(erro))
        return
    messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{caminho}\n\nForam exportados os dados da última aplicação dos filtros.")


def mostrar_pasta_dados():
    messagebox.showinfo("Local dos dados", f"Banco ativo:\n{CAMINHO_BANCO}\n\nBackups:\n{CAMINHO_BANCO.parent / 'backups'}")


def atualizar_botoes_selecao(event=None):
    estado = 'normal' if tabela.selection() else 'disabled'
    botao_editar.configure(state=estado)
    botao_excluir_venda.configure(state=estado)


def atualizar_cabecalhos():
    for coluna, titulo in titulos_colunas.items():
        seta = (' ▼' if ordenacao_decrescente else ' ▲') if coluna == ordenacao_coluna else ''
        tabela.heading(coluna, text=titulo + seta)


def ordenar_tabela(coluna):
    global ordenacao_coluna, ordenacao_decrescente, relatorio_atual
    if relatorio_atual is None:
        return
    ordenacao_decrescente = not ordenacao_decrescente if ordenacao_coluna == coluna else coluna in ('total', 'dinheiro', 'pix', 'cartao', 'data')
    ordenacao_coluna = coluna
    vendas = ordenar_vendas(relatorio_atual['vendas'], coluna, ordenacao_decrescente)
    itens = {int(tabela.item(item, 'values')[0]): item for item in tabela.get_children()}
    for indice, venda in enumerate(vendas):
        item = itens[int(venda[0])]
        tabela.move(item, '', indice)
        tabela.item(item, tags=('par' if indice % 2 == 0 else 'impar',))
    relatorio_atual = {**relatorio_atual, 'vendas': tuple(vendas)}
    atualizar_cabecalhos()


def mostrar_formulario():
    formulario.title('Editar venda' if venda_em_edicao is not None else 'Nova venda')
    titulo_formulario.set('Editar venda' if venda_em_edicao is not None else 'Nova venda')
    botao_cancelar_edicao.pack(side='left')
    janela.update_idletasks()
    x = max(0, janela.winfo_rootx() + (janela.winfo_width() - 520) // 2)
    y = max(0, janela.winfo_rooty() + (janela.winfo_height() - 400) // 2)
    formulario.geometry(f'520x400+{x}+{y}')
    formulario.deiconify()
    formulario.transient(janela)
    formulario.grab_set()
    formulario.lift()
    entrada_dinheiro.focus_set()


def nova_venda():
    if conexao_nuvem.bloqueando_edicao:
        return
    cancelar_edicao()
    hoje = date.today()
    entrada_ano.set(str(hoje.year))
    entrada_mes.set(next(nome for nome, numero in MESES.items() if numero == hoje.month))
    atualizar_dias()
    entrada_dia.set(str(hoje.day))
    mostrar_formulario()


def atualizar_dias(event=None):
    mes = MESES[entrada_mes.get()]
    ano = int(entrada_ano.get())
    quantidade = calendar.monthrange(ano, mes)[1]
    entrada_dia['values'] = tuple(range(1, quantidade + 1))
    atual = entrada_dia.get()
    entrada_dia.set(atual if atual.isdigit() and 1 <= int(atual) <= quantidade else '1')


def ajustar_larguras_colunas(event=None):
    fonte = font.nametofont('TkDefaultFont')
    # Medir cada texto uma vez: várias vendas repetem datas, zeros e valores.
    linhas = [tabela.item(item, 'values') for item in tabela.get_children()]
    medidas = {}
    def medir(texto):
        if texto not in medidas:
            medidas[texto] = fonte.measure(texto)
        return medidas[texto]
    for indice, coluna in enumerate(colunas):
        valores = {str(linha[indice]) for linha in linhas}
        largura = max([medir(titulos_colunas[coluna] + ' ▼'), *(medir(v) for v in valores)]) + 26
        tabela.column(coluna, width=max(48, largura), minwidth=48, stretch=False, anchor='center')
    ajustar_area_tabela()


def ajustar_area_tabela(event=None):
    largura = sum(tabela.column(c, 'width') for c in colunas) + scroll_vertical.winfo_reqwidth() + 4
    container_tabela.configure(width=min(largura, max(100, area_tabela.winfo_width() - 28)))


def alternar_tema():
    novo = 'claro' if tema_atual.get() == 'escuro' else 'escuro'
    aplicar_tema(janela, novo)
    tema_atual.set(novo)
    texto_botao_tema.set('Tema claro' if novo == 'escuro' else 'Tema escuro')
    tabela.tag_configure('par', background=CORES['superficie'])
    tabela.tag_configure('impar', background=CORES['alternada'])
    global layout_compacto
    layout_compacto = None
    organizar_cartoes()
    try:
        salvar_tema(CAMINHO_BANCO.parent, novo)
    except OSError as erro:
        messagebox.showwarning('Preferência não salva', f'O tema foi alterado, mas não pôde ser salvo para a próxima abertura.\n{erro}')


registrar_fontes()
janela = tk.Tk()
janela.title(f'Gestão da Feira · {VERSAO} · Controle de vendas')
largura = min(1280, janela.winfo_screenwidth() - 60)
altura = min(900, janela.winfo_screenheight() - 90)
janela.geometry(f'{largura}x{altura}')
janela.minsize(940, 660)
tema_atual = tk.StringVar(value=carregar_tema(CAMINHO_BANCO.parent))
aplicar_tema(janela, tema_atual.get())
janela.columnconfigure(0, weight=1)
janela.rowconfigure(3, weight=1)


def informar_erro_callback(tipo, erro, traceback):
    registrar_erro(erro, CAMINHO_BANCO.parent)
    messagebox.showerror('Operação não concluída', f'Não foi possível concluir a operação.\n{erro}')


janela.report_callback_exception = informar_erro_callback
menu = tk.Menu(janela)
menu_dados = tk.Menu(menu, tearoff=False)
menu_dados.add_command(label='Criar backup agora', command=fazer_backup_manual)
menu_dados.add_command(label='Restaurar backup…', command=restaurar_copia)
menu_dados.add_command(label='Verificar integridade do backup…', command=testar_copia)
menu_dados.add_command(label='Sobre esta versão…', command=lambda: messagebox.showinfo('Gestão da Feira',
    f'Versão {VERSAO}\n\nDados locais: {CAMINHO_BANCO.parent}\nDiagnósticos: {CAMINHO_BANCO.parent / "logs"}\n\nOs registros de diagnóstico não incluem valores financeiros, mensagens do serviço, senha ou tokens.'))

backup_drive = BackupDrive(janela, CAMINHO_BANCO)
menu_dados.add_command(label='Backup no Google Drive…', command=backup_drive.configurar)


def verificar_formulario_sincronizacao():
    if formulario.state() == 'normal':
        raise ErroNuvem('Conclua ou cancele o formulário de venda antes de sincronizar.')
    def janelas_visiveis(widget):
        for filho in widget.winfo_children():
            if isinstance(filho, tk.Toplevel):
                if filho is not conexao_nuvem.popup and not getattr(filho, '_dica_informativa', False) and filho.winfo_viewable():
                    return True
            elif janelas_visiveis(filho):
                return True
        return False
    if janelas_visiveis(janela) or janela.grab_current() not in (None, conexao_nuvem.popup):
        raise ErroNuvem('Conclua ou feche a janela aberta antes de sincronizar.')


def verificar_automatico():
    verificar_formulario_sincronizacao()


controles_bloqueados = []
menus_bloqueados = []


def bloquear_edicao_sincronizacao(bloquear):
    if bloquear:
        def visitar(widget):
            for filho in widget.winfo_children():
                if isinstance(filho, tk.Toplevel):
                    continue
                if isinstance(filho, (ttk.Button, ttk.Menubutton, ttk.Entry, ttk.Combobox, ttk.Checkbutton)):
                    controles_bloqueados.append((filho, 'disabled' in filho.state()))
                    filho.state(['disabled'])
                visitar(filho)
        visitar(janela)
        for i in range((menu_dados.index('end') or 0) + 1):
            if menu_dados.type(i) == 'command':
                menus_bloqueados.append((i, menu_dados.entrycget(i, 'state')))
                menu_dados.entryconfigure(i, state='disabled')
    else:
        for widget, desativado in controles_bloqueados:
            if widget.winfo_exists() and not desativado:
                widget.state(['!disabled'])
        controles_bloqueados.clear()
        for indice, estado in menus_bloqueados:
            menu_dados.entryconfigure(indice, state=estado)
        menus_bloqueados.clear()
        atualizar_botoes_selecao()


def atualizar_apos_sincronizacao():
    global sincronizando_filtros
    # Atualiza os resultados já aplicados sem consumir seleções em preparação.
    pendentes = assinatura_filtros()
    aplicada = filtros_aplicados or pendentes

    def selecionar(assinatura):
        tipo, ano, mes, fechamento, dias = assinatura
        filtro_tipo.set(tipo)
        filtro_ano.set(ano)
        filtro_mes.set(mes)
        filtro_fechamento.set(fechamento)
        for dia, variavel in filtros_dias_semana.items():
            variavel.set(dia in dias)

    sincronizando_filtros = True
    try:
        atualizar_anos_disponiveis()
        selecionar(aplicada)
        atualizar_tabela()
    finally:
        selecionar(pendentes)
        sincronizando_filtros = False
        atualizar_aviso_filtros()
    painel_financeiro.consultar(manter_periodo=True)


conexao_nuvem = ConexaoNuvem(janela, CAMINHO_BANCO.parent,
    ao_sincronizar=atualizar_apos_sincronizacao,
    antes_sincronizar=verificar_formulario_sincronizacao,
    antes_automatico=verificar_automatico,
    bloquear_edicao=bloquear_edicao_sincronizacao)
menu_dados.add_command(label='Conexão com a nuvem…', command=conexao_nuvem.configurar)
menu_dados.add_separator()
menu_dados.add_command(label='Local dos dados', command=mostrar_pasta_dados)
# Os comandos são apresentados na janela Configurações; este menu guarda suas ações.
menu_exportar = tk.Menu(menu, tearoff=False)
menu_exportar.add_command(label='Excel (.xlsx)…', command=lambda: exportar_visualizacao('xlsx'))
menu_exportar.add_command(label='CSV (.csv)…', command=lambda: exportar_visualizacao('csv'))
menu.add_cascade(label='Exportar', menu=menu_exportar)
janela.config(menu=menu)

filtro_tipo = tk.StringVar(value='Todas as vendas')
filtro_mes = tk.StringVar(value='Todos os meses')
filtro_ano = tk.StringVar(value='Todos os anos')
filtro_fechamento = tk.BooleanVar(value=False)
sincronizando_filtros = False
texto_filtro_atual = tk.StringVar()
aviso_filtros = tk.StringVar()
filtros_dias_semana = {d: tk.BooleanVar() for d in range(7)}
resumo_dinheiro = tk.StringVar()
resumo_pix = tk.StringVar()
resumo_cartao = tk.StringVar()
resumo_total = tk.StringVar()
resumo_quantidade = tk.StringVar()
resumo_media = tk.StringVar()
resumo_participacao = tk.StringVar()
resumo_comparacao = tk.StringVar()
indicadores_visuais = {chave: tk.StringVar() for chave in ('total', 'quantidade', 'media', 'dinheiro', 'pix', 'cartao')}

configuracoes = None


def abrir_configuracoes():
    global configuracoes
    if conexao_nuvem.bloqueando_edicao:
        return
    if configuracoes is not None and configuracoes.winfo_exists():
        configuracoes.lift()
        return configuracoes
    from ProgramFeira.interface.configuracoes import Configuracoes
    configuracoes = Configuracoes(janela, menu_dados)
    return configuracoes


# Cabeçalho e ações principais.
cabecalho = ttk.Frame(janela, padding=(24, 18, 24, 12))
cabecalho.grid(row=0, column=0, sticky='ew')
cabecalho.columnconfigure(0, weight=1)
marca = ttk.Frame(cabecalho)
marca.grid(row=0, column=0, rowspan=2, sticky='w')
rotulo_icone(marca, 'marca', CORES, tamanho=58, estilo='TLabel').pack(side='left', padx=(0, 12))
texto_marca = ttk.Frame(marca)
texto_marca.pack(side='left')
ttk.Label(texto_marca, text='Gestão da Feira', style='Title.TLabel').pack(anchor='w')
ttk.Label(texto_marca, text='Suas feiras, seus resultados.', style='Muted.TLabel').pack(anchor='w')
botao_configuracoes = ttk.Button(marca, text='', width=3, command=abrir_configuracoes)
botao_configuracoes.icone_nome = 'configuracoes'
botao_configuracoes.icone_tamanho = 22
botao_configuracoes.pack(side='left', padx=(16, 0))
from ProgramFeira.interface.ajuda import Dica
dica_configuracoes = Dica(botao_configuracoes, 'Configurações: backups, sincronização e informações do programa.')
acoes = ttk.Frame(cabecalho)
acoes.grid(row=0, column=1, rowspan=2, sticky='e')
texto_botao_tema = tk.StringVar(value='Tema claro' if tema_atual.get() == 'escuro' else 'Tema escuro')
ttk.Button(acoes, textvariable=texto_botao_tema, command=alternar_tema).pack(side='left', padx=(0, 10))
botao_exportar = ttk.Menubutton(acoes, text='Exportar relatório', menu=menu_exportar)
botao_exportar.pack(side='left', padx=(0, 10))
ttk.Button(acoes, text='Nova venda', style='Primary.TButton', command=nova_venda).pack(side='left')

# Indicadores se adaptam à largura da janela.
area_cartoes = ttk.Frame(janela)
area_cartoes.grid(row=1, column=0, sticky='ew', padx=24, pady=(0, 10))
cartoes = []
for chave, titulo in [('total', 'TOTAL DO PERÍODO'), ('quantidade', 'DIAS DE FEIRA'), ('media', 'MÉDIA POR DIA'),
                      ('dinheiro', 'DINHEIRO'), ('pix', 'PIX'), ('cartao', 'CARTÃO')]:
    card = ttk.Frame(area_cartoes, style='Card.TFrame', padding=(14, 11))
    linha_titulo = ttk.Frame(card, style='Surface.TFrame')
    linha_titulo.pack(anchor='w')
    rotulo_icone(linha_titulo, chave, CORES, tamanho=16).pack(side='left', padx=(0, 5))
    rotulo_com_ajuda(linha_titulo, titulo, chave, 'CardTitle.TLabel').pack(side='left')
    ttk.Label(card, textvariable=indicadores_visuais[chave], style='Accent.CardValue.TLabel' if chave == 'total' else 'CardValue.TLabel').pack(anchor='w', pady=(5, 0))
    cartoes.append(card)
layout_colunas = None
layout_compacto = None


def organizar_cartoes(event=None):
    global layout_colunas, layout_compacto
    compacto = janela.winfo_height() < 760
    if compacto != layout_compacto:
        layout_compacto = compacto
        familia = font.nametofont('TkDefaultFont').actual('family')
        ttk.Style(janela).configure('CardValue.TLabel', font=(familia, 14 if compacto else 18, 'bold'))
        for card in cartoes:
            card.configure(padding=(12, 7) if compacto else (14, 11))
    colunas = 6 if area_cartoes.winfo_width() >= 1120 else 3
    if colunas == layout_colunas:
        return
    layout_colunas = colunas
    for i in range(6):
        area_cartoes.columnconfigure(i, weight=1 if i < colunas else 0, uniform='cartoes' if i < colunas else '')
    for i, card in enumerate(cartoes):
        card.grid(row=i // colunas, column=i % colunas, sticky='nsew', padx=(0 if i % colunas == 0 else 8, 0), pady=(0, 6))


area_cartoes.bind('<Configure>', organizar_cartoes)
janela.bind('<Configure>', lambda e: organizar_cartoes() if e.widget is janela else None)
organizar_cartoes()

analises = ttk.Frame(janela, style='Panel.TFrame', padding=(14, 8))
analises.grid(row=2, column=0, sticky='ew', padx=24, pady=(0, 10))
label_participacao = ttk.Label(analises, textvariable=resumo_participacao, style='Surface.TLabel')
label_participacao.grid(row=0, column=1, sticky='w', pady=(0, 4))
botao_ajuda(analises, 'participacao').grid(row=0, column=0, sticky='w', padx=(0, 7), pady=(0, 4))
label_comparacao = ttk.Label(analises, textvariable=resumo_comparacao, style='Surface.TLabel', justify='left')
label_comparacao.grid(row=1, column=1, sticky='w')
botao_ajuda(analises, 'comparacao').grid(row=1, column=0, sticky='nw', padx=(0, 7))
analises.columnconfigure(1, weight=1)
analises.bind('<Configure>', lambda e: label_comparacao.configure(wraplength=max(100, e.width - 65)))

# Abas compartilham a mesma seleção aplicada e os indicadores superiores.
abas = ttk.Notebook(janela)
abas.grid(row=3, column=0, sticky='nsew', padx=24)
aba_vendas = ttk.Frame(abas)
aba_vendas.rowconfigure(0, weight=1)
aba_vendas.columnconfigure(0, weight=1)
abas.add(aba_vendas, text='Vendas')
aba_analises = ttk.Frame(abas)
aba_analises.rowconfigure(0, weight=1)
aba_analises.columnconfigure(0, weight=1)
abas.add(aba_analises, text='Análises')
painel_analises = PainelAnalises(aba_analises)
painel_analises.grid(row=0, column=0, sticky='nsew')
painel_financeiro = PainelFinanceiro(abas, ao_alterar=conexao_nuvem.notificar_alteracao)
abas.add(painel_financeiro, text='Finanças')
def alternar_pagina(evento):
    if evento.widget is not abas:
        return
    em_financas = abas.select() == str(painel_financeiro)
    # Finanças tem indicadores próprios: dá espaço à consulta sem misturar totais.
    for bloco in (area_cartoes, analises):
        bloco.grid_remove() if em_financas else bloco.grid()
    botao_exportar.configure(text='Exportar vendas' if em_financas else 'Exportar relatório')
    if em_financas:
        painel_financeiro.consultar()

abas.bind('<<NotebookTabChanged>>', alternar_pagina)

# Área de consulta: histórico à esquerda, filtros em painel lateral.
area_trabalho = ttk.Frame(aba_vendas)
area_trabalho.grid(row=0, column=0, sticky='nsew', pady=(12, 0))
area_trabalho.columnconfigure(0, weight=1)
area_trabalho.rowconfigure(0, weight=1)

painel_filtros = ttk.Frame(area_trabalho, style='Panel.TFrame', padding=8)
painel_filtros.grid(row=0, column=1, sticky='nsew', padx=(12, 0))
painel_filtros.columnconfigure(0, weight=1)
painel_filtros.rowconfigure(0, weight=1)
canvas_filtros = tk.Canvas(painel_filtros, width=272, height=1, background=CORES['superficie'], highlightthickness=0)
canvas_filtros.grid(row=0, column=0, sticky='nsew')
scroll_filtros = ttk.Scrollbar(painel_filtros, orient='vertical', command=canvas_filtros.yview)
scroll_filtros.grid(row=0, column=1, sticky='ns')
canvas_filtros.configure(yscrollcommand=scroll_filtros.set)
frame_filtros = ttk.Frame(canvas_filtros, style='Surface.TFrame', padding=(16, 14))
janela_filtros = canvas_filtros.create_window((0, 0), window=frame_filtros, anchor='nw')
canvas_filtros.bind('<Configure>', lambda e: canvas_filtros.itemconfigure(janela_filtros, width=e.width))
frame_filtros.bind('<Configure>', lambda e: canvas_filtros.configure(scrollregion=canvas_filtros.bbox('all')))
frame_filtros.columnconfigure(0, weight=1)


def rolar_painel_filtros(event):
    if event.widget is canvas_filtros or str(event.widget).startswith(str(frame_filtros)):
        if getattr(event, 'num', None) in (4, 5):
            unidades = -1 if event.num == 4 else 1
        else:
            unidades = -1 if event.delta > 0 else 1
        canvas_filtros.yview_scroll(unidades, 'units')
        return 'break'


janela.bind('<MouseWheel>', rolar_painel_filtros, add='+')
janela.bind('<Button-4>', rolar_painel_filtros, add='+')
janela.bind('<Button-5>', rolar_painel_filtros, add='+')

rotulo_com_ajuda(frame_filtros, 'Filtrar vendas', 'filtros', 'Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 14))
rotulo_com_ajuda(frame_filtros, 'Ano', 'ano').grid(row=1, column=0, sticky='w')
filtro_ano_combobox = ttk.Combobox(frame_filtros, textvariable=filtro_ano, values=('Todos os anos', *ANOS), state='readonly', width=16)
filtro_ano_combobox.grid(row=2, column=0, sticky='ew', pady=(4, 10))
filtro_ano_combobox.bind('<<ComboboxSelected>>', selecionar_ano_filtro)
rotulo_com_ajuda(frame_filtros, 'Mês', 'mes').grid(row=3, column=0, sticky='w')
filtro_mes_combobox = ttk.Combobox(frame_filtros, textvariable=filtro_mes, values=('Todos os meses', *MESES), state='readonly', width=16)
filtro_mes_combobox.grid(row=4, column=0, sticky='ew', pady=(4, 10))
filtro_mes_combobox.bind('<<ComboboxSelected>>', selecionar_mes_filtro)
filtro_ano.trace_add('write', lambda *args: selecionar_ano_filtro())
filtro_mes.trace_add('write', lambda *args: selecionar_mes_filtro())
filtro_fechamento.trace_add('write', lambda *args: sincronizar_filtros('fechamento'))
linha_fechamento = ttk.Frame(frame_filtros, style='Surface.TFrame')
linha_fechamento.grid(row=5, column=0, sticky='w', pady=(0, 10))
ttk.Checkbutton(linha_fechamento, text='Fechamento 10 → 9', variable=filtro_fechamento).pack(side='left')
botao_ajuda(linha_fechamento, 'fechamento').pack(side='left', padx=(5, 0))
rotulo_com_ajuda(frame_filtros, 'Dias da semana', 'dias').grid(row=6, column=0, sticky='w')
linha_dias = ttk.Frame(frame_filtros, style='Surface.TFrame')
linha_dias.grid(row=7, column=0, sticky='ew', pady=(5, 8))
for d, nome in enumerate(('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')):
    ttk.Checkbutton(linha_dias, text=nome, variable=filtros_dias_semana[d]).grid(row=d // 2, column=d % 2, sticky='w', padx=(0, 10))
    filtros_dias_semana[d].trace_add('write', atualizar_aviso_filtros)
acoes_filtros = ttk.Frame(painel_filtros, style='Surface.TFrame', padding=(16, 8, 16, 14))
acoes_filtros.grid(row=1, column=0, columnspan=2, sticky='ew')
acoes_filtros.columnconfigure(0, weight=1)
label_aviso = ttk.Label(acoes_filtros, textvariable=aviso_filtros, style='Aviso.TLabel', wraplength=230, justify='left')
label_aviso.grid(row=0, column=0, sticky='ew', pady=(0, 8))
botao_aplicar_filtros = ttk.Button(acoes_filtros, text='Aplicar filtros', style='Primary.TButton', command=atualizar_tabela)
botao_aplicar_filtros.grid(row=1, column=0, sticky='ew', pady=(0, 7))
ttk.Button(acoes_filtros, text='Limpar filtros', command=limpar_filtros).grid(row=2, column=0, sticky='ew')

# Histórico e ações sobre o registro selecionado.
area_tabela = ttk.Frame(area_trabalho, style='Panel.TFrame', padding=(14, 14, 14, 10))
area_tabela.grid(row=0, column=0, sticky='nsew')
area_tabela.columnconfigure(0, weight=1)
area_tabela.rowconfigure(2, weight=1)
barra_tabela = ttk.Frame(area_tabela, style='Surface.TFrame')
barra_tabela.grid(row=0, column=0, sticky='ew', pady=(0, 8))
rotulo_com_ajuda(barra_tabela, 'Histórico de vendas', 'historico', 'Section.TLabel').pack(side='left')
label_filtro = ttk.Label(area_tabela, textvariable=texto_filtro_atual, style='Filtro.TLabel', justify='left')
label_filtro.grid(row=1, column=0, sticky='ew', pady=(0, 10))
acoes_historico = ttk.Frame(area_tabela, style='Surface.TFrame')
acoes_historico.grid(row=3, column=0, sticky='w', pady=(10, 0))
botao_editar = ttk.Button(acoes_historico, text='Editar venda', command=editar_venda_selecionada, state='disabled')
botao_editar.pack(side='left', padx=(0, 8))
botao_excluir_venda = ttk.Button(acoes_historico, text='Excluir', style='Danger.TButton', command=excluir_venda_selecionada, state='disabled')
botao_excluir_venda.pack(side='left')
container_tabela = ttk.Frame(area_tabela, style='Surface.TFrame')
container_tabela.grid(row=2, column=0, sticky='nsw')
container_tabela.grid_propagate(False)
container_tabela.columnconfigure(0, weight=1)
container_tabela.rowconfigure(0, weight=1)
colunas = ('id', 'data', 'dia_semana', 'dinheiro', 'pix', 'cartao', 'total')
titulos_colunas = dict(zip(colunas, ('ID', 'Data', 'Dia da semana', 'Dinheiro', 'Pix', 'Cartão', 'Total')))
tabela = ttk.Treeview(container_tabela, columns=colunas, show='headings', selectmode='browse', height=7)
tabela.grid(row=0, column=0, sticky='nsew')
for coluna, largura_coluna in zip(colunas, (55, 110, 160, 130, 130, 130, 150)):
    tabela.column(coluna, width=largura_coluna, minwidth=48, stretch=False, anchor='center')
    tabela.heading(coluna, anchor='center', command=lambda c=coluna: ordenar_tabela(c))
scroll_vertical = ttk.Scrollbar(container_tabela, orient='vertical', command=tabela.yview)
scroll_vertical.grid(row=0, column=1, sticky='ns')
scroll_horizontal = ttk.Scrollbar(container_tabela, orient='horizontal', command=tabela.xview)
scroll_horizontal.grid(row=1, column=0, sticky='ew')
tabela.configure(yscrollcommand=scroll_vertical.set, xscrollcommand=scroll_horizontal.set)
area_tabela.bind('<Configure>', lambda e: (ajustar_area_tabela(), label_filtro.configure(wraplength=max(100, e.width - 28))))
tabela.tag_configure('par', background=CORES['superficie'])
tabela.tag_configure('impar', background=CORES['alternada'])
tabela.bind('<<TreeviewSelect>>', atualizar_botoes_selecao)
tabela.bind('<Double-1>', editar_venda_selecionada)
tabela.bind('<Return>', editar_venda_selecionada)
rodape = ttk.Frame(janela, padding=(24, 9))
rodape.grid(row=4, column=0, sticky='ew')
ttk.Label(rodape, text='Clique nos títulos para ordenar · Duplo clique para editar', style='Muted.TLabel').pack(side='left')
ttk.Label(rodape, text='Dias zerados incluídos · Fechamento: 10 → 9', style='Muted.TLabel').pack(side='right')

# Formulário separado: usa as mesmas ações de cadastro e edição.
formulario = tk.Toplevel(janela)
formulario.withdraw()
formulario.geometry('520x400')
formulario.resizable(False, False)
formulario.configure(background=CORES['fundo'])
formulario.protocol('WM_DELETE_WINDOW', cancelar_edicao)
formulario.bind('<Escape>', lambda e: cancelar_edicao())
titulo_formulario = tk.StringVar(value='Nova venda')
corpo_formulario = ttk.Frame(formulario, padding=24)
corpo_formulario.pack(fill='both', expand=True)
ttk.Label(corpo_formulario, textvariable=titulo_formulario, style='Title.TLabel').pack(anchor='w')
ttk.Label(corpo_formulario, text='Informe a data e os valores recebidos.', style='Muted.TLabel').pack(anchor='w', pady=(2, 18))
ttk.Label(corpo_formulario, text='Data da feira').pack(anchor='w')
frame_data = ttk.Frame(corpo_formulario)
frame_data.pack(fill='x', pady=(5, 16))
entrada_dia = ttk.Combobox(frame_data, width=5, state='readonly')
entrada_mes = ttk.Combobox(frame_data, width=14, state='readonly', values=tuple(MESES))
entrada_ano = ttk.Combobox(frame_data, width=7, state='readonly', values=ANOS)
for campo in (entrada_dia, entrada_mes, entrada_ano):
    campo.pack(side='left', padx=(0, 8))
entrada_mes.bind('<<ComboboxSelected>>', atualizar_dias)
entrada_ano.bind('<<ComboboxSelected>>', atualizar_dias)
entrada_ano.set(str(date.today().year))
entrada_mes.set(next(nome for nome, numero in MESES.items() if numero == date.today().month))
atualizar_dias()
entrada_dia.set(str(date.today().day))
linha_valores = ttk.Frame(corpo_formulario)
linha_valores.pack(fill='x')
campos_valores = []
for i, nome in enumerate(('Dinheiro (R$)', 'Pix (R$)', 'Cartão (R$)')):
    linha_valores.columnconfigure(i, weight=1)
    ttk.Label(linha_valores, text=nome).grid(row=0, column=i, sticky='w', padx=(0, 10))
    campo = ttk.Entry(linha_valores, width=13)
    campo.grid(row=1, column=i, sticky='ew', padx=(0, 10), pady=(5, 0))
    campos_valores.append(campo)
entrada_dinheiro, entrada_pix, entrada_cartao = campos_valores
ttk.Label(corpo_formulario, text='Ex.: 125,50 · Campos vazios valem zero.', style='Muted.TLabel').pack(anchor='w', pady=(12, 0))
ttk.Label(corpo_formulario, text='Cada data pode ter apenas um registro.', style='Muted.TLabel').pack(anchor='w', pady=(4, 20))
acoes_formulario = ttk.Frame(corpo_formulario)
acoes_formulario.pack(side='bottom', fill='x')
botao_cadastrar = ttk.Button(acoes_formulario, text='Cadastrar venda', style='Primary.TButton', command=cadastrar)
botao_cadastrar.pack(side='right')
botao_cancelar_edicao = ttk.Button(acoes_formulario, text='Cancelar', command=cancelar_edicao)
botao_cancelar_edicao.pack(side='left')

rodape_nuvem = ttk.Label(janela, textvariable=conexao_nuvem.resumo, style='Muted.TLabel', padding=(24, 6))
rodape_nuvem.grid(row=4, column=0, sticky='ew')
rodape_nuvem.bind('<Button-1>', lambda e: conexao_nuvem.configurar())
aplicar_tema(janela, tema_atual.get())
layout_compacto = None
organizar_cartoes()
atualizar_tabela()
janela.mainloop()
