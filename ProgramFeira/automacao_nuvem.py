"""Agendamento no loop gráfico, sem rede ou acesso ao banco nesta camada."""
import json
import os
from pathlib import Path
import tempfile
from ProgramFeira.nuvem import ErroTemporario


def carregar_preferencia(pasta):
    try:
        valor = json.loads((Path(pasta) / 'sincronizacao.json').read_text(encoding='utf-8'))['automatica']
        return valor if type(valor) is bool else False
    except FileNotFoundError:
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def salvar_preferencia(pasta, automatica):
    if type(automatica) is not bool:
        raise ValueError('Preferência inválida.')
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=pasta, prefix='.sincronizacao-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as arquivo:
            json.dump({'automatica': automatica}, arquivo)
        os.replace(temporario, pasta / 'sincronizacao.json')
    finally:
        Path(temporario).unlink(missing_ok=True)


class Agendador:
    INTERVALO = 60_000

    def __init__(self, relogio, ativo, livre, iniciar):
        self.relogio, self.ativo, self.livre, self.iniciar = relogio, ativo, livre, iniciar
        self.tarefa = None
        self.executando = self.pausado = False
        self.falhas = 0

    def parar(self):
        if self.tarefa is not None:
            self.relogio.after_cancel(self.tarefa)
            self.tarefa = None

    def agendar(self, atraso):
        self.parar()
        if self.ativo() and not self.executando and not self.pausado:
            self.tarefa = self.relogio.after(atraso, self._disparar)

    def ativar(self):
        self.pausado = False
        self.falhas = 0
        self.agendar(2000)

    def _disparar(self):
        self.tarefa = None
        if not self.ativo() or self.executando or self.pausado:
            return
        if not self.livre():
            self.agendar(5000)
            return
        self.executando = True
        self.iniciar()

    def concluir(self, erro=None, adiar=False):
        self.executando = False
        if erro is not None and not isinstance(erro, ErroTemporario):
            self.pausado = True
            self.parar()
            return
        if erro:
            self.falhas += 1
            atraso = min(300_000, self.INTERVALO * 2 ** min(self.falhas - 1, 3))
        else:
            self.falhas = 0
            atraso = 5000 if adiar else self.INTERVALO
        self.agendar(atraso)
