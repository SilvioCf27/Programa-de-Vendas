"""Ícones vetoriais originais, rasterizados em memória sem dependências extras."""
import base64
import math
import tkinter as tk
from tkinter import ttk
from ProgramFeira.interface.acabamento import _png, _rgb

TRACOS = {
    'configuracoes': [[(9, 2), (15, 2), (16, 5), (19, 5), (22, 10), (20, 12), (22, 14), (19, 19), (16, 19), (15, 22), (9, 22), (8, 19), (5, 19), (2, 14), (4, 12), (2, 10), (5, 5), (8, 5), (9, 2)]],
    'baixo': [[(6, 9), (12, 15), (18, 9)]],
    'mais': [[(12, 4), (12, 20)], [(4, 12), (20, 12)]],
    'editar': [[(4, 17), (16, 5), (20, 9), (8, 21), (3, 22), (4, 17)], [(14, 7), (18, 11)]],
    'excluir': [[(5, 6), (19, 6)], [(9, 6), (9, 3), (15, 3), (15, 6)], [(7, 9), (8, 21), (16, 21), (17, 9)], [(10, 10), (10, 18)], [(14, 10), (14, 18)]],
    'filtro': [[(3, 4), (21, 4), (14, 12), (14, 20), (10, 18), (10, 12), (3, 4)]],
    'exportar': [[(12, 3), (12, 15)], [(7, 10), (12, 15), (17, 10)], [(4, 16), (4, 21), (20, 21), (20, 16)]],
    'quantidade': [[(4, 6), (20, 6), (20, 21), (4, 21), (4, 6)], [(4, 11), (20, 11)], [(8, 3), (8, 8)], [(16, 3), (16, 8)], [(8, 15), (10, 15)], [(14, 15), (16, 15)]],
    'media': [[(3, 19), (9, 13), (13, 16), (21, 5)], [(15, 5), (21, 5), (21, 11)]],
    'total': [[(5, 20), (5, 12)], [(12, 20), (12, 7)], [(19, 20), (19, 3)]],
    'dinheiro': [[(3, 6), (21, 6), (21, 18), (3, 18), (3, 6)], [(7, 10), (7, 14)], [(17, 10), (17, 14)], [(11, 9), (14, 9), (14, 15), (11, 15), (11, 9)]],
    'pix': [[(3, 12), (8, 7), (12, 11), (16, 7), (21, 12), (16, 17), (12, 13), (8, 17), (3, 12)], [(9, 5), (12, 2), (15, 5)], [(9, 19), (12, 22), (15, 19)]],
    'cartao': [[(3, 5), (21, 5), (21, 19), (3, 19), (3, 5)], [(3, 10), (21, 10)], [(7, 15), (11, 15)]],
    'comparar': [[(3, 7), (20, 7), (16, 3)], [(21, 17), (4, 17), (8, 21)]],
    'tema': [[(12, 2), (12, 4)], [(12, 20), (12, 22)], [(2, 12), (4, 12)], [(20, 12), (22, 12)], [(5, 5), (7, 7)], [(17, 17), (19, 19)], [(5, 19), (7, 17)], [(17, 7), (19, 5)]],
    'marca': [[(3, 14), (7, 6), (22, 6), (26, 14)], [(3, 14), (26, 14)], [(5, 15), (5, 29), (24, 29), (24, 15)], [(5, 23), (24, 23)], [(10, 6), (8, 14)], [(18, 6), (20, 14)], [(14, 6), (14, 14)]],
}


def _distancia(x, y, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((x - a[0]) * vx + (y - a[1]) * vy) / (vx * vx + vy * vy)))
    return math.hypot(x - a[0] - t * vx, y - a[1] - t * vy)


def imagem_icone(root, nome, cor, tamanho=18):
    if not hasattr(root, '_icones'):
        root._icones = {}
    chave = (nome, cor, tamanho)
    if chave in root._icones:
        return root._icones[chave]
    escala = 36 if nome == 'marca' else 24
    segmentos = [(a, b, min(a[0], b[0]) - 1, min(a[1], b[1]) - 1, max(a[0], b[0]) + 1, max(a[1], b[1]) + 1) for traco in TRACOS[nome] for a, b in zip(traco, traco[1:])]
    pixels = []
    rgb = _rgb(cor)
    for y in range(tamanho):
        for x in range(tamanho):
            cobertos = 0
            for dy in (1/6, 0.5, 5/6):
                for dx in (1/6, 0.5, 5/6):
                    px, py = (x + dx) * escala / tamanho, (y + dy) * escala / tamanho
                    linha = any(x0 <= px <= x1 and y0 <= py <= y1 and _distancia(px, py, a, b) <= 0.95 for a, b, x0, y0, x1, y1 in segmentos)
                    if nome == 'marca':
                        # Lua crescente: diferença entre dois discos.
                        linha |= math.hypot(px - 29, py - 9) <= 5 and math.hypot(px - 31.5, py - 7) > 4.7
                    if nome == 'configuracoes':
                        linha |= abs(math.hypot(px - 12, py - 12) - 3.5) <= 0.9
                    if nome == 'tema':
                        linha |= abs(math.hypot(px - 12, py - 12) - 5) <= 0.9
                    cobertos += bool(linha)
            pixels.extend((*rgb, round(255 * cobertos / 9)))
    imagem = tk.PhotoImage(master=root, data=base64.b64encode(_png(tamanho, tamanho, pixels)))
    root._icones[chave] = imagem
    return imagem


def aplicar_icones(widget, cores):
    nome = getattr(widget, 'icone_nome', None)
    if nome is None and not isinstance(widget, (ttk.Button, ttk.Menubutton)):
        return
    if nome is None:
        try:
            texto = str(widget.cget('text'))
        except tk.TclError:
            texto = ''
        nome = {'+ Nova venda': 'mais', 'Nova venda': 'mais', 'Aplicar filtros': 'filtro',
                'Editar venda': 'editar', 'Excluir': 'excluir', 'Exportar relatório': 'exportar', 'Exportar vendas': 'exportar',
                'Tema claro': 'tema', 'Tema escuro': 'tema', 'Comparar A e B': 'comparar'}.get(texto)
    if nome:
        root = widget.winfo_toplevel()
        cor = '#FFFFFF' if 'Primary' in str(widget.cget('style')) else cores['vermelho' if nome == 'excluir' else 'azul']
        normal = imagem_icone(root, nome, cor, getattr(widget, 'icone_tamanho', 16))
        disabled = imagem_icone(root, nome, cores['disabled'], getattr(widget, 'icone_tamanho', 16))
        widget.configure(image=(normal, 'disabled', disabled), compound='left')


def rotulo_icone(parent, nome, cores, tamanho=18, estilo='Surface.TLabel'):
    from tkinter import ttk
    label = ttk.Label(parent, style=estilo)
    label.icone_nome = nome
    label.icone_tamanho = tamanho
    aplicar_icones(label, cores)
    return label
