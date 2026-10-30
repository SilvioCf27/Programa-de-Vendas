"""Adaptador real do atualizador portátil, sem alterar os globais do núcleo."""
from pathlib import Path
import shutil
import sys

from ProgramFeira import atualizador
from reforma_desktop.versao import VERSAO


class ServicoAtualizacao:
    real = True

    def __init__(self, banco):
        self.banco = Path(banco)
        self.preparacao = None
        self.helper = None

    @property
    def disponivel(self):
        return sys.platform == 'win32' and bool(getattr(sys, 'frozen', False))

    def consultar(self):
        return atualizador.consultar(versao_atual=VERSAO)

    def preparar(self, release):
        if not self.disponivel:
            raise ValueError('A instalação requer o pacote portátil completo no Windows.')
        self.preparacao = atualizador.preparar(release, Path(sys.executable), self.banco, versao_atual=VERSAO)
        return self.preparacao

    def instalar(self):
        if self.preparacao is None:
            raise ValueError('Confira o pacote antes de instalar.')
        self.helper = atualizador.instalar(self.preparacao, self.banco)
        self.preparacao = None  # O helper passa a ser dono da área de atualização.
        return {'reiniciar': True}

    def limpar(self):
        if self.preparacao is not None:
            shutil.rmtree(self.preparacao['stage'], ignore_errors=True)
        self.preparacao = None
