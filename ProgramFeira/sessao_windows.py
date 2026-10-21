"""Sessão renovável protegida pela conta do Windows; nunca armazena a senha."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile
from ProgramFeira.nuvem import Sessao, ErroNuvem


DISPONIVEL = sys.platform == 'win32'
NOME = 'sessao-nuvem.dpapi'


class _Blob(ctypes.Structure):
    _fields_ = [('tamanho', wintypes.DWORD), ('dados', ctypes.POINTER(ctypes.c_ubyte))]


def _converter(dados, proteger):
    if not DISPONIVEL:
        raise OSError('A sessão persistente requer a proteção de credenciais do Windows.')
    entrada = ctypes.create_string_buffer(dados)
    blob = _Blob(len(dados), ctypes.cast(entrada, ctypes.POINTER(ctypes.c_ubyte)))
    saida = _Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if proteger:
        funcao = crypt.CryptProtectData
        funcao.argtypes = [ctypes.POINTER(_Blob), wintypes.LPCWSTR, ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        argumentos = (ctypes.byref(blob), 'Gestão da Feira', None, None, None, 1, ctypes.byref(saida))
    else:
        funcao = crypt.CryptUnprotectData
        funcao.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        argumentos = (ctypes.byref(blob), None, None, None, None, 1, ctypes.byref(saida))
    funcao.restype = wintypes.BOOL
    if not funcao(*argumentos):
        raise OSError('Não foi possível acessar a sessão protegida pelo Windows.')
    try:
        return ctypes.string_at(saida.dados, saida.tamanho)
    finally:
        kernel.LocalFree(ctypes.cast(saida.dados, ctypes.c_void_p))


def remover(pasta):
    (Path(pasta) / NOME).unlink(missing_ok=True)


def salvar(pasta, url, sessao):
    if not DISPONIVEL:
        return
    if not sessao.refresh_token:
        remover(pasta)
        return
    # Somente a credencial renovável é persistida. O token de acesso fica na memória.
    dados = json.dumps({'protocolo': 1, 'url': url, 'usuario_id': sessao.usuario_id,
                        'email': sessao.email, 'refresh_token': sessao.refresh_token}).encode('utf-8')
    protegido = _converter(dados, True)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=pasta, prefix='.sessao-', suffix='.dpapi')
    try:
        with os.fdopen(fd, 'wb') as arquivo:
            arquivo.write(protegido)
        os.replace(temporario, pasta / NOME)
    finally:
        Path(temporario).unlink(missing_ok=True)


def carregar(pasta, url):
    caminho = Path(pasta) / NOME
    if not DISPONIVEL or not caminho.exists():
        return None
    try:
        if caminho.stat().st_size > 65536:
            raise ValueError()
        dados = json.loads(_converter(caminho.read_bytes(), False))
        if dados['protocolo'] != 1 or dados['url'] != url:
            raise ValueError()
        if not all(isinstance(dados[k], str) and dados[k] for k in ('usuario_id', 'email', 'refresh_token')):
            raise ValueError()
        # Obriga a renovação online antes de qualquer consulta ou envio.
        return Sessao(dados['usuario_id'], dados['email'], '', dados['refresh_token'], 1)
    except (OSError, ValueError, KeyError, TypeError):
        raise ErroNuvem('A sessão salva não pôde ser recuperada. Entre novamente na sua conta.') from None
