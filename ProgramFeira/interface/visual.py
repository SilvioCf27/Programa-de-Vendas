"""Tema ttk e ordenação de registros sem alterar dados ou regras financeiras."""
import tkinter as tk
from tkinter import ttk, font
from ProgramFeira.interface.acabamento import instalar_elementos
from ProgramFeira.interface.icones import aplicar_icones, imagem_icone
from decimal import Decimal
from datetime import date
from ProgramFeira.database.banco import converter_data_salva

PALETAS = {
    'claro': {
        'fundo': '#F3F5F9', 'superficie': '#FFFFFF', 'texto': '#17243B',
        'muted': '#64748B', 'borda': '#DFE5EE', 'azul': '#2459D3',
        'azul_hover': '#1C46AC', 'verde': '#147D65', 'vermelho': '#B33F4B',
        'hover': '#E8EEF9', 'disabled': '#94A3B8', 'cabecalho': '#EAF0F8',
        'selecionado': '#DDE8FF', 'texto_selecionado': '#153575', 'alternada': '#F4F7FC',
        'aviso': '#94600B', 'botao': '#2459D3', 'botao_hover': '#1C46AC', 'scroll': '#CBD5E1',
    },
    'escuro': {
        'fundo': '#0F1929', 'superficie': '#1B2A40', 'texto': '#E9F0FC',
        'muted': '#AABBD2', 'borda': '#31465F', 'azul': '#8BB5FF',
        'azul_hover': '#2D5DB5', 'verde': '#6ED4AC', 'vermelho': '#FF9CA8',
        'hover': '#2C3D55', 'disabled': '#8292A8', 'cabecalho': '#26364D',
        'selecionado': '#304E7B', 'texto_selecionado': '#FFFFFF', 'alternada': '#233148',
        'aviso': '#F3C97E', 'botao': '#2468DB', 'botao_hover': '#347DF1', 'scroll': '#53657D',
    },
}
# Os nomes internos antigos são mantidos para preservar as preferências existentes.
NOMES_TEMAS = {'escuro': 'Noite', 'claro': 'Claro', 'grafite': 'Grafite', 'areia': 'Areia'}
PALETAS['grafite'] = {
    'fundo': '#171A20', 'superficie': '#232830', 'texto': '#F0F2F5',
    'muted': '#B5BDC9', 'borda': '#414953', 'azul': '#9CCFC7',
    'azul_hover': '#32776C', 'verde': '#90D9B5', 'vermelho': '#FFA5AD',
    'hover': '#333D46', 'disabled': '#89939F', 'cabecalho': '#2D343D',
    'selecionado': '#34544F', 'texto_selecionado': '#FFFFFF', 'alternada': '#292F38',
    'aviso': '#F2CA87', 'botao': '#286E63', 'botao_hover': '#348276', 'scroll': '#59636E',
}
PALETAS['areia'] = {
    'fundo': '#201B17', 'superficie': '#2D2620', 'texto': '#F5EBDD',
    'muted': '#C8B6A3', 'borda': '#554638', 'azul': '#E8BA83',
    'azul_hover': '#A7733E', 'verde': '#A9CF9D', 'vermelho': '#F4A49B',
    'hover': '#403329', 'disabled': '#A18B76', 'cabecalho': '#382E25',
    'selecionado': '#63482F', 'texto_selecionado': '#FFF4E5', 'alternada': '#332A22',
    'aviso': '#EBC681', 'botao': '#986131', 'botao_hover': '#AD7340', 'scroll': '#79624E',
}
PALETAS['aurora'] = {
    'fundo': '#191625', 'superficie': '#262137', 'texto': '#F3EFFB',
    'muted': '#BCB2D2', 'borda': '#4B405F', 'azul': '#C5ACFA',
    'azul_hover': '#8654C2', 'verde': '#91D4BD', 'vermelho': '#FFABB9',
    'hover': '#39304D', 'disabled': '#9D8EB4', 'cabecalho': '#302940',
    'selecionado': '#53406F', 'texto_selecionado': '#FFFFFF', 'alternada': '#2C263C',
    'aviso': '#EFCC92', 'botao': '#7548AC', 'botao_hover': '#895DC1', 'scroll': '#716085',
}
NOMES_TEMAS['aurora'] = 'Aurora'
CORES = dict(PALETAS['claro'])


def misturar(base, destaque, proporcao):
    canais = lambda cor: [int(cor[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(a * (1 - proporcao) + b * proporcao):02x}'
                         for a, b in zip(canais(base), canais(destaque)))


def cores_indicadores(cores):
    escuro = sum(int(cores['fundo'][i:i + 2], 16) for i in (1, 3, 5)) < 380
    acentos = (('#42D5AD', '#66B7F2', '#63D7BA', '#F2BD59', '#A999FF', '#64B5F8') if escuro
               else ('#10765B', '#2462A4', '#187661', '#996116', '#7252B2', '#2462A4'))
    return {chave: (cor, misturar(cores['superficie'], cor, .10 if escuro else .06),
                   misturar(cores['borda'], cor, .48))
            for chave, cor in zip(('total', 'quantidade', 'media', 'dinheiro', 'pix', 'cartao'), acentos)}


def aplicar_tema(janela, tema='claro'):
    CORES.clear()
    CORES.update(PALETAS[tema])
    familias = {nome.lower(): nome for nome in font.families(janela)}
    familia = next((familias[nome.lower()] for nome in ('Feira Text', 'Inter', 'Segoe UI', 'DejaVu Sans', 'Liberation Sans', 'Nimbus Sans L', 'Helvetica') if nome.lower() in familias), 'TkDefaultFont')
    titulo = next((familias[nome.lower()] for nome in ('Feira Display', 'Plus Jakarta Sans', 'Segoe UI', familia) if nome.lower() in familias), familia)
    estilo = ttk.Style(janela)
    estilo.theme_use('clam')
    janela.configure(background=CORES['fundo'])
    for nome in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont'):
        font.nametofont(nome, root=janela).configure(family=familia, size=10)
    estilo.configure('.', font=(familia, 10), foreground=CORES['texto'], background=CORES['fundo'])
    estilo.configure('TFrame', background=CORES['fundo'])
    estilo.configure('Surface.TFrame', background=CORES['superficie'])
    estilo.configure('TLabel', background=CORES['fundo'], foreground=CORES['texto'])
    estilo.configure('Muted.TLabel', foreground=CORES['muted'])
    estilo.configure('Title.TLabel', font=(titulo, 26, 'bold'))
    estilo.configure('Section.TLabel', font=(familia, 13, 'bold'), background=CORES['superficie'])
    estilo.configure('Surface.TLabel', background=CORES['superficie'])
    estilo.configure('CardTitle.TLabel', background=CORES['superficie'], foreground=CORES['muted'], font=(familia, 9))
    estilo.configure('CardValue.TLabel', background=CORES['superficie'], font=(familia, 18, 'bold'))
    estilo.configure('Accent.CardValue.TLabel', foreground=CORES['azul'])
    estilo.configure('TButton', padding=(9, 5), background=CORES['superficie'], bordercolor=CORES['borda'], relief='flat')
    estilo.map('TButton', background=[('active', CORES['hover'])], foreground=[('disabled', CORES['disabled'])])
    estilo.configure('Primary.TButton', background=CORES['fundo'], foreground='white', bordercolor=CORES['botao'])
    estilo.map('Primary.TButton', background=[('active', CORES['botao_hover']), ('pressed', CORES['botao_hover'])], foreground=[('disabled', '#CBD5E1'), ('!disabled', 'white')])
    estilo.configure('Danger.TButton', foreground=CORES['vermelho'])
    estilo.configure('TMenubutton', padding=(9, 5), background=CORES['superficie'], bordercolor=CORES['borda'], relief='flat')
    estilo.map('TMenubutton', background=[('active', CORES['hover'])])
    estilo.configure('TEntry', padding=(6, 4), fieldbackground=CORES['superficie'], bordercolor=CORES['borda'])
    estilo.configure('TCombobox', padding=(6, 4), fieldbackground=CORES['superficie'], background=CORES['superficie'], bordercolor=CORES['borda'], arrowsize=14)
    estilo.map('TCombobox', fieldbackground=[('readonly', CORES['superficie'])], selectbackground=[('readonly', CORES['superficie'])], selectforeground=[('readonly', CORES['texto'])])
    estilo.configure('TCheckbutton', background=CORES['superficie'], padding=(0, 3))
    estilo.map('TCheckbutton', background=[('active', CORES['superficie'])])
    estilo.configure('Treeview', background=CORES['superficie'], fieldbackground=CORES['superficie'], rowheight=36,
                     borderwidth=0, font=(familia, 10))
    estilo.configure('Treeview.Heading', background=CORES['cabecalho'], foreground=CORES['muted'],
                     padding=(10, 12), relief='flat', font=(familia, 10, 'bold'))
    estilo.map('Treeview', background=[('selected', CORES['selecionado'])], foreground=[('selected', CORES['texto_selecionado'])])
    estilo.map('Treeview.Heading', background=[('active', CORES['hover'])])
    estilo.configure('Vertical.TScrollbar', background=CORES['scroll'], troughcolor=CORES['fundo'], borderwidth=0, arrowsize=12)
    for nome in ('TCombobox', 'TEntry', 'Treeview', 'TMenubutton', 'Vertical.TScrollbar', 'Horizontal.TScrollbar'):
        estilo.configure(nome, bordercolor=CORES['borda'], lightcolor=CORES['borda'], darkcolor=CORES['borda'], arrowcolor=CORES['texto'])
    for nome in ('Vertical.TScrollbar', 'Horizontal.TScrollbar'):
        estilo.configure(nome, background=CORES['scroll'], troughcolor=CORES['superficie'], borderwidth=0)
        estilo.map(nome, background=[('active', CORES['muted'])])
    # Trilho discreto, sem as setas e os relevos do tema nativo.
    for orientacao, direcao in (('Vertical', 'ns'), ('Horizontal', 'ew')):
        estilo.layout(orientacao + '.TScrollbar', [
            (orientacao + '.Scrollbar.trough', {'sticky': direcao, 'children': [
                (orientacao + '.Scrollbar.thumb', {'sticky': direcao, 'expand': '1'})]})])
        estilo.configure(orientacao + '.TScrollbar', width=8, arrowsize=8,
                         gripcount=0, relief='flat', borderwidth=0)
    estilo.configure('Aviso.TLabel', background=CORES['superficie'], foreground=CORES['aviso'])
    estilo.configure('Ajuda.TButton', padding=(3, 1), foreground=CORES['azul'], font=(familia, 9, 'bold'))
    estilo.configure('TNotebook', background=CORES['fundo'], borderwidth=0, bordercolor=CORES['fundo'], lightcolor=CORES['fundo'], darkcolor=CORES['fundo'])
    estilo.configure('TNotebook.Tab', font=(familia, 10, 'bold'), padding=(24, 8), background=CORES['superficie'], foreground=CORES['muted'])
    estilo.map('TNotebook.Tab', background=[('selected', CORES['selecionado']), ('active', CORES['hover'])], foreground=[('selected', CORES['texto_selecionado']), ('!selected', CORES['muted'])])
    estilo.configure('Filtro.TLabel', background=CORES['superficie'], foreground=CORES['azul'])
    estilo.configure('TEntry', foreground=CORES['texto'], insertcolor=CORES['texto'])
    estilo.configure('TCheckbutton', foreground=CORES['texto'], indicatorbackground=CORES['superficie'], indicatorforeground=CORES['texto'])
    estilo.map('TCheckbutton', indicatorbackground=[('selected', CORES['botao']), ('!selected', CORES['superficie'])], indicatorforeground=[('selected', 'white')])
    estilo.map('TCombobox', foreground=[('readonly', CORES['texto'])], selectforeground=[('readonly', CORES['texto'])])
    for option, valor in (('background', CORES['superficie']), ('foreground', CORES['texto']),
                          ('selectBackground', CORES['selecionado']), ('selectForeground', CORES['texto_selecionado'])):
        janela.option_add('*TCombobox*Listbox.' + option, valor)
    estilo.configure('Horizontal.TProgressbar', background=CORES['botao'],
                     troughcolor=CORES['alternada'], borderwidth=0, thickness=8)
    for chave, (cor, fundo, borda) in cores_indicadores(CORES).items():
        estilo.configure(f'{chave}.Indicador.TFrame', background=fundo)
        for nome, tamanho, peso, texto in (
                ('Titulo', 8, 'bold', cor), ('Valor', 24, 'bold', cor if chave == 'total' else CORES['texto']),
                ('Detalhe', 10, 'normal', CORES['muted']), ('Icone', 10, 'normal', cor)):
            estilo.configure(f'{chave}.{nome}.TLabel', background=fundo,
                             foreground=texto, font=(familia, tamanho, peso))
    instalar_elementos(janela, estilo, CORES, tema)
    # Atualiza também popups já abertos anteriormente.
    def visitar(widget):
        cores_widget = CORES
        indicador = getattr(widget, 'indicador', None)
        if indicador:
            cor, fundo, _ = cores_indicadores(CORES)[indicador]
            cores_widget = dict(CORES, azul=cor, superficie=fundo)
        aplicar_icones(widget, cores_widget)
        if isinstance(widget, (ttk.Button, ttk.Menubutton, ttk.Entry, ttk.Combobox)):
            base = getattr(widget, '_estilo_base', widget.cget('style') or widget.winfo_class())
            widget._estilo_base = base
            pai = widget.master
            estilo_pai = str(pai.cget('style')) if isinstance(pai, ttk.Frame) else ''
            superficie = estilo_pai in ('Surface.TFrame', 'Panel.TFrame', 'Card.TFrame') or estilo_pai.endswith('.Indicador.TFrame')
            cor = cores_widget['superficie'] if superficie else CORES['fundo']
            derivado = ((indicador + '.') if indicador else '') + ('Superficie.' if superficie else 'Pagina.') + base
            estilo.configure(derivado, background=cor)
            estilo.map(derivado, background=[('disabled', cor), ('!disabled', cor)])
            widget.configure(style=derivado)
        if isinstance(widget, tk.Canvas):
            widget.configure(background=CORES['superficie'])
            if hasattr(widget, 'atualizar_aparencia'):
                widget.atualizar_aparencia()
        if isinstance(widget, (tk.Menu, tk.Toplevel)):
            widget.configure(background=CORES['superficie'] if isinstance(widget, tk.Menu) else CORES['fundo'])
        if isinstance(widget, tk.Menu):
            widget.configure(foreground=CORES['texto'], activebackground=CORES['selecionado'], activeforeground=CORES['texto_selecionado'])
        if isinstance(widget, ttk.Combobox):
            try:
                popup = widget.tk.call('ttk::combobox::PopdownWindow', widget)
                widget.tk.call(str(popup) + '.f.l', 'configure', '-background', CORES['superficie'], '-foreground', CORES['texto'], '-selectbackground', CORES['selecionado'], '-selectforeground', CORES['texto_selecionado'])
            except tk.TclError:
                pass  # O menu do seletor pode ser nativo da plataforma.
        if isinstance(widget, ttk.Notebook):
            widget._icones_abas = []
            for aba in widget.tabs():
                nome = {'Vendas': 'total', 'Análises': 'media', 'Finanças': 'dinheiro'}.get(widget.tab(aba, 'text'))
                if nome:
                    icone = imagem_icone(janela, nome, CORES['azul'], 20)
                    widget._icones_abas.append(icone)
                    widget.tab(aba, image=icone, compound='left')
        for filho in widget.winfo_children():
            visitar(filho)
    visitar(janela)
    janela._marca_app = imagem_icone(janela, 'marca', CORES['azul'], 64)
    janela.iconphoto(True, janela._marca_app)
    return estilo


def ordenar_vendas(vendas, coluna, decrescente=False):
    indices = {'id': 0, 'dinheiro': 2, 'pix': 3, 'cartao': 4}

    def chave(venda):
        if coluna == 'data':
            return converter_data_salva(venda[1]) or date.min
        if coluna == 'dia_semana':
            dia = converter_data_salva(venda[1])
            return dia.weekday() if dia else -1
        if coluna == 'total':
            return sum(Decimal(str(v)) for v in venda[2:5])
        if coluna == 'id':
            return int(venda[0])
        return Decimal(str(venda[indices[coluna]]))

    return sorted(vendas, key=chave, reverse=decrescente)
