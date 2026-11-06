"""Converte a logo vetorial aprovada em ícones PWA/Windows, sem redesenhar a marca.

Requer os requisitos do estudo (PySide6 e Pillow). Não acessa rede ou dados.
"""
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6 import QtCore, QtGui, QtSvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
    fonte = ROOT / 'prototipos/reforma/recursos/logo.svg'
    renderer = QtSvg.QSvgRenderer(str(fonte))
    if not renderer.isValid():
        raise ValueError('Logo vetorial inválida.')
    publico = ROOT / 'web/public'
    shutil.copyfile(fonte, publico / 'logo-feira.svg')

    def renderizar(tamanho, destino, mascara=False, transparente=False):
        imagem = QtGui.QImage(tamanho, tamanho, QtGui.QImage.Format.Format_ARGB32)
        imagem.fill(QtCore.Qt.GlobalColor.transparent if transparente else QtGui.QColor('#0c171f'))
        painter = QtGui.QPainter(imagem)
        margem = tamanho * .12 if mascara else 0
        renderer.render(painter, QtCore.QRectF(margem, margem, tamanho - 2 * margem, tamanho - 2 * margem))
        painter.end()
        if not imagem.save(str(destino)):
            raise OSError('Não foi possível salvar o ícone.')

    for tamanho in (180, 192, 512):
        renderizar(tamanho, publico / f'icon-{tamanho}.png')
    renderizar(512, publico / 'icon-maskable-512.png', mascara=True)
    # ICO é só uma conversão de formato do mesmo vetor, em tamanhos nativos.
    with TemporaryDirectory(prefix='feira-icone-') as pasta:
        png = Path(pasta) / 'icone.png'
        renderizar(256, png, transparente=True)
        with Image.open(png) as imagem:
            imagem.save(ROOT / 'ProgramFeira/assets/gestao-da-feira.ico', sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print('Ícones PWA e Windows gerados a partir da logo vetorial do desktop.')


if __name__ == '__main__':
    main()
