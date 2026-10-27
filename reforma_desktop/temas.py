"""Paletas compatíveis com o núcleo, sem importar widgets Tk nem ler fontes no runtime."""
from PySide6 import QtGui as G
from tema_noturno import C
from reforma_desktop.paletas_compat import PALETAS
from noturno_demo import Fundo, FaixaSemana

BASE = dict(C)
NOMES = {'escuro': 'Noite', 'claro': 'Claro', 'grafite': 'Grafite', 'areia': 'Areia', 'aurora': 'Aurora'}


def cores(tema):
    if tema not in NOMES:
        raise ValueError('Tema inválido.')
    if tema == 'escuro':
        return legibilidade(dict(BASE))  # Preserva a identidade Noturno aprovada como Noite.
    p = PALETAS[tema]
    claro = tema == 'claro'
    c = dict(BASE)
    c.update(bg=p['fundo'], side=p['superficie'], panel=p['superficie'], field=p['cabecalho'], border=p['borda'],
             text=p['texto'], muted=p['muted'], discrete=p['disabled'], green=p['verde'], turquoise=p['verde'],
             blue=p['azul'], cyan=p['azul'], yellow=p['aviso'], red=p['vermelho'],
             purple='#7252B2' if claro else p['azul'] if tema == 'aurora' else BASE['purple'],
             alternate=p['alternada'], panel_gradient=p['superficie'], hover=p['hover'], selected=p['selecionado'],
             primary_start=p['selecionado'] if claro else p['botao'], primary_end=p['selecionado'] if claro else p['botao'],
             primary_hover=p['hover'] if claro else p['botao_hover'], query=p['selecionado'] if claro else p['botao'],
             query_border=p['borda'], danger='#FFE6EA' if claro else BASE['danger'],
             danger_border=p['vermelho'], danger_hover='#FFD0D8' if claro else BASE['danger_hover'],
             active_start=p['selecionado'], active_end=p['selecionado'], active_border=p['azul'],
             disabled=p['superficie'], disabled_border=p['borda'], scroll_handle=p['scroll'],
             hero=p['cabecalho'], card_end=p['fundo'], table_bg=p['superficie'], progress_track=p['alternada'],
             edit=p['selecionado'], edit_border=p['azul'], delete='#FFE6EA' if claro else BASE['delete'], delete_border=p['vermelho'])
    return legibilidade(c)


def contraste(a, b):
    def luz(cor):
        canais = [int(cor[i:i+2], 16) / 255 for i in (1, 3, 5)]
        canais = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in canais]
        return sum(v * p for v, p in zip(canais, (.2126, .7152, .0722)))
    x, y = luz(a), luz(b)
    return (max(x, y) + .05) / (min(x, y) + .05)


def legibilidade(c):
    # Correção pontual: mantém a família de cor, escurecendo fundos de ação
    # quando texto/ícone claro não atinge 4,5:1. Não muda os blocos ou os dados.
    for chave in ('primary_start', 'primary_end', 'primary_hover', 'query'):
        for _ in range(24):
            if contraste(c['text'], c[chave]) >= 4.5:
                break
            c[chave] = G.QColor(c[chave]).darker(110).name()
        else:
            c[chave] = max(('#000000', '#FFFFFF'), key=lambda fundo: contraste(c['text'], fundo))
    return c


def aplicar_tokens(tema):
    import noturno_demo
    import re
    # A alteração ocorre ANTES de construir os widgets. Nenhum estado de tela é reconstruído.
    destino = cores(tema)
    modelo = getattr(noturno_demo, '_estilo_original_qt', noturno_demo.ESTILO)
    noturno_demo._estilo_original_qt = modelo
    traducao = {v.lower(): destino[k] for k, v in BASE.items()}
    noturno_demo.ESTILO = re.sub(r'#[0-9a-fA-F]{6}', lambda m: traducao.get(m[0].lower(), m[0]), modelo)
    C.clear()
    C.update(destino)


class FundoQt(Fundo):
    def paintEvent(self, evento):
        if C['bg'] == PALETAS['claro']['fundo']:
            p = G.QPainter(self)
            p.fillRect(self.rect(), G.QColor(C['side'] if self.lateral else C['bg']))
            p.end()
        else:
            super().paintEvent(evento)


class FaixaSemanaQt(FaixaSemana):
    def paintEvent(self, evento):
        if C['bg'] == PALETAS['claro']['fundo']:
            p = G.QPainter(self)
            p.setRenderHint(G.QPainter.RenderHint.Antialiasing)
            p.setBrush(G.QColor(C['hero']))
            p.setPen(G.QColor(C['border']))
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)
            p.end()
        else:
            super().paintEvent(evento)
