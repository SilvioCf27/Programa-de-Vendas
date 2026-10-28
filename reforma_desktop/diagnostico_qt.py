"""Diagnóstico seguro do estudo Qt, sem mensagens/valores no registro técnico."""
from pathlib import Path
import sys
import threading
from ProgramFeira.diagnostico import registrar


def pasta_do_objeto(objeto):
    """Resolve na thread criadora; trabalhadores guardam apenas um Path."""
    while objeto is not None:
        pasta = getattr(objeto, 'pasta', None)
        if pasta is not None:
            return Path(pasta)
        objeto = objeto.parent()
    return None


def registrar_seguro(erro, pasta):
    if pasta is None:
        return False
    try:
        return registrar(erro, pasta)
    except Exception:
        # Diagnóstico não pode esconder o resultado original da operação.
        return False


def instalar(pasta, avisar):
    anterior = sys.excepthook
    def tratar(tipo, erro, pilha):
        registrar_seguro(erro.with_traceback(pilha), pasta)
        if threading.current_thread() is threading.main_thread():
            try:
                avisar('Não foi possível concluir a operação. Confira os dados e tente novamente. O diagnóstico técnico não inclui valores ou credenciais.')
            except Exception as falha_aviso:
                registrar_seguro(falha_aviso, pasta)
    sys.excepthook = tratar
    def restaurar():
        if sys.excepthook is tratar:
            sys.excepthook = anterior
    return restaurar
