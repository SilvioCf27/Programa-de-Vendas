"""Gera as fontes estáticas distribuídas com o app (requer fonttools apenas aqui).

Entradas oficiais, licenças e hashes em ProgramFeira/assets/fonts/README.md.
Uso: python tools/gerar_fontes.py /pasta/com/Inter.ttf/e/PlusJakartaSans.ttf
"""
import hashlib
from pathlib import Path
import sys
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ORIGENS = {'Inter': '29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031',
           'PlusJakartaSans': '89b3fb38aa0d275d7a731d0d817a4f1622b316b4d7fbdedcf02ee9099ff68bc8'}


def gerar(pasta):
    destino = Path(__file__).resolve().parents[1] / 'ProgramFeira/assets/fonts'
    for origem, checksum in ORIGENS.items():
        arquivo = pasta / (origem + '.ttf')
        if hashlib.sha256(arquivo.read_bytes()).hexdigest() != checksum:
            raise ValueError('Checksum da fonte de origem divergente: ' + origem)
        for peso, estilo in ((400, 'Regular'), (600, 'SemiBold')):
            fonte = TTFont(arquivo)
            eixos = {'wght': peso, **({'opsz': 14} if origem == 'Inter' else {})}
            fonte = instantiateVariableFont(fonte, eixos, inplace=True)
            familia = 'Feira Text' if origem == 'Inter' else 'Feira Display'
            for plataforma, encoding, idioma in ((3, 1, 0x409), (1, 0, 0)):
                for id_nome, valor in ((1, familia), (2, estilo), (4, familia + ' ' + estilo),
                                       (6, familia.replace(' ', '') + '-' + estilo), (16, familia), (17, estilo)):
                    fonte['name'].setName(valor, id_nome, plataforma, encoding, idioma)
            if origem == 'Inter':
                # Torna os algarismos tabulares também nos renderizadores Tk/GDI
                # que não oferecem seleção de recursos OpenType em tempo de uso.
                mapa = {}
                for record in fonte['GSUB'].table.FeatureList.FeatureRecord:
                    if record.FeatureTag == 'tnum':
                        for indice in record.Feature.LookupListIndex:
                            for sub in fonte['GSUB'].table.LookupList.Lookup[indice].SubTable:
                                mapa.update(getattr(sub, 'mapping', {}))
                for tabela in fonte['cmap'].tables:
                    if tabela.isUnicode():
                        for codigo in range(48, 58):
                            glyph = tabela.cmap.get(codigo)
                            tabela.cmap[codigo] = mapa.get(glyph, glyph)
                melhores = fonte.getBestCmap()
                assert len({fonte['hmtx'][melhores[c]][0] for c in range(48, 58)}) == 1
            fonte.save(destino / origem / (origem + '-' + estilo + '.ttf'))


if __name__ == '__main__':
    gerar(Path(sys.argv[1]))
