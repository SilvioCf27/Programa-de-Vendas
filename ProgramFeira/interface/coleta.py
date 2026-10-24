"""Mantém a finalização de ciclos Tk na thread da interface durante tarefas."""
import gc
import threading

_trabalhos = 0
_reabilitar = False


def suspender_coleta():
    # CPython pode coletar ciclos antigos de StringVar na thread que aloca
    # memória. Isso chama Tcl fora da interface mesmo sem usar widgets no worker.
    global _trabalhos, _reabilitar
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('A tarefa gráfica deve ser iniciada pela interface.')
    gc.collect()
    if _trabalhos == 0:
        _reabilitar = gc.isenabled()
        gc.disable()
    _trabalhos += 1
    encerrado = False

    def concluir():
        nonlocal encerrado
        global _trabalhos
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('A coleta gráfica deve ser retomada pela interface.')
        if encerrado:
            return
        encerrado = True
        _trabalhos -= 1
        if _trabalhos == 0:
            # O controlador só chama esta função após o worker ter terminado.
            gc.collect()
            if _reabilitar:
                gc.enable()
    return concluir
