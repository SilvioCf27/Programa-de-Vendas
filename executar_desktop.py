"""Entrada candidata do desktop 2.0; executar.py preserva a versão 1.7.1."""
import os
from pathlib import Path
import sys


def preparar_importacoes():
    raiz = Path(__file__).resolve().parent
    sys.path.insert(0, str(raiz / 'prototipos/reforma'))


def iniciar():
    preparar_importacoes()
    from reforma_desktop.producao import iniciar as iniciar_producao
    return iniciar_producao()


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--verificar-pacote':
        preparar_importacoes()
        from reforma_desktop.pacote import verificar
        return verificar(Path(sys.argv[2]))
    if len(sys.argv) != 1 and not (len(sys.argv) == 3 and sys.argv[1] == '--confirmar-atualizacao'):
        print('Argumentos de inicialização inválidos.', file=sys.stderr)
        return 1
    try:
        return iniciar()
    except Exception as erro:
        from ProgramFeira.diagnostico import registrar
        from ProgramFeira.database.armazenamento import pasta_dados
        try:
            registrar(erro, pasta_dados())
        except Exception:
            pass
        mensagem = 'Não foi possível abrir o Gestão da Feira 2.0. Seus arquivos foram preservados. Confira os requisitos e o diagnóstico na pasta de dados.'
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, mensagem, 'Gestão da Feira', 0x10)
        else:
            print(mensagem, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
