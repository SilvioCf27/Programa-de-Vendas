"""Servidor TLS de contrato, apenas em loopback, com estado fictício.

O certificado/chave públicos do repositório servem SÓ a estes testes.
A confiança é configurada no opener do teste, nunca no aplicativo.
"""
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import ssl
import threading
from unittest.mock import patch
from urllib import request
from ProgramFeira import nuvem
from reforma_desktop.servico_nuvem_estudo import ClienteEstudo

URL='https://contrato-qt.supabase.co'
CHAVE='sb_publishable_contrato_local'
HOST='contrato-qt.supabase.co'


class ServidorContrato:
    def __init__(self,pasta):
        self.modelo=ClienteEstudo(pasta)
        self.requisicoes=[]
        self.conexoes=[]
        self.falhas=deque()
        self.autorizado=True
        self.bloquear=None
        self.iniciada=threading.Event()
        self.liberar=threading.Event()
        estado=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                corpo=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
                estado.requisicoes.append(dict(caminho=self.path,corpo=corpo,apikey=self.headers.get('apikey'),authorization=self.headers.get('Authorization'),tls=self.connection.version()))
                if estado.bloquear==self.path:
                    estado.iniciada.set();estado.liberar.wait(5)
                status=200;headers={}
                if self.headers.get('apikey')!=CHAVE:
                    status,retorno=403,{'message':'Chave fictícia recusada'}
                elif estado.falhas and estado.falhas[0][0]==self.path:
                    _,status,retorno,headers=estado.falhas.popleft()
                else:
                    token=self.headers.get('Authorization','').removeprefix('Bearer ') or None
                    try:
                        retorno=estado.modelo._post(self.path,corpo,token)
                        if self.path.endswith('/usuario_autorizado'):retorno=retorno and estado.autorizado
                    except nuvem.ConflitoSincronizacao:
                        status,retorno=409,{'code':'PFS01'}
                    except nuvem.ErroTemporario:
                        status,retorno=503,{'message':'Falha temporária fictícia'}
                    except nuvem.ErroNuvem:
                        status=400
                        retorno={'code':'40001' if self.path.endswith('/salvar_fechamento') else 'PFM01'}
                dados=retorno if isinstance(retorno,bytes) else json.dumps(retorno).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(dados)))
                for k,v in headers.items():self.send_header(k,v)
                self.end_headers()
                self.wfile.write(dados)
        self.http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        contexto=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto.minimum_version=ssl.TLSVersion.TLSv1_2
        recursos=Path(__file__).parent/'recursos'
        contexto.load_cert_chain(recursos/'servidor-loopback-cert.pem',recursos/'servidor-loopback-chave-apenas-testes.pem')
        self.http.socket=contexto.wrap_socket(self.http.socket,server_side=True)
        self.thread=threading.Thread(target=lambda:self.http.serve_forever(poll_interval=.01),daemon=True)
        self.thread.start()
        self.contexto_cliente=ssl.create_default_context(cafile=str(recursos/'servidor-loopback-cert.pem'))

    def cliente(self,confiar=True):
        # Usa o opener real e mantém o bloqueio de redirecionamento do núcleo.
        construir=request.build_opener
        def opener(*handlers):
            return construir(request.ProxyHandler({}),request.HTTPSHandler(context=self.contexto_cliente if confiar else None),*handlers)
        with patch.object(nuvem.request,'build_opener',opener):
            return nuvem.ClienteNuvem(URL,CHAVE)

    def rotear(self):
        # Somente o socket do hostname de contrato vai ao loopback. DNS/saída
        # para qualquer outro endereço causam falha, nunca tráfego externo.
        conectar=socket.create_connection
        def local(endereco,*args,**kwargs):
            if endereco!=(HOST,443):raise AssertionError('Saída externa proibida no contrato TLS')
            self.conexoes.append(endereco)
            return conectar(self.http.server_address,*args,**kwargs)
        return patch('socket.create_connection',local)

    def falhar(self,caminho,status,corpo=None,headers=None):
        self.falhas.append((caminho,status,corpo if corpo is not None else {'message':'SEGREDO-HTTP-NAO-EXIBIR'},headers or {}))

    def fechar(self):
        self.liberar.set()
        self.http.shutdown();self.http.server_close();self.thread.join(timeout=5)
        if self.thread.is_alive():raise RuntimeError('Servidor local de teste não terminou')
