"""Elementos arredondados preservando os controles nativos ttk e seu teclado.

Os pequenos fundos RGBA são desenhados em memória e esticados em nove partes;
não substituem botões, campos, seletores ou suas ações por controles de Canvas.
"""
import base64
import struct
import zlib
import tkinter as tk
from functools import lru_cache


def _rgb(cor):
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def _png(largura, altura, pixels):
    def parte(tipo, conteudo):
        return struct.pack('!I', len(conteudo)) + tipo + conteudo + struct.pack('!I', zlib.crc32(tipo + conteudo) & 0xffffffff)
    dados = b''.join(b'\0' + bytes(pixels[y * largura * 4:(y + 1) * largura * 4]) for y in range(altura))
    return b'\x89PNG\r\n\x1a\n' + parte(b'IHDR', struct.pack('!2I5B', largura, altura, 8, 6, 0, 0, 0)) + parte(b'IDAT', zlib.compress(dados)) + parte(b'IEND', b'')


@lru_cache(maxsize=16)
def cobertura_arredondada(raio):
    tamanho = raio * 2 + 6
    def dentro(x, y, margem):
        r = max(0, raio - margem)
        cx = min(max(x, margem + r), tamanho - margem - r)
        cy = min(max(y, margem + r), tamanho - margem - r)
        return margem <= x <= tamanho - margem and margem <= y <= tamanho - margem and (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2
    cobertura = []
    for y in range(tamanho):
        for x in range(tamanho):
            total = interno = 0
            for sy in (.125, .375, .625, .875):
                for sx in (.125, .375, .625, .875):
                    if dentro(x + sx, y + sy, 0):
                        total += 1
                        interno += dentro(x + sx, y + sy, 1)
            cobertura.append((total, interno))
    return tuple(cobertura)


def imagem_arredondada(root, fundo, borda, raio=9, realce=False):
    cache = root.__dict__.setdefault('_fundos_arredondados', {})
    chave = (fundo, borda, raio, realce)
    if chave in cache:
        return cache[chave]
    tamanho = raio * 2 + 6
    pixels = bytearray()
    cor_fundo, cor_borda = _rgb(fundo), _rgb(borda)
    for i, (total, interno) in enumerate(cobertura_arredondada(raio)):
        if total:
            cor = [round((a * interno + b * (total - interno)) / total)
                   for a, b in zip(cor_fundo, cor_borda)]
            y = i // tamanho
            if realce and y < raio + 1:
                intensidade = .055 * (1 - y / (raio + 1))
                cor = [round(c + (255 - c) * intensidade) for c in cor]
            pixels.extend((*cor, round(total * 255 / 16)))
        else:
            pixels.extend((0, 0, 0, 0))
    # ttk repete o miolo da imagem para preencher o controle. Um miolo de
    # poucos pixels multiplica as operações de composição, sobretudo em painéis.
    # Expandir apenas a área lisa preserva os cantos e reduz essas repetições.
    lado = 128
    margem = raio + 1
    origem = [i if i < margem else tamanho - (lado - i) if i >= lado - margem else margem for i in range(lado)]
    linhas = {}
    expandido = bytearray()
    for y in origem:
        if y not in linhas:
            linhas[y] = b''.join(bytes(pixels[(y * tamanho + x) * 4:(y * tamanho + x) * 4 + 4]) for x in origem)
        expandido.extend(linhas[y])
    imagem = tk.PhotoImage(master=root, data=base64.b64encode(_png(lado, lado, expandido)))
    cache[chave] = imagem
    return imagem


def instalar_elementos(root, estilo, cores, tema):
    if not hasattr(root, '_acabamento'):
        root._acabamento = {}
    cache = root._acabamento
    if not hasattr(root, '_layouts_originais'):
        root._layouts_originais = {nome: estilo.layout(nome) for nome in ('TEntry', 'TCombobox', 'TMenubutton', 'TNotebook.Tab', 'TCheckbutton')}
    def elemento(nome, normal, borda, raio=9, estados=()):
        identificador = f'Gestao.{tema}.{nome}'
        if identificador not in estilo.element_names():
            imagens = [imagem_arredondada(root, normal, borda, raio, realce=(nome == 'Panel' or nome.startswith('Indicador') or nome == 'Primary.TButton'))]
            specs = []
            for estado, preenchimento, contorno in estados:
                imagem = imagem_arredondada(root, preenchimento, contorno, raio)
                imagens.append(imagem)
                specs.append((estado, imagem))
            # A imagem maior não deve aumentar o tamanho mínimo dos controles.
            estilo.element_create(identificador, 'image', imagens[0], *specs, width=raio * 2 + 6, height=raio * 2 + 6, border=raio + 1, padding=(0 if nome == 'Panel' else 3 if nome.startswith('Ajuda') else raio + 1), sticky='nsew')
            cache[identificador] = imagens
        return identificador

    def trocar(layout, nomes):
        resultado = []
        for nome, opcoes in layout:
            opcoes = dict(opcoes)
            if 'children' in opcoes:
                opcoes['children'] = trocar(opcoes['children'], nomes)
            resultado.append((nomes.get(nome, nome), opcoes))
        return resultado

    for classe, fundo, cor_borda in (
        ('TButton', cores['superficie'], cores['borda']),
        ('Primary.TButton', cores['botao'], cores['botao']),
        ('Danger.TButton', cores['superficie'], cores['vermelho']),
    ):
        ativo = cores['botao_hover'] if classe == 'Primary.TButton' else cores['hover']
        imagem = elemento(classe, fundo, cor_borda, estados=(('disabled', cores['superficie'], cores['borda']), ('pressed', ativo, cores['azul']), ('active', ativo, cor_borda), ('focus', fundo, cores['azul'])))
        estilo.layout(classe, [(imagem, {'sticky': 'nsew', 'children': [('Button.focus', {'sticky': 'nsew', 'children': [('Button.padding', {'sticky': 'nsew', 'children': [('Button.label', {'sticky': 'nsew'})]})]})]})])
    ajuda = elemento('Ajuda', cores['superficie'], cores['borda'], raio=7, estados=(('active', cores['hover'], cores['azul']), ('focus', cores['superficie'], cores['azul'])))
    estilo.layout('Ajuda.TButton', [(ajuda, {'sticky': 'nsew', 'children': [('Button.label', {'sticky': 'nsew'})]})])
    for classe, antigo in (('TEntry', 'Entry.field'), ('TCombobox', 'Combobox.field'), ('TMenubutton', 'Menubutton.border')):
        imagem = elemento(classe, cores['superficie'], cores['borda'], raio=8, estados=(('focus', cores['superficie'], cores['azul']),))
        estilo.layout(classe, trocar(root._layouts_originais[classe], {antigo: imagem}))
    from ProgramFeira.interface.icones import imagem_icone, _distancia
    seta_nome = f'Gestao.{tema}.Combobox.downarrow'
    if seta_nome not in estilo.element_names():
        estilo.element_create(seta_nome, 'image', imagem_icone(root, 'baixo', cores['texto'], 18), sticky='')
    campo_combo = f'Gestao.{tema}.TCombobox'
    estilo.layout('TCombobox', [(campo_combo, {'sticky': 'nsew', 'children': [
        (seta_nome, {'side': 'right', 'sticky': ''}),
        ('Combobox.padding', {'sticky': 'nsew', 'children': [('Combobox.textarea', {'sticky': 'nsew'})]})]})])
    nome_check = f'Gestao.{tema}.Checkbutton.indicator'
    if nome_check not in estilo.element_names():
        imagens_check = []
        for selecionado in (False, True):
            pixels = []
            for y in range(18):
                for x in range(18):
                    raio = 4
                    cx, cy = min(max(x + .5, raio), 18 - raio), min(max(y + .5, raio), 18 - raio)
                    dentro = (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= raio ** 2
                    interno = 1 <= x < 17 and 1 <= y < 17 and (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= (raio - 1) ** 2
                    preenchimento = cores['botao'] if selecionado else cores['superficie']
                    cor = preenchimento if interno or selecionado else cores['borda']
                    if selecionado and min(_distancia(x, y, (4, 8), (7, 12)), _distancia(x, y, (7, 12), (14, 5))) < 1:
                        cor = '#FFFFFF'
                    pixels.extend((*_rgb(cor), 255 if dentro else 0))
            imagens_check.append(tk.PhotoImage(master=root, data=base64.b64encode(_png(18, 18, pixels))))
        cache[nome_check] = imagens_check
        estilo.element_create(nome_check, 'image', imagens_check[0], ('selected', imagens_check[1]), width=24, sticky='')
    estilo.layout('TCheckbutton', trocar(root._layouts_originais['TCheckbutton'], {'Checkbutton.indicator': nome_check}))
    painel = elemento('Panel', cores['superficie'], cores['borda'], raio=16)
    for classe in ('Panel.TFrame', 'Card.TFrame'):
        estilo.configure(classe, background=cores['fundo'])
        estilo.layout(classe, [(painel, {'sticky': 'nsew', 'border': 0})])
    aba = elemento('Tab', cores['superficie'], cores['borda'], raio=8, estados=(('selected', cores['selecionado'], cores['azul']), ('active', cores['hover'], cores['borda'])))
    margem_aba = 'Gestao.TabMargem'
    if margem_aba not in estilo.element_names():
        transparente = tk.PhotoImage(master=root, width=8, height=1)
        cache[margem_aba] = transparente
        estilo.element_create(margem_aba, 'image', transparente, padding=(0, 0, 7, 0), sticky='nsew')
    estilo.layout('TNotebook.Tab', [(margem_aba, {'sticky': 'nsew', 'children':
        trocar(root._layouts_originais['TNotebook.Tab'], {'Notebook.tab': aba})})])

    from ProgramFeira.interface.visual import cores_indicadores
    for chave, (cor, fundo, borda) in cores_indicadores(cores).items():
        nome = elemento('Indicador' + chave, fundo, borda, raio=14)
        estilo.configure(f'{chave}.Card.TFrame', background=cores['fundo'])
        estilo.layout(f'{chave}.Card.TFrame', [(nome, {'sticky': 'nsew', 'border': 0})])
        ajuda_card = elemento('Ajuda' + chave, fundo, borda, raio=10,
                              estados=(('active', cores['hover'], cor), ('focus', fundo, cor)))
        estilo.layout(f'{chave}.Superficie.Ajuda.TButton', [
            (ajuda_card, {'sticky': 'nsew', 'children': [('Button.label', {'sticky': 'nsew'})]})])
        estilo.configure(f'{chave}.Superficie.Ajuda.TButton', foreground=cor, padding=(2, 0))
