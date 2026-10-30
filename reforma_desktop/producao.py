"""Inicialização do desktop candidato com os dados e adaptadores existentes."""
from pathlib import Path
import sqlite3

from ProgramFeira import nuvem
from ProgramFeira.database.entrada_backup import MIN_SQLITE


class SemConfiguracao:
    """Ausência explícita de projeto: nunca substitui por serviço simulado."""
    url = ''
    ao_renovar = None
    _ultima_sessao = None


def cliente_configurado(pasta):
    config = nuvem.carregar_config(pasta)
    return nuvem.ClienteNuvem(config['url'], config['chave_publica']) if config else SemConfiguracao()


def conferir_runtime():
    if sqlite3.sqlite_version_info < MIN_SQLITE:
        raise RuntimeError('A versão 2.0 exige SQLite 3.50.2 ou mais recente.')


def iniciar():
    conferir_runtime()
    from ProgramFeira.database.armazenamento import pasta_dados, criar_backup
    from ProgramFeira.database.seguranca_arquivos import sem_redirecionamentos
    from ProgramFeira import atualizador
    from reforma_desktop.versao import VERSAO
    pasta = sem_redirecionamentos(pasta_dados())
    pasta.mkdir(parents=True, exist_ok=True)
    banco = sem_redirecionamentos(pasta/'vendas.db')
    # Preserva o estado anterior antes das inicializações do adaptador Qt.
    if banco.exists():
        criar_backup(banco, motivo='antes-desktop-2')
    cliente = cliente_configurado(pasta)
    from reforma_desktop.aplicacao import iniciar as iniciar_interface
    return iniciar_interface(pasta, cliente_nuvem=cliente, producao=True,
        ao_exibir=lambda: atualizador.confirmar_inicio(versao=VERSAO))
