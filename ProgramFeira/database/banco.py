import sqlite3
import re
from datetime import datetime
from pathlib import Path
from contextlib import closing
from ProgramFeira.database.armazenamento import (
    pasta_dados, preparar_banco, criar_backup as backup_arquivo,
    restaurar_backup as restaurar_arquivo,
)


BANCO_INICIAL = Path(__file__).resolve().parent.parent / "assets/banco_inicial.db"
CAMINHO_BANCO = pasta_dados() / "vendas.db"

def conectar():
    preparar_banco(CAMINHO_BANCO, BANCO_INICIAL)
    return sqlite3.connect(CAMINHO_BANCO)

def criar_backup():
    preparar_banco(CAMINHO_BANCO, BANCO_INICIAL)
    return backup_arquivo(CAMINHO_BANCO)


def restaurar_backup(origem):
    preparar_banco(CAMINHO_BANCO, BANCO_INICIAL)
    return restaurar_arquivo(CAMINHO_BANCO, origem)


def criar_tabela():
    with closing(conectar()) as conexao, conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                dinheiro REAL NOT NULL DEFAULT 0,
                pix REAL NOT NULL DEFAULT 0,
                cartao REAL NOT NULL DEFAULT 0
            )
        """)
        conexao.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vendas_data_unica ON vendas(data)")
    backup_arquivo(CAMINHO_BANCO, 'abertura')


def gravar(sql, parametros, motivo):
    preparar_banco(CAMINHO_BANCO, BANCO_INICIAL)
    # Falha no backup impede a alteração, preservando os dados atuais.
    backup_arquivo(CAMINHO_BANCO, motivo)
    with closing(conectar()) as conexao, conexao:
        conexao.execute(sql, parametros)


def cadastrar_venda(data, dinheiro, pix, cartao):
    gravar("INSERT INTO vendas (data, dinheiro, pix, cartao) VALUES (?, ?, ?, ?)",
           (data, dinheiro, pix, cartao), 'antes-cadastro')


def converter_data_salva(valor):
    """Converte datas antigas e novas do banco para um objeto date."""
    texto = str(valor).strip()

    for formato in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass

    partes = re.search(r"(\d{1,2})\D+(\d{1,2})\D+(\d{4})", texto)

    if partes:
        dia, mes, ano = map(int, partes.groups())

        try:
            return datetime(ano, mes, dia).date()
        except ValueError:
            pass

    return None


def listar_vendas(data_inicial=None, data_final=None, dias_semana=None):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id, data, dinheiro, pix, cartao
        FROM vendas
    """)

    vendas_brutas = cursor.fetchall()

    conexao.close()

    inicio = converter_data_salva(data_inicial) if data_inicial else None
    fim = converter_data_salva(data_final) if data_final else None
    vendas = []

    for venda in vendas_brutas:
        data_venda = converter_data_salva(venda[1])

        if data_venda is None:
            if inicio or fim or dias_semana:
                continue
        else:
            if inicio and data_venda < inicio:
                continue

            if fim and data_venda > fim:
                continue

            if dias_semana and data_venda.weekday() not in dias_semana:
                continue

        vendas.append((venda, data_venda))

    vendas.sort(key=lambda item: item[1] or datetime.min.date(), reverse=True)

    return [venda for venda, _ in vendas]


def listar_anos_vendas():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT data FROM vendas")
    datas = cursor.fetchall()

    conexao.close()

    anos = set()

    for (data,) in datas:
        data_convertida = converter_data_salva(data)

        if data_convertida:
            anos.add(data_convertida.year)

    return sorted(anos)


def obter_resumo_vendas(data_inicial=None, data_final=None, dias_semana=None):
    vendas = listar_vendas(data_inicial, data_final, dias_semana)

    dinheiro = sum(venda[2] for venda in vendas)
    pix = sum(venda[3] for venda in vendas)
    cartao = sum(venda[4] for venda in vendas)

    return dinheiro, pix, cartao

def buscar_venda_por_data(data):
    for venda in listar_vendas():
        data_venda = converter_data_salva(venda[1])

        if data_venda and data_venda.isoformat() == data:
            return venda

    return None


def buscar_venda_por_id(id_venda):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id, data, dinheiro, pix, cartao
        FROM vendas
        WHERE id = ?
    """, (id_venda,))

    venda = cursor.fetchone()

    conexao.close()

    return venda


def excluir_venda(id_venda):
    gravar("DELETE FROM vendas WHERE id = ?", (id_venda,), 'antes-exclusao')


def atualizar_venda(id_venda, data, dinheiro, pix, cartao):
    gravar("UPDATE vendas SET data = ?, dinheiro = ?, pix = ?, cartao = ? WHERE id = ?",
           (data, dinheiro, pix, cartao, id_venda), 'antes-edicao')
